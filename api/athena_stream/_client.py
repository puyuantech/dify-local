import inspect
import json
import time
from typing import TYPE_CHECKING, Dict, Generator, Type, TypeVar, Union, cast, Optional

import httpx
import pydantic
from httpx import URL
from loguru import logger

from ._constants import (
    DEFAULT_MAX_RETRIES,
    DEFAULT_TIMEOUT,
    INITIAL_RETRY_DELAY,
    MAX_RETRY_DELAY,
)
from .types._request import FinalRequestOptions, RequestOptions
from .types.errors import (
    HTTP_CODE,
    APIConnectionError,
    APITimeoutError,
    BadResponseError,
    VMCException,
)

if TYPE_CHECKING:
    from .types._base import BaseResponse

ResponseT = TypeVar(
    "ResponseT",
    bound=Union[
        None,
        dict,
        list,
        "BaseResponse",
    ],
)


class SyncAPIClient:
    _client: httpx.Client
    max_retries: int
    auth_headers: dict

    def __init__(
        self,
        *,
        base_url: Union[str, URL],
        max_retries: int = DEFAULT_MAX_RETRIES,
        timeout: httpx.Timeout = DEFAULT_TIMEOUT,
        proxies: Union[None, httpx._types.ProxyTypes] = None,
        auth_headers: Union[None, Dict] = None,
    ):
        self._client = httpx.Client(base_url=base_url, timeout=timeout, proxies=proxies)
        self.max_retries = max_retries
        self.auth_headers = auth_headers or {}

    def get_auth_headers(self) -> dict:
        return self.auth_headers

    @property
    def default_headers(self) -> dict:
        return {
            "Accept": "application/json",
        }

    def _build_headers(self, options: FinalRequestOptions) -> httpx.Headers:
        headers = {**self.default_headers, **options.headers}
        if not options.no_auth:
            auth_headers = self.get_auth_headers()
            headers = {**headers, **auth_headers}
        return httpx.Headers(headers)

    def _build_request(self, options: FinalRequestOptions) -> httpx.Request:
        headers = self._build_headers(options)
        content_type = headers.get("Content-Type")
        if options.json_data is not None and content_type is None:
            headers["Content-Type"] = "application/json; charset=utf-8"
        # if options.files is not None or options.data is not None and content_type is None:
        #     headers["Content-Type"] = "multipart/form-data"
        # httpx uses connection pooling, uncompatible with asyncio
        headers["Connection"] = "close"
        kwargs = {}
        if options.timeout is not None:
            kwargs["timeout"] = options.timeout
        return self._client.build_request(
            method=options.method,
            url=options.url,
            params=options.params,
            headers=headers,
            json=options.json_data,
            files=options.files,
            data=options.data,
            content=options.content,
            **kwargs,
        )

    def _raise_api_exception_from_text(self, text: str, e: Exception = None):
        try:
            body = json.loads(text)
            if "code" not in body:
                raise ValueError("No code in response")
        except Exception as e:
            raise BadResponseError(msg=str(e), context={"response": text}) from e
        if body["code"] == HTTP_CODE.API_TIMEOUT:
            raise APITimeoutError(context=body) from e
        if body["code"] == HTTP_CODE.API_CONNECTION_ERROR:
            raise APIConnectionError(context=body) from e
        if body["code"] != HTTP_CODE.SUCCESS:
            raise VMCException(HTTP_CODE=body["code"], msg=body.get("msg", "")) from None

    def _retry_request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        remaining_retries: int,
    ) -> ResponseT:
        remaining = remaining_retries - 1
        if remaining == 1:
            logger.debug("1 retry left")
        else:
            logger.debug(f"{remaining} retries left")
        max_retries = options.get_max_retries(self.max_retries)
        retry_timeout = min(
            INITIAL_RETRY_DELAY * 2 ** (max_retries - remaining), MAX_RETRY_DELAY
        )
        logger.info(f"Retrying {options.url} in {retry_timeout} seconds")
        time.sleep(retry_timeout)

        return self._request(
            cast_to=cast_to,
            options=options,
            remaining_retries=remaining,
        )

    def _should_retry(self, response: httpx.Response) -> bool:
        logger.debug(f"Server error {response.status_code}")
        try:
            json = response.json()
        except Exception:
            """Server might not work properly"""
            return False
        if "code" not in json:
            return False
        if json["code"] in (
            HTTP_CODE.API_TIMEOUT,
            HTTP_CODE.API_CONNECTION_ERROR,
            HTTP_CODE.API_RATE_LIMIT,
        ):
            return True
        return False

    def _request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        remaining_retries: Union[None, int] = None,
    ):
        request = self._build_request(options)
        retries = (
            remaining_retries
            if remaining_retries is not None
            else options.get_max_retries(self.max_retries)
        )

        try:
            response = self._client.send(request, stream=options.stream)
        except httpx.TimeoutException as e:
            logger.debug(f"Request timed out: {e}")
            if retries > 0:
                return self._retry_request(cast_to, options, retries)
            raise APITimeoutError(context={"request": request}) from e
        except Exception as e:
            logger.debug(f"Request failed: {e}")
            if retries > 0:
                return self._retry_request(cast_to, options, retries)
            raise APIConnectionError(context={"request": request}) from e

        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as e:
            logger.debug(f"Request failed: {e}, {response.text}")
            if retries > 0 and self._should_retry(response):
                return self._retry_request(cast_to, options, retries)
            self._raise_api_exception_from_text(e.response.text, e)
        if not options.stream:
            if options.raw_response:
                return cast(ResponseT, response)
            self._raise_api_exception_from_text(response.text)
            try:
                if inspect.isclass(cast_to) and issubclass(cast_to, pydantic.BaseModel):
                    return cast(ResponseT, cast_to.model_validate(response.json()))
                return cast(ResponseT, response.json())
            except Exception as e:
                logger.error(f"Encountered Bad Response: {response.json()}")
                raise BadResponseError(str(e), context={"response": response.json()})
        else:
            def streaming():
                for chunk in response.iter_lines():
                    if not chunk:
                        continue
                    if options.raw_response:
                        yield cast(ResponseT, chunk)
                    else:
                        if not chunk.startswith(options.stream_prefix):
                            raise BadResponseError(
                                msg="Invalid stream prefix",
                                context={"response": chunk},
                            )
                        data = chunk[len(options.stream_prefix) :]
                        self._raise_api_exception_from_text(data)

                        if inspect.isclass(cast_to) and issubclass(
                            cast_to, pydantic.BaseModel
                        ):
                            yield cast(
                                ResponseT, cast_to.model_validate(json.loads(data))
                            )
                        else:
                            yield cast(ResponseT, json.loads(data))

            return streaming()

    def request(
        self,
        cast_to: Type[ResponseT],
        options: FinalRequestOptions,
        remaining_retries: Union[int, None] = None,
    ):
        return self._request(cast_to, options, remaining_retries)

    def get(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: RequestOptions = None,
    ) -> ResponseT:
        options = options or {}
        opts = FinalRequestOptions(method="get", url=path, **options)
        return self.request(cast_to, opts)

    def post(
        self,
        path: str,
        *,
        body: Union[Dict, None] = None,
        cast_to: Type[ResponseT],
        options: Optional[RequestOptions] = None,
    ) -> ResponseT:
        options = options or {}
        opts = FinalRequestOptions(method="post", json_data=body, url=path, **options)
        return self.request(cast_to, opts)

    def stream(
        self,
        path: str,
        *,
        body: Union[Dict, None] = None,
        cast_to: Type[ResponseT],
        options: Optional[RequestOptions] = None,
    ) -> Generator[ResponseT, None, None]:
        options = options or {}
        opts = FinalRequestOptions(
            method="post", json_data=body, url=path, stream=True, **options
        )
        return self.request(cast_to, opts)

    def put(
        self,
        path: str,
        *,
        body: Union[Dict, None] = None,
        cast_to: Type[ResponseT],
        options: Optional[RequestOptions] = None,
    ) -> ResponseT:
        options = options or {}
        opts = FinalRequestOptions(method="put", json_data=body, url=path, **options)
        return self.request(cast_to, opts)

    def delete(
        self,
        path: str,
        *,
        cast_to: Type[ResponseT],
        options: Optional[RequestOptions] = None,
    ) -> ResponseT:
        options = options or {}
        opts = FinalRequestOptions(method="delete", url=path, **options)
        return self.request(cast_to, opts)

    def patch(
        self,
        path: str,
        *,
        body: Union[Dict, None] = None,
        cast_to: Type[ResponseT],
        options: Optional[RequestOptions] = None,
    ) -> ResponseT:
        options = options or {}
        opts = FinalRequestOptions(method="patch", json_data=body, url=path, **options)
        return self.request(cast_to, opts)
