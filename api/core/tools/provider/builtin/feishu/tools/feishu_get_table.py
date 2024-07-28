from typing import Any, Union

import anyio
from slark import AsyncLark

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool


class FeishuGetTableTool(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ) -> Union[ToolInvokeMessage, list[ToolInvokeMessage]]:
        table_url = tool_parameters.get("table_url", "")
        if not table_url:
            return self.create_text_message("Invalid parameter table_url")
        output_format = tool_parameters.get("output_format", "markdown")
        credentials = self.runtime.credentials
        try:
            lark = AsyncLark(app_id=credentials["app_id"], app_secret=credentials["app_secret"])
            async def read_table(url: str, has_header: bool = True):
                return await lark.sheets.read(url, has_header=has_header)
            df = anyio.run(read_table, table_url)

            if output_format == "csv":
                ret = df.to_csv(index=False)
            elif output_format == "markdown":
                ret = df.to_markdown(index=False)
            else:
                raise ValueError(f"Invalid output format: {output_format}")
            return self.create_text_message(ret)
        except Exception as e:
            return self.create_text_message("Failed to get table. {}".format(e))
