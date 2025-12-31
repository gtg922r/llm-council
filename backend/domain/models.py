"""Domain models for the LLM Council application (Pydantic v2)."""

from __future__ import annotations

from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, Field
from pydantic.aliases import AliasChoices


class FileAttachment(BaseModel):
    """A reference to a blob-stored file attachment."""

    name: str
    file_reference_id: str
    size: int | None = None


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str
    files: list[FileAttachment] = Field(default_factory=list)


class Stage1Result(BaseModel):
    model: str
    response: str = Field(validation_alias=AliasChoices("response", "content"))
    status: Literal["success", "error"] = "success"


class Stage2Result(BaseModel):
    model: str
    ranking: str = Field(validation_alias=AliasChoices("ranking", "content"))
    parsed_ranking: list[str] = Field(default_factory=list)
    status: Literal["success", "error"] = "success"


class Stage3Result(BaseModel):
    model: str
    response: str = Field(validation_alias=AliasChoices("response", "content"))


class AggregateRanking(BaseModel):
    model: str
    average_rank: float
    rankings_count: int


class AssistantMessageMetadata(BaseModel):
    """
    Persisted metadata needed for UI transparency.

    IMPORTANT: This fixes the "persistence amnesia" bug by storing the Stage 2
    anonymization mapping and the computed aggregate rankings alongside the
    assistant message.
    """

    label_to_model: dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: list[AggregateRanking] = Field(default_factory=list)


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    stage1: list[Stage1Result] = Field(default_factory=list)
    stage2: list[Stage2Result] = Field(default_factory=list)
    stage3: Stage3Result | dict[str, Any] | None = None
    metadata: AssistantMessageMetadata | dict[str, Any] = Field(
        default_factory=AssistantMessageMetadata
    )


Message = Annotated[Union[UserMessage, AssistantMessage], Field(discriminator="role")]


class Conversation(BaseModel):
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: list[Message] = Field(default_factory=list)


class ConversationMetadata(BaseModel):
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int


class CouncilRun(BaseModel):
    stage1: list[Stage1Result] = Field(default_factory=list)
    stage2: list[Stage2Result] = Field(default_factory=list)
    stage3: Stage3Result | dict[str, Any] | None = None
    metadata: AssistantMessageMetadata | dict[str, Any] = Field(
        default_factory=AssistantMessageMetadata
    )

