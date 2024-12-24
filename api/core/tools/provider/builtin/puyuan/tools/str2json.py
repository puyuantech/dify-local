import re
import orjson
from typing import Any
import regex


from core.tools.entities.tool_entities import ToolInvokeMessage
from core.tools.tool.builtin_tool import BuiltinTool


def extract_json_list_from_json_md(input_str) -> str | None:
    match = re.search(
        r'(?:```)?(?:json)?\s*(\[\s*(?:\d+|"[^"]*"|\[[^]]*]|{[\s\S]*?}|null|true|false)?(?:,\s*(?:\d+|"[^"]*"|\[[^]]*]|{[\s\S]*?}|null|true|false))*\s*])\s*(?:```)?',
        input_str, re.DOTALL)
    if match:
        return match.group(1)
    raise ValueError("未提取到有效的JSON字符串，请确认输入包含列表")


def extract_json_dict_from_json_md(input_str) -> str | None:
    match = regex.search(r'(?:```)?(?:json)?\s*({(?:[^{}]|(?R))*})\s*(?:```)?', input_str, regex.DOTALL)
    if match:
        return match.group(1)
    raise ValueError("未提取到有效的JSON字符串，请确认输入包含Json对象")


def loads_json(json_str: str) -> dict | list:
    try:
        return orjson.loads(json_str)
    except Exception as e:
        raise ValueError(f"JSON字符串解析失败:\n{json_str}\n{e}")


class Str2JsonTool(BuiltinTool):
    def _invoke(self, user_id: str, tool_parameters: dict[str, Any]) -> ToolInvokeMessage | list[ToolInvokeMessage]:
        """
        Invoke the tool with the given message.

        Args:
            message (ToolInvokeMessage): The message containing the parameters.

        Returns:
            dict | list: The converted JSON object or list.
        """
        json_string = tool_parameters.get("json_string")
        target_type = tool_parameters.get("target_type", "object")

        if target_type == "list":
            json_string = extract_json_list_from_json_md(json_string)
            return self.create_json_message({'list': loads_json(json_string)})
        else:
            json_string = extract_json_dict_from_json_md(json_string)
            return self.create_json_message(loads_json(json_string))
