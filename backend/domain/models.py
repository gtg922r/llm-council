"""Domain models for LLM Council.

This module contains pure data models representing the core domain entities.
These models are infrastructure-agnostic and focus on business data.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field


class FileReference(BaseModel):
    """Reference to a file stored in the blob store."""
    
    name: str
    blob_id: str  # Reference ID to content in blob store
    size: Optional[int] = None


class FileContext(BaseModel):
    """Inline file context (for API requests before blob storage)."""
    
    name: str
    content: str
    size: Optional[int] = None


class Stage1Result(BaseModel):
    """Result from Stage 1 - individual model response."""
    
    model: str
    response: str
    status: Literal["success", "error"] = "success"


class Stage2Result(BaseModel):
    """Result from Stage 2 - peer ranking/evaluation."""
    
    model: str
    ranking: str  # Full evaluation text
    parsed_ranking: List[str] = Field(default_factory=list)  # Extracted ranking order
    status: Literal["success", "error"] = "success"


class Stage3Result(BaseModel):
    """Result from Stage 3 - chairman synthesis."""
    
    model: str
    response: str


class AggregateRanking(BaseModel):
    """Aggregate ranking score for a model."""
    
    model: str
    average_rank: float
    rankings_count: int


class CouncilMetadata(BaseModel):
    """Metadata from a council run including rankings and label mappings.
    
    This data is persisted with assistant messages to prevent "amnesia" 
    where rankings are lost on page reload.
    """
    
    label_to_model: Dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: List[AggregateRanking] = Field(default_factory=list)


class UserMessage(BaseModel):
    """A user message in a conversation."""
    
    role: Literal["user"] = "user"
    content: str
    files: List[FileReference] = Field(default_factory=list)


class AssistantMessage(BaseModel):
    """An assistant message containing council stages and metadata.
    
    The metadata field persists rankings and label mappings to fix the 
    "persistence amnesia" bug where this data was lost on page reload.
    """
    
    role: Literal["assistant"] = "assistant"
    stage1: List[Stage1Result] = Field(default_factory=list)
    stage2: List[Stage2Result] = Field(default_factory=list)
    stage3: Optional[Stage3Result] = None
    metadata: CouncilMetadata = Field(default_factory=CouncilMetadata)


# Union type for all message types
Message = Union[UserMessage, AssistantMessage]


class Conversation(BaseModel):
    """A conversation containing messages between user and the council."""
    
    id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    title: str = "New Conversation"
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: List[Message] = Field(default_factory=list)


class ConversationMetadata(BaseModel):
    """Lightweight conversation metadata for list views."""
    
    id: str
    created_at: datetime
    title: str = "New Conversation"
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int = 0


# Domain Events for the event-driven architecture
class DomainEvent(BaseModel):
    """Base class for domain events."""
    
    type: str


class Stage1Started(DomainEvent):
    """Emitted when Stage 1 begins."""
    
    type: Literal["stage1_start"] = "stage1_start"
    total: int


class Stage1Progress(DomainEvent):
    """Emitted for Stage 1 progress updates."""
    
    type: Literal["stage1_progress"] = "stage1_progress"
    completed: int
    total: int


class Stage1Complete(DomainEvent):
    """Emitted when Stage 1 completes."""
    
    type: Literal["stage1_complete"] = "stage1_complete"
    data: List[Stage1Result]


class Stage2Started(DomainEvent):
    """Emitted when Stage 2 begins."""
    
    type: Literal["stage2_start"] = "stage2_start"
    total: int


class Stage2Progress(DomainEvent):
    """Emitted for Stage 2 progress updates."""
    
    type: Literal["stage2_progress"] = "stage2_progress"
    completed: int
    total: int


class Stage2Complete(DomainEvent):
    """Emitted when Stage 2 completes."""
    
    type: Literal["stage2_complete"] = "stage2_complete"
    data: List[Stage2Result]
    metadata: CouncilMetadata


class Stage3Started(DomainEvent):
    """Emitted when Stage 3 begins."""
    
    type: Literal["stage3_start"] = "stage3_start"


class Stage3Complete(DomainEvent):
    """Emitted when Stage 3 completes."""
    
    type: Literal["stage3_complete"] = "stage3_complete"
    data: Stage3Result


class TitleGenerated(DomainEvent):
    """Emitted when a conversation title is generated."""
    
    type: Literal["title_complete"] = "title_complete"
    title: str


class CouncilComplete(DomainEvent):
    """Emitted when the full council run completes."""
    
    type: Literal["complete"] = "complete"


class CouncilError(DomainEvent):
    """Emitted when an error occurs during council run."""
    
    type: Literal["error"] = "error"
    message: str


# Union of all domain events
CouncilEvent = Union[
    Stage1Started,
    Stage1Progress,
    Stage1Complete,
    Stage2Started,
    Stage2Progress,
    Stage2Complete,
    Stage3Started,
    Stage3Complete,
    TitleGenerated,
    CouncilComplete,
    CouncilError,
]
