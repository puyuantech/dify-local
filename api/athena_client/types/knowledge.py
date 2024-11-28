import enum
import json
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator

from ._base import SuccessResponse


class KnowledgeDetailsQuery(BaseModel):
    knowledge_base_id: str
    return_files: bool = True


class KnowledgeDetailsQueryV2(BaseModel):
    id: str


class KnowledgeBatchDetailsBody(BaseModel):
    knowledge_base_ids: List[str]
    return_files: bool = True


class KnowledgeFileListQuery(BaseModel):
    knowledge_base_id: str


class KnowledgeFileSearchParams(BaseModel):
    knowledge_base_id: str
    query: str
    top_k: int
    score_threshold: float
    strategy: Literal[
        "normal", "bm25", "rag_fusion", "self_rag", "hybrid", "bm25_only", "es_only"
    ] = "normal"


class KnowledgeFileSearchDoc(BaseModel):
    id: int | str | None = None
    content: str
    score: float | None = None
    source: str | None = None
    knowledge_file_id: str | None = None
    metadata: dict | None = None


class KnowledgeFileSearchResponse(SuccessResponse):
    data: List[KnowledgeFileSearchDoc]


class KnowledgeFileDownloadQuery(BaseModel):
    """下载文件请求参数，二选一"""

    knowledge_file_id: Optional[str] = None
    """文件id"""
    key: Optional[str] = None
    """文件唯一标识"""


class KnowledgeFileDeleteParams(BaseModel):
    knowledge_file_id: str


class FileStatus(enum.Enum):
    UPLOADED = "UPLOADED"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INACTIVE = "INACTIVE"


class KnowledgeFileUpdateParams(BaseModel):
    knowledge_file_id: str
    file_status: FileStatus | None = None
    file_name: str | None = None


class KnowledgeFileDetailParams(BaseModel):
    knowledge_file_id: str


class KnowledgeCreateParams(BaseModel):
    name: str = Field(alias="knowledge_base_name")
    embed_model: str = Field(alias="embedding_model")
    vs_type: str = Field(alias="vector_type")
    description: str = ""
    tags: list[str] = []
    is_general: bool = False


class KnowledgeUpdateParams(BaseModel):
    name: str | None = Field(alias="knowledge_base_name", default=None)
    embed_model: str | None = Field(alias="embedding_model", default=None)
    vs_type: str | None = Field(alias="vector_type", default=None)
    description: str | None = None
    tags: list[str] | None = None
    is_general: bool | None = None


class KnowledgeUpdateParams(KnowledgeUpdateParams):
    knowledge_base_id: str


class KnowledgeDeleteParams(BaseModel):
    knowledge_base_id: str
    # knowledge_base_name: str


class Message(BaseModel):
    role: Literal["user", "assistant"]
    """消息角色"""
    """消息内容"""
    content: str


class KnowledgeChatParams(BaseModel):
    app_id: str
    """对话应用的id"""
    user_id: str = None
    """用户id"""
    session_id: str = None
    """会话id"""

    query: str
    """用户输入的query"""
    history: List[Message] = []
    """历史对话"""
    kb_ids: List[str] = []
    """知识库id"""
    # kb_names: List = []
    verbose: int = 0
    """对话的详细程度"""

    is_multiple_project_query: bool = False
    """是否多项目查询，必须指定kb_ids"""

    is_qa_query: bool = True
    """是否 qa 问答模式"""

    @model_validator(mode="after")
    def validate_params(cls, model: "KnowledgeChatParams"):  # noqa: N805
        if model.is_multiple_project_query and model.kb_ids == []:
            msg = "kb_ids is required when is_multiple_project_query is True"
            raise ValueError(msg)
        return model


class ChatVoteParams(BaseModel):
    message_id: str
    vote: Literal[-1, 0, 1]
    vote_reason: Optional[str] = None
    vote_message: Optional[str] = None


class MessageSearchOrderby(BaseModel):
    order_by: Literal["created_at", "updated_at", "vote"]
    desc: bool = False


class MessageSearchParams(BaseModel):
    page: int = Field(default=1, ge=1, description="页码")
    page_size: int = Field(default=10, ge=1, description="每页数量")
    app_id: str | None = Field(default=None, description="应用id/None表示所有")
    keyword: str | None = Field(default=None, description="关键词/None表示所有")
    vote: Literal[-1, 0, 1] | None = Field(
        default=None, description="投票/None表示所有"
    )
    order_bys: List[MessageSearchOrderby] = Field(default=[], description="排序")
    filter_time: List[str] = Field(default=[], description="日期筛选")


class LoaderParams(BaseModel):
    chunk_size: int = 1000
    overlap_size: int = 50
    add_start_index: bool = True
    has_watermark: Optional[bool] = False

    def get_splitter_params(self):
        return {
            "chunk_size": self.chunk_size,
            "chunk_overlap": self.overlap_size,
            # "add_start_index": self.add_start_index,
        }

    def get_loader_params(self):
        return {"has_watermark": self.has_watermark}


class KnowledgeFileUploadQuery(BaseModel):
    knowledge_base_id: str
    document_loader_name: str = ""
    text_splitter_name: str = ""
    loader_params: str = "{}"
    tags: str = "{}"

    def model_post_init(self, __context: Any) -> None:
        params = LoaderParams.model_validate_json(self.loader_params)
        self.loader_params = params.model_dump_json()

    @model_validator(mode="after")
    @classmethod
    def validate_params(cls, model: "KnowledgeFileUploadQuery"):
        try:
            json.loads(model.tags)
        except json.JSONDecodeError:
            raise ValueError("tags must be a valid json string")
        return model


class DocumentType(enum.Enum):
    NORMAL = "NORMAL"
    QA = "QA"


class KnowledgeBaseFileUploadPostParam(BaseModel):
    kb_id: str
    document_type: DocumentType
    tags: Optional[str] = None

    @model_validator(mode="after")
    @classmethod
    def validate_params(cls, model: "KnowledgeBaseFileUploadPostParam"):
        if model.tags is not None:
            json.loads(model.tags)
        return model


class KnowledgeBaseFileActionPostParam(BaseModel):
    action: Literal["delete", "process"]
    kf_ids: list[str]


class KnowledgeBaseFileListQuery(BaseModel):
    id: str
    search_key: Optional[str] = None


class KnowledgePostParams(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    embed_model: Optional[str] = None
    vs_type: Optional[str] = None
    description: Optional[str] = None
    tags: Optional[list[str]] = None
    labels: Optional[list[str]] = None
    is_hidden: Optional[bool] = None
    is_general: Optional[bool] = None
