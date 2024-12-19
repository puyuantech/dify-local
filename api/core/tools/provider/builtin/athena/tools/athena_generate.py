import json
from typing import Any

from athena_stream import AthenaClient
from athena_stream.types.chat import MessageType
from core.tools.tool.builtin_tool import BuiltinTool


class AthenaGenerate(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ):
        app_id, query = tool_parameters.get("app_id"), tool_parameters.get("query")

        assert app_id and query, "app_id and query are required"

        try:
            history = json.loads(tool_parameters.get("history") or "[]")
        except json.JSONDecodeError:
            raise ValueError("history must be valid JSON") from None

        try:
            kb_ids = json.loads(tool_parameters.get("kb_ids") or "[]")
        except json.JSONDecodeError:
            raise ValueError("kb_ids must be valid JSON") from None

        credentials = self.runtime.credentials

        client = AthenaClient(base_url=credentials["base_url"], api_key=credentials["api_key"])

        recall = []
        full_text = ''

        yield self.create_text_message('athena')

        for t in client.stream(
            app_id=app_id,
            query=query,
            history=history or [],
            kb_ids=kb_ids or [],
            is_multiple_project_query=bool(tool_parameters.get("is_multiple_project_query", 0)),
            is_qa_query=bool(tool_parameters.get("is_qa_query", 0))
        ):
            if t.msg_type == MessageType.RETRIEVAL:
                recall.extend(t.data)
            elif t.msg_type == MessageType.GENERATION:
                full_text += t.data
            yield self.create_text_message("athena" + json.dumps(t.model_dump()))

        return [
            self.create_json_message({"recall": recall}),
            self.create_text_message(full_text),
        ]
