import re
from typing import Any, Union

import pandas as pd
from feishuconnector import FeishuConnector

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
            if set(cells[0]) == set("-"):
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


def write_feishu_table(app_id, app_secret, table_url, table_data):
    fc = FeishuConnector({"default": None})
    fc.init(app_id=app_id, app_secret=app_secret)
    assert "sheet" in table_url, "Only Wiki sheet is supported currently"
    match = re.findall(r"wiki/(.*)\?sheet=(.*)", table_url)
    assert match, "Invalid parameter table_url"
    assert len(match[0]) == 2, "Invalid parameter table_url"
    df = extract_table(table_data)
    return fc.write_sheet_data(
        match[0][0], match[0][1], [df.columns.tolist()] + df.values.tolist()
    )


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
        try:
            ret = write_feishu_table(
                self.runtime.credentials["app_id"],
                self.runtime.credentials["app_secret"],
                table_url,
                table_data,
            )
            return self.create_text_message(str(ret))
        except Exception as e:
            return self.create_text_message("Failed to get table. {}".format(e))
