import json
from typing import Any

import pydantic


class BaseModel(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", arbitrary_types_allowed=True, use_enum_values=True)


class BaseResponse(BaseModel):
    code: int
    msg: str
    data: Any | None = None


class SuccessResponse(BaseResponse):
    code: int = 200
    msg: str = "success"


class VMCException(Exception):
    def __init__(self, http_code: int = 200, vmc_code: int = 0, msg: str = "", **kwargs):
        self.code = http_code
        self.vmc_code = vmc_code
        self.msg = msg
        self.context = kwargs

    def __str__(self):
        return json.dumps({"code": self.vmc_code, "msg": self.msg, "context": self.context})

    __repr__ = __str__
