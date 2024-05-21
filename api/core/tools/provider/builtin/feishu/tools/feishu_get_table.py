from typing import Any, Union

from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool
from feishuconnector import FeishuConnector
import re
import pandas as pd


def get_feishu_table(app_id, app_secret, url):
    fc = FeishuConnector({"default": None})
    fc.init(app_id=app_id, app_secret=app_secret)
    """
    https://puyuan.feishu.cn/wiki/JqfTbpjOqaaqX6sH7YycBHnQndc?table=tblpLi6m92tgzzM5&view=vewp20ORLW
    https://puyuan.feishu.cn/wiki/KUnOwXioIii4MwkmyEHckbyan2b?sheet=ed98fa
    """
    assert not "base" in url, "Only Wiki is supported"
    is_sheet = "sheet" in url
    if is_sheet:
        match = re.findall(r"wiki/(.*)\?sheet=(.*)", url)
    else:
        match = re.findall(r"wiki/(.*)\?table=(.*)&", url)
    assert match, "Invalid parameter table_url"
    assert len(match[0]) == 2, "Invalid parameter table_url"
    if is_sheet:
        records = fc.get_sheet_data(match[0][0], match[0][1])
        return pd.DataFrame(records[1:], columns=records[0])
    else:
        records = fc.get_bitable_records(match[0][0], match[0][1])
        return pd.DataFrame([r["fields"] for r in records])


class FeishuGetTableTool(BuiltinTool):
    def _invoke(
        self, user_id: str, tool_parameters: dict[str, Any]
    ) -> Union[ToolInvokeMessage, list[ToolInvokeMessage]]:
        """
        invoke tools
        API document: https://open.feishu.cn/document/client-docs/bot-v3/add-custom-bot
        https://open.feishu.cn/document/home/agile-project-cycle-management-based-on-bitable/prep-work
        """

        # app_id = tool_parameters.get("app_id", '')
        # if not app_id:
        #     return self.create_text_message('Invalid parameter app_id')

        # app_secret = tool_parameters.get('app_secret', '')
        # if not app_secret:
        #     return self.create_text_message('Invalid parameter app_secret')

        table_url = tool_parameters.get("table_url", "")
        if not table_url:
            return self.create_text_message("Invalid parameter table_url")

        try:
            df = get_feishu_table(
                self.runtime.credentials["app_id"],
                self.runtime.credentials["app_secret"],
                table_url,
            )
            return self.create_text_message(df.to_markdown(index=False))
        except Exception as e:
            return self.create_text_message("Failed to get table. {}".format(e))
