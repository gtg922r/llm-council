from enum import Enum
from typing import List, Dict, Any, Optional, Union
from pydantic import BaseModel, Field
from datetime import datetime, timezone

class MessageRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

class Attachment(BaseModel):
    filename: str
    content_type: str
    file_reference_id: str

class Stage1Result(BaseModel):
    model: str
    response: str
    status: str

class Stage2Result(BaseModel):
    model: str
    ranking: str
    parsed_ranking: List[str]
    status: str

class AggregateRanking(BaseModel):
    model: str
    average_rank: float
    rankings_count: int

class AssistantMetadata(BaseModel):
    label_to_model: Dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: List[AggregateRanking] = Field(default_factory=list)

class Message(BaseModel):
    role: MessageRole
    content: Optional[str] = None

class UserMessage(Message):
    role: MessageRole = MessageRole.USER
    files: Optional[List[Any]] = None

class AssistantMessage(Message):
    role: MessageRole = MessageRole.ASSISTANT
    stage1: List[Stage1Result] = Field(default_factory=list)
    stage2: List[Stage2Result] = Field(default_factory=list)
    stage3: Dict[str, Any] = Field(default_factory=dict)
    metadata: AssistantMetadata = Field(default_factory=AssistantMetadata)

class Conversation(BaseModel):
    id: str
    created_at: datetime
    title: str = "New Conversation"
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: List[Union[UserMessage, AssistantMessage]] = Field(default_factory=list)

class CouncilRun(BaseModel):
    stage1_results: List[Stage1Result]
    stage2_results: List[Stage2Result]
    stage3_result: Dict[str, Any]
    metadata: AssistantMetadata
