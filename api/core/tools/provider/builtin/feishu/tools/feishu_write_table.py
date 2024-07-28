from typing import Any, Union

import anyio
import pandas as pd
from slark import AsyncLark

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool


def extract_table(md_text):
    if not md_text:
        raise ValueError("The Markdown text is empty.")
    lines = md_text.split("\n")
    table_elements = []
    delimeter = "|"
    for line in lines:
        if line.startswith(delimeter) and line.endswith(delimeter):
            cells = [cell.strip() for cell in line.strip(delimeter).split(delimeter)]
            if set(cells[0]) == set(":-"):
                continue
            table_elements.append(cells)
    assert table_elements, "No tables found in the Markdown text."
    assert (
        len(table_elements) > 1
    ), "At least two table lines must be present in the Markdown text."
    for cells in table_elements[1:]:
        assert len(cells) == len(
            table_elements[0]
        ), "All tables must have the same number of columns."
    df = pd.DataFrame(table_elements[1:], columns=table_elements[0])
    return df



class FeishuWriteTableTool(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ) -> Union[ToolInvokeMessage, list[ToolInvokeMessage]]:
        table_url = tool_parameters.get("table_url", "")
        if not table_url:
            return self.create_text_message("Invalid parameter table_url")
        table_data = tool_parameters.get("table_data", "")
        if not table_data:
            return self.create_text_message("Invalid parameter table_data")
        
        credentials = self.runtime.credentials
        try:
            df = extract_table(table_data)
            lark = AsyncLark(app_id=credentials["app_id"], app_secret=credentials["app_secret"])
            async def write_feishu_table(table_url, df, has_header=True):
                return await lark.sheets.write(table_url, data=df, has_header=has_header)
            
            response = anyio.run(write_feishu_table, table_url, df)
            return self.create_text_message(str(response))
        except Exception as e:
            return self.create_text_message("Failed to get table. {}".format(e))
