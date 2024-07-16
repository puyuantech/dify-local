from typing import Optional

import numpy as np
from modelhub import ModelhubClient

from core.model_runtime.entities.rerank_entities import RerankDocument, RerankResult
from core.model_runtime.errors.invoke import (
    InvokeError,
)
from core.model_runtime.errors.validate import CredentialsValidateFailedError
from core.model_runtime.model_providers.__base.rerank_model import RerankModel


class CohereRerankModel(RerankModel):
    """
    Model class for Cohere rerank model.
    """

    def _invoke(
        self,
        model: str,
        credentials: dict,
        query: str,
        docs: list[str],
        score_threshold: Optional[float] = None,
        top_n: Optional[int] = None,
        user: Optional[str] = None,
    ) -> RerankResult:
        """
        Invoke rerank model

        :param model: model name
        :param credentials: model credentials
        :param query: search query
        :param docs: docs for reranking
        :param score_threshold: score threshold
        :param top_n: top n
        :param user: unique user id
        :return: rerank result
        """
        if len(docs) == 0:
            return RerankResult(model=model, docs=docs)

        user_name, user_password = credentials["api_key"].split(":")
        client = ModelhubClient(
            user_name=user_name,
            user_password=user_password,
            host=credentials["endpoint_url"].replace("v1", ""),
        )
        scores = client.cross_embedding(
            [[query, doc] for doc in docs],
            model=model,
        ).scores
        sort_idx = np.argsort(scores)[::-1]
        rerank_documents = []
        for i in sort_idx[:top_n] if top_n is not None else sort_idx:
            rerank_document = RerankDocument(index=i, text=docs[i], score=scores[i])
            if score_threshold is not None:
                if scores[i] >= score_threshold:
                    rerank_documents.append(rerank_document)
            else:
                rerank_documents.append(rerank_document)

        return RerankResult(model=model, docs=rerank_documents)

    def validate_credentials(self, model: str, credentials: dict) -> None:
        """
        Validate model credentials

        :param model: model name
        :param credentials: model credentials
        :return:
        """
        try:
            self.invoke(
                model=model,
                credentials=credentials,
                query="What is the capital of the United States?",
                docs=[
                    "Carson City is the capital city of the American state of Nevada. At the 2010 United States "
                    "Census, Carson City had a population of 55,274.",
                    "The Commonwealth of the Northern Mariana Islands is a group of islands in the Pacific Ocean that "
                    "are a political division controlled by the United States. Its capital is Saipan.",
                ],
                score_threshold=0.8,
            )
        except Exception as ex:
            raise CredentialsValidateFailedError(str(ex))

    @property
    def _invoke_error_mapping(self) -> dict[type[InvokeError], list[type[Exception]]]:
        """
        Map model invoke error to unified error
        The key is the error type thrown to the caller
        The value is the error type thrown by the model,
        which needs to be converted into a unified error type for the caller.

        :return: Invoke error mapping
        """
        return {}
