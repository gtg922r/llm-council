"""Domain events emitted by the application service layer."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


StageName = Literal["stage1", "stage2", "stage3"]


class DomainEvent(BaseModel):
    type: str


class StageStarted(DomainEvent):
    type: Literal["stage_started"] = "stage_started"
    stage: StageName
    total: int | None = None


class StageProgress(DomainEvent):
    type: Literal["stage_progress"] = "stage_progress"
    stage: StageName
    completed: int
    total: int | None = None


class StageCompleted(DomainEvent):
    type: Literal["stage_completed"] = "stage_completed"
    stage: StageName
    data: Any = None
    metadata: dict[str, Any] | None = None


class TitleUpdated(DomainEvent):
    type: Literal["title_updated"] = "title_updated"
    title: str


class RunCompleted(DomainEvent):
    type: Literal["run_completed"] = "run_completed"


class ErrorEvent(DomainEvent):
    type: Literal["error"] = "error"
    message: str
    details: dict[str, Any] | None = None


CouncilEvent = (
    StageStarted
    | StageProgress
    | StageCompleted
    | TitleUpdated
    | RunCompleted
    | ErrorEvent
)

