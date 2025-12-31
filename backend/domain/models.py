"""Domain models for LLM Council (Ports & Adapters architecture).

These models are intentionally free of infrastructure concerns (filesystem, HTTP, etc.).
They represent the stable data contracts used across the application.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal, Union

from pydantic import BaseModel, Field, model_serializer, model_validator


class FileAttachment(BaseModel):
    """A file attached to a user message.

    New conversations should store `reference_id` only (content is stored in a blob store).
    Legacy conversations may still contain inline `content`.
    """

    name: str
    reference_id: str | None = None
    size: int | None = None

    # Legacy-only (kept for backward compatibility when loading older JSON)
    content: str | None = None

    model_config = {"ser_json_exclude_none": True}

    @model_validator(mode="after")
    def _validate_reference_or_content(self) -> "FileAttachment":
        # Allow empty attachments in defensive parsing scenarios, but if either is present
        # ensure the name exists (it always should via schema) and accept either.
        return self


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str
    files: list[FileAttachment] = Field(default_factory=list)


class Stage1Result(BaseModel):
    model: str
    response: str
    status: Literal["success", "error"]


class Stage2Result(BaseModel):
    model: str
    ranking: str
    parsed_ranking: list[str] = Field(default_factory=list)
    status: Literal["success", "error"]


class AggregateRanking(BaseModel):
    model: str
    average_rank: float
    rankings_count: int


class Stage3Result(BaseModel):
    # Historically some call sites only stored `response`. Keep a safe default so
    # we can load older/partially-mocked data without failing validation.
    model: str = "unknown"
    response: str


class AssistantMessageMetadata(BaseModel):
    """Metadata persisted with assistant messages.

    The frontend historically expects `label_to_model` + `aggregate_rankings`.
    The architecture refactor spec calls the label mapping `anonymized_label_map`.

    We persist both keys in JSON to keep the UI and the spec aligned.
    """

    label_to_model: dict[str, str] = Field(default_factory=dict)
    aggregate_rankings: list[AggregateRanking] = Field(default_factory=list)

    @model_validator(mode="before")
    @classmethod
    def _accept_alternate_keys(cls, data: Any) -> Any:
        if not isinstance(data, dict):
            return data
        if "label_to_model" not in data and "anonymized_label_map" in data:
            data = dict(data)
            data["label_to_model"] = data.get("anonymized_label_map") or {}
        return data

    @model_serializer(mode="wrap")
    def _serialize_with_legacy_and_spec_keys(self, handler):
        data = handler(self)
        # Spec-required alias
        data["anonymized_label_map"] = data.get("label_to_model", {})
        return data


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    stage1: list[Stage1Result] = Field(default_factory=list)
    stage2: list[Stage2Result] = Field(default_factory=list)
    stage3: Stage3Result
    metadata: AssistantMessageMetadata = Field(default_factory=AssistantMessageMetadata)


Message = Union[UserMessage, AssistantMessage]


class Conversation(BaseModel):
    id: str
    created_at: datetime
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: list[Message] = Field(default_factory=list)

    model_config = {"extra": "ignore"}


class ConversationSummary(BaseModel):
    """Conversation metadata for list views."""

    id: str
    created_at: datetime
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int

