from collections.abc import Iterable
from typing import Literal, TypedDict, Union

import httpx
from pydantic import Field

from ._base import BaseModel


class RequestOptions(TypedDict, total=False):
    headers: dict
    timeout: httpx.Timeout
    params: dict
    max_retries: int
    no_auth: bool
    raw_response: bool
    files: dict
    data: dict
    content: Union[bytes, str, Iterable[bytes], Iterable[str]]
    stream_prefix: str


class FinalRequestOptions(BaseModel):
    method: Literal["get", "post", "put", "delete", "patch"]
    url: str
    headers: dict = Field(default_factory=dict)
    params: dict = Field(default_factory=dict)
    max_retries: Union[int, None] = None
    timeout: Union[httpx.Timeout, None] = None
    json_data: Union[dict, None] = None
    files: Union[dict, None] = None
    data: Union[dict, None] = None
    content: Union[bytes, str, Iterable[bytes], Iterable[str], None] = None
    no_auth: bool = False
    raw_response: bool = False
    stream: bool = False
    stream_prefix: str = "data:"

    def get_max_retries(self, max_retries: int) -> int:
        return self.max_retries if self.max_retries is not None else max_retries
