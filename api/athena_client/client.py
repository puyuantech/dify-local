import os

from ._client import SyncAPIClient
from .types.chat import ChatResponse, MessageType


class AthenaClient:
    def __init__(self, base_url: str | None = None, api_key: str | None = None):
        base_url = base_url or os.getenv("ATHENA_BASE_URL")
        api_key = api_key or os.getenv("ATHENA_API_KEY")
        assert base_url, "base_url is required"
        assert api_key, "api_key is required"
        self.client = SyncAPIClient(base_url=base_url, auth_headers={"Authorization": f"Bearer {api_key}"})
        self._stream = self.client.stream
        self._get = self.client.get
        self._post = self.client.post

    def stream(
        self,
        app_id: str,
        query: str,
        history: list[dict] = [],
        kb_ids: list[str] = [],
        verbose: int = 0,
        is_multiple_project_query: bool = False,
        is_qa_query: bool = True,
    ):
        return self._stream(
            "/knowledge/chat",
            body={
                "app_id": app_id,
                "query": query,
                "history": history,
                "kb_ids": kb_ids,
                "verbose": verbose,
                "is_multiple_project_query": is_multiple_project_query,
                "is_qa_query": is_qa_query,
            },
            cast_to=ChatResponse,
            options={"stream_prefix": ""},
        )

    def generate(
        self,
        app_id: str,
        query: str,
        history: list[dict] = [],
        kb_ids: list[str] = [],
        is_multiple_project_query: bool = False,
        is_qa_query: bool = True,
    ):
        generation = {"recall": [], "text": ""}
        for t in self.stream(
            app_id=app_id,
            query=query,
            history=history,
            kb_ids=kb_ids,
            verbose=3,
            is_multiple_project_query=is_multiple_project_query,
            is_qa_query=is_qa_query,
        ):
            if t.msg_type == MessageType.RETRIEVAL:
                generation["recall"].extend(t.data)
            elif t.msg_type == MessageType.GENERATION:
                generation["text"] = generation.get("text", "") + t.data
        return generation
