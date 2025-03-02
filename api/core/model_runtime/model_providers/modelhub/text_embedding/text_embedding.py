import json
import time
from decimal import Decimal
from typing import Optional, Dict, Any
from urllib.parse import urljoin

import requests

from core.entities.embedding_type import EmbeddingInputType
from core.model_runtime.entities.common_entities import I18nObject
from core.model_runtime.entities.model_entities import (
    AIModelEntity,
    FetchFrom,
    ModelPropertyKey,
    ModelType,
    PriceConfig,
    PriceType,
)
from core.model_runtime.entities.text_embedding_entities import EmbeddingUsage, TextEmbeddingResult
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.text_embedding_model import TextEmbeddingModel
from core.model_runtime.model_providers.modelhub._common import _CommonOAI_API_Compat


class ModelHubEmbeddingModel(_CommonOAI_API_Compat, TextEmbeddingModel):
    """
    Model class for an OpenAI API-compatible text embedding model.
    """

    def _invoke(
        self,
        model: str,
        credentials: dict,
        texts: list[str],
        user: Optional[str] = None,
        input_type: EmbeddingInputType = EmbeddingInputType.DOCUMENT,
    ) -> TextEmbeddingResult:
        """
        Invoke text embedding model

        :param model: model name
        :param credentials: model credentials
        :param texts: texts to embed
        :param user: unique user id
        :return: embeddings result
        """

        # Prepare headers and payload for the request
        headers = {"Content-Type": "application/json"}

        api_key = credentials.get("api_key")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"

        endpoint_url = credentials.get("endpoint_url")
        if not endpoint_url.endswith("/"):
            endpoint_url += "/"

        endpoint_url = endpoint_url.replace("v1/", "")

        endpoint_url = urljoin(endpoint_url, "embedding")

        payload: Dict[str, Any] = {"content": texts, "model": model, }

        if user:
            payload["user"] = user

        response = requests.post(endpoint_url, headers=headers, json=payload, timeout=(10, 300))
        response.raise_for_status()
        response_data = response.json()

        used_tokens = response_data.get("cost", {}).get("total_tokens", 0)

        usage = self._calc_response_usage(model=model, credentials=credentials, tokens=used_tokens)

        return TextEmbeddingResult(embeddings=response_data["embedding"], usage=usage, model=model)

    def get_num_tokens(self, model: str, credentials: dict, texts: list[str]) -> int:
        """
        Approximate number of tokens for given messages using GPT2 tokenizer

        :param model: model name
        :param credentials: model credentials
        :param texts: texts to embed
        :return:
        """
        return sum(self._get_num_tokens_by_gpt2(text) for text in texts)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            headers = {"Content-Type": "application/json"}

            api_key = credentials.get("api_key")

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            endpoint_url = credentials.get("endpoint_url")
            if not endpoint_url.endswith("/"):
                endpoint_url += "/"

            endpoint_url = urljoin(endpoint_url, "embeddings")

            payload = {"input": "ping", "model": model}

            response = requests.post(url=endpoint_url, headers=headers, data=json.dumps(payload), timeout=(10, 300))

            if response.status_code != 200:
                raise CredentialsValidateFailedError(
                    f"Credentials validation failed with status code {response.status_code}"
                )

            try:
                json_result = response.json()
            except json.JSONDecodeError as e:
                raise CredentialsValidateFailedError("Credentials validation failed: JSON decode error")

            if "model" not in json_result:
                raise CredentialsValidateFailedError("Credentials validation failed: invalid response")
        except CredentialsValidateFailedError:
            raise
        except Exception as ex:
            raise CredentialsValidateFailedError(str(ex))

    def get_customizable_model_schema(self, model: str, credentials: dict) -> AIModelEntity:
        """
        generate custom model entities from credentials
        """
        entity = AIModelEntity(
            model=model,
            label=I18nObject(en_US=model),
            model_type=ModelType.TEXT_EMBEDDING,
            fetch_from=FetchFrom.CUSTOMIZABLE_MODEL,
            model_properties={
                ModelPropertyKey.CONTEXT_SIZE: int(credentials.get("context_size")),
                ModelPropertyKey.MAX_CHUNKS: 1,
            },
            parameter_rules=[],
            pricing=PriceConfig(
                input=Decimal(credentials.get("input_price", 0)),
                unit=Decimal(credentials.get("unit", 0)),
                currency=credentials.get("currency", "USD"),
            ),
        )

        return entity

    def _calc_response_usage(self, model: str, credentials: dict, tokens: int) -> EmbeddingUsage:
        """
        Calculate response usage

        :param model: model name
        :param credentials: model credentials
        :param tokens: input tokens
        :return: usage
        """
        # get input price info
        input_price_info = self.get_price(
            model=model, credentials=credentials, price_type=PriceType.INPUT, tokens=tokens
        )

        # transform usage
        usage = EmbeddingUsage(
            tokens=tokens,
            total_tokens=tokens,
            unit_price=input_price_info.unit_price,
            price_unit=input_price_info.unit,
            total_price=input_price_info.total_amount,
            currency=input_price_info.currency,
            latency=time.perf_counter() - self.started_at,
        )

        return usage
