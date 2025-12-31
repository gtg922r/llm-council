from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field
from datetime import datetime

class Stage1Result(BaseModel):
    model: str
    response: str
    status: str

class Stage2Result(BaseModel):
    model: str
    ranking: str
    parsed_ranking: List[str]
    status: str

class Stage3Result(BaseModel):
    model: str
    response: str

class AssistantMessageMetadata(BaseModel):
    label_to_model: Dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: List[Dict[str, Any]] = Field(default_factory=list)

class Message(BaseModel):
    role: str
    content: Optional[str] = None

class FileReference(BaseModel):
    name: str
    file_reference_id: str
    size: Optional[int] = None

class UserMessage(Message):
    role: Literal["user"] = "user"
    files: Optional[List[FileReference]] = None

class AssistantMessage(Message):
    role: Literal["assistant"] = "assistant"
    stage1: List[Stage1Result]
    stage2: List[Stage2Result]
    stage3: Stage3Result
    metadata: AssistantMessageMetadata = Field(default_factory=AssistantMessageMetadata)

class Conversation(BaseModel):
    id: str
    created_at: str
    title: str = "New Conversation"
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: List[Union[UserMessage, AssistantMessage]] = Field(default_factory=list)
