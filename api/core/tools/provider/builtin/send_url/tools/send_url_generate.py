from typing import Any, Union
import requests

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool


class SendUrlGenerate(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ) -> Union[ToolInvokeMessage, list[ToolInvokeMessage]]:
        url = tool_parameters.get("url", "")
        text = tool_parameters.get("data", "")
        
        assert url, "url is required"
        data = {
            'action': 'update_state', 
            'data': text
        }   

        requests.post(url, json=data)
        return self.create_json_message({"message": "Data sent successfully", "url": url})
