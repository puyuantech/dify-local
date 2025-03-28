from typing import Any, Union

from loguru import logger
from slark import Lark

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
        has_header = tool_parameters.get("has_header", "true").lower() == "true"
        credentials = self.runtime.credentials

        logger.info(
            f"Getting table from {table_url}, output_format={output_format}"
            f", has_header={has_header}, type(has_header)={type(has_header)}"
        )
        try:
            lark = Lark(app_id=credentials["app_id"], app_secret=credentials["app_secret"])
            df = lark.sheets.read(table_url, has_header=has_header)

            if output_format == "csv":
                ret = df.to_csv(index=False)
            elif output_format == "markdown":
                ret = df.to_markdown(index=False)
            else:
                raise ValueError(f"Invalid output format: {output_format}")
            return self.create_text_message(ret)
        except Exception as e:
            return self.create_text_message("Failed to get table. {}".format(e))
