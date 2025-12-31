"""Domain models for the LLM Council.

This module defines the core data structures used throughout the application.
These models are pure data containers with no knowledge of infrastructure
(files, APIs, databases).
"""

from datetime import datetime, timezone
from typing import List, Optional, Union, Literal
from pydantic import BaseModel, Field


# =============================================================================
# Stage-specific Models
# =============================================================================

class Stage1Response(BaseModel):
    """A single model's response in Stage 1 (individual responses)."""
    
    model: str
    """The model identifier (e.g., 'openai/gpt-4o')."""
    
    response: str
    """The model's response text."""
    
    status: Literal["success", "error"]
    """Whether the response was successful or an error occurred."""


class Stage2Ranking(BaseModel):
    """A single model's ranking evaluation in Stage 2 (peer review)."""
    
    model: str
    """The model identifier."""
    
    ranking: str
    """The full raw ranking text from the model."""
    
    parsed_ranking: List[str] = Field(default_factory=list)
    """Extracted ranking labels in order (e.g., ['Response A', 'Response B'])."""
    
    status: Literal["success", "error"]
    """Whether the ranking was successful or an error occurred."""


class Stage3Synthesis(BaseModel):
    """The chairman's synthesized final answer in Stage 3."""
    
    model: str
    """The chairman model identifier."""
    
    response: str
    """The synthesized final response."""


# =============================================================================
# Metadata Models
# =============================================================================

class AggregateRanking(BaseModel):
    """Aggregate ranking data for a single model across all peer evaluations."""
    
    model: str
    """The model identifier."""
    
    average_rank: float
    """The average rank position (lower is better)."""
    
    rankings_count: int
    """The number of rankings received."""


class CouncilMetadata(BaseModel):
    """Metadata from a council run, including label mappings and aggregate rankings.
    
    This data was previously ephemeral (returned via API but not persisted).
    It is now stored alongside the AssistantMessage to fix the "amnesia" bug.
    """
    
    label_to_model: dict[str, str] = Field(default_factory=dict)
    """Mapping from anonymous labels to model names (e.g., {'Response A': 'openai/gpt-4o'})."""
    
    aggregate_rankings: List[AggregateRanking] = Field(default_factory=list)
    """Aggregate rankings sorted by average position."""


# =============================================================================
# File Attachment Models
# =============================================================================

class FileAttachment(BaseModel):
    """A file attached to a user message.
    
    Supports both inline content (for backward compatibility) and blob references
    (for the blob-store split that keeps conversation JSON small).
    """
    
    name: str
    """The filename."""
    
    content: Optional[str] = None
    """The file content (text only). Used for inline storage or when resolved from blob."""
    
    size: Optional[int] = None
    """The file size in bytes."""
    
    blob_reference_id: Optional[str] = None
    """Reference ID for content stored in the blob store.
    
    If set, the actual content is stored in the blob store and should be
    resolved via BlobStore.get_text(blob_reference_id) when needed.
    """
    
    @property
    def is_blob_reference(self) -> bool:
        """Check if this attachment uses blob storage."""
        return self.blob_reference_id is not None


# =============================================================================
# Message Models
# =============================================================================

class UserMessage(BaseModel):
    """A message from the user."""
    
    role: Literal["user"] = "user"
    """The message role."""
    
    content: str
    """The user's message content."""
    
    files: Optional[List[FileAttachment]] = None
    """Optional file attachments."""


class AssistantMessage(BaseModel):
    """A message from the assistant (LLM Council response).
    
    Contains all three stages of the council deliberation process,
    plus metadata that was previously lost on page reload.
    """
    
    role: Literal["assistant"] = "assistant"
    """The message role."""
    
    stage1: List[Stage1Response] = Field(default_factory=list)
    """Individual model responses from Stage 1."""
    
    stage2: List[Stage2Ranking] = Field(default_factory=list)
    """Peer rankings from Stage 2."""
    
    stage3: Optional[Stage3Synthesis] = None
    """Chairman's synthesis from Stage 3."""
    
    metadata: Optional[CouncilMetadata] = None
    """Council metadata including label mappings and aggregate rankings.
    
    This field fixes the 'amnesia' bug where this data was previously
    only returned via API but not persisted to storage.
    """


# Type alias for any message type
Message = Union[UserMessage, AssistantMessage]


# =============================================================================
# Conversation Model
# =============================================================================

class Conversation(BaseModel):
    """A conversation containing a sequence of messages."""
    
    id: str
    """Unique identifier for the conversation."""
    
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    """When the conversation was created."""
    
    title: str = "New Conversation"
    """The conversation title."""
    
    is_pinned: bool = False
    """Whether the conversation is pinned."""
    
    is_archived: bool = False
    """Whether the conversation is archived."""
    
    has_unread: bool = False
    """Whether the conversation has unread messages."""
    
    messages: List[Union[UserMessage, AssistantMessage]] = Field(default_factory=list)
    """The messages in this conversation."""


# =============================================================================
# Council Workflow Models
# =============================================================================

class CouncilRun(BaseModel):
    """Represents a complete council workflow run.
    
    This model encapsulates all the data from a single council deliberation,
    making it easy to pass around and test the workflow logic.
    """
    
    user_query: str
    """The original user query that initiated this run."""
    
    stage1: List[Stage1Response] = Field(default_factory=list)
    """Stage 1 responses."""
    
    stage2: List[Stage2Ranking] = Field(default_factory=list)
    """Stage 2 rankings."""
    
    stage3: Optional[Stage3Synthesis] = None
    """Stage 3 synthesis."""
    
    metadata: Optional[CouncilMetadata] = None
    """Metadata including label mappings and aggregate rankings."""
