from typing import Any
from core.tools.tool.builtin_tool import BuiltinTool


class EmitState(BuiltinTool):
    """
    Emit state on Athena chat frontend.
    First 6 characters of the message belong to protocal header.
    """
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ):
        main_state = tool_parameters.get("main_state")
        sub_state = tool_parameters.get("sub_state")

        response = []
        if main_state:
            text_message = self.create_text_message(main_state)
            response.append(text_message)
        if sub_state:
            text_message = self.create_text_message(sub_state)
            response.append(text_message)

        return response
