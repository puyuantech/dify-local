import enum
import time
from enum import Enum
from typing import List, Union

from pydantic import BaseModel, Field

from ._base import SuccessResponse
from .knowledge import KnowledgeFileSearchDoc


class SubQueryParams(BaseModel):
    message_id: str
    sub_query: str
    sub_query_retrival: str
    sub_query_response: str


class IntentClassification(Enum):
    RETRIEVAL = "1"
    NO_RETRIEVAL = "0"


class MessageType:
    CONDENSE = "condense"
    """condense 结果消息类型"""
    DECOMPOSE = "decompose"
    """问题拆分结果消息类型"""
    SUBQUERY_GENERATION = "subquery_generation"
    """子问题回答消息类型"""
    PROMPT = "prompt"
    """Prompt 消息类型"""
    STEP_BACK = "step_back"
    """step back 结果消息类型"""
    HYDE = "HyDE"
    """HyDE 结果消息类型"""
    GENERATION = "generation"
    """LLM 生成结果消息类型"""
    RETRIEVAL = "retrieval"
    """检索结果消息类型"""
    NONCE = "nonce"
    """nonce 消息类型"""
    INTENT = "intent"
    """intent 消息类型"""
    QALoaderPrompt = "prompt"
    """intent 消息类型"""


class SubQuery(BaseModel):
    query: str
    """sub query 的 query，如果生成失败，则是原 query"""
    knowledge_base_name: Union[str, List[str], None] = None
    """sub query 对应的知识库名称"""
    knowledge_base_id: Union[str, List[str], None] | None = None
    """sub query 对应的知识库 id"""
    can_match_database: bool = False
    """是否可以匹配到数据库中的知识库，和 knowledge_base_id 效果一样"""


class ChatResponse(SuccessResponse):
    msg_type: str
    """消息类型"""
    message_id: str | None = None
    """消息 id"""
    debug_info: dict | None = None
    """调试信息"""
    verbose_level: int = 0
    """verbose 等级"""
    timestamp: int = Field(default_factory=lambda: int(time.time() * 1000))
    """时间戳，单位 ms"""


class NonceResponse(ChatResponse):
    msg_type: str = MessageType.NONCE
    data: str


class CondenseResponse(ChatResponse):
    msg_type: str = MessageType.CONDENSE
    verbose_level: int = 2
    data: str


class DecomposeResponse(ChatResponse):
    msg_type: str = MessageType.DECOMPOSE
    """消息类型"""
    verbose_level: int = 1
    """verbose 等级"""
    data: list[SubQuery] | None = None
    """生成的 sub query 列表，如果生成失败，则为 None"""
    failed: bool = False
    """生成失败或者知识库全部匹配失败时为 True，否则为 False"""
    end: bool = False
    """是否是最后一个 sub query， 始终为 True"""


class IntentResponse(ChatResponse):
    msg_type: str = MessageType.INTENT
    verbose_level: int = 1
    data: IntentClassification
    """intent"""


class PromptStage(enum.Enum):
    DECOMPOSE = "decompose"
    """拆分阶段"""
    SUBQUERY = "subquery"
    """子问题阶段"""
    FINAL = "final"
    """最终生成阶段"""


class PromptResponse(ChatResponse):
    msg_type: str = MessageType.PROMPT
    stage: PromptStage | None = None
    """Prompt 的阶段"""
    verbose_level: int = 2
    query: str
    """生成 prompt 所使用的 query"""
    data: str
    """生成的 prompt"""


class QALoaderQueryResponse(ChatResponse):
    msg_type: str = MessageType.QALoaderPrompt
    verbose_level: int = 3
    query: str
    """生成 prompt 所使用的 query"""
    data: str
    """生成的 prompt"""
    context: Union[str, List[dict], None] | None = None
    """retrieval context"""
    is_support: bool = True
    """qa loader 是否有 doc 被有效检索"""


class StepBackResponse(ChatResponse):
    msg_type: str = MessageType.STEP_BACK
    verbose_level: int = 2
    data: str


class HyDEResponse(ChatResponse):
    msg_type: str = MessageType.HYDE
    verbose_level: int = 2
    data: str


class GenerationResponse(ChatResponse):
    msg_type: str = MessageType.GENERATION
    verbose_level: int = 0
    data: str


class SubqueryGeneration(BaseModel):
    query: str
    answer: str


class SubqueryGenerationResponse(ChatResponse):
    msg_type: str = MessageType.SUBQUERY_GENERATION
    verbose_level: int = 1
    data: SubqueryGeneration


class RetrievalResponse(ChatResponse):
    msg_type: str = MessageType.RETRIEVAL
    verbose_level: int = 1
    query: str
    """检索的 query"""
    data: List[KnowledgeFileSearchDoc] = Field(default_factory=list)
    """检索到的文档"""
    end: bool = True
    """多轮检索中，是否是最后一个 retrieval"""


class ErrorChatResponse(ChatResponse):
    code: int = 500
    msg_type: str = "error"
    verbose_level: int = 0
    data: str
