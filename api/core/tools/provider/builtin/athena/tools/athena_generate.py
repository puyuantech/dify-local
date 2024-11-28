import json
from typing import Any, Union

from athena_client import AthenaClient
from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool


class AthenaGenerate(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ) -> Union[ToolInvokeMessage, list[ToolInvokeMessage]]:
        app_id = tool_parameters.get("app_id", "")
        query = tool_parameters.get("query", "")
        assert app_id, "app_id is required"
        assert query, "query is required"
        try:
            history = json.loads(tool_parameters.get("history") or "[]")
            kb_ids = json.loads(tool_parameters.get("kb_ids") or "[]")
        except json.JSONDecodeError:
            raise ValueError("history and kb_ids must be valid JSON") from None
        is_multiple_project_query = tool_parameters.get("is_multiple_project_query", False)
        is_qa_query = tool_parameters.get("is_qa_query", True)
        credentials = self.runtime.credentials
        client = AthenaClient(base_url=credentials["base_url"], api_key=credentials["api_key"])
        res = client.generate(app_id=app_id, query=query, history=history, kb_ids=kb_ids, is_multiple_project_query=is_multiple_project_query, is_qa_query=is_qa_query)
        return self.create_json_message(res)      