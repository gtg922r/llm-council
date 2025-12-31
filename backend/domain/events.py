"""Domain events emitted by the council workflow service.

These are serialized and sent over SSE, and also used internally for the non-streaming
endpoint (represented as structured events instead of ad-hoc dicts).
"""

from __future__ import annotations

from typing import Any, Literal, Union

from pydantic import BaseModel, Field

from .models import Stage1Result, Stage2Result, Stage3Result, AssistantMessageMetadata


class BaseEvent(BaseModel):
    type: str


class Stage1Start(BaseEvent):
    type: Literal["stage1_start"] = "stage1_start"
    total: int


class Stage1Progress(BaseEvent):
    type: Literal["stage1_progress"] = "stage1_progress"
    completed: int
    total: int


class Stage1Complete(BaseEvent):
    type: Literal["stage1_complete"] = "stage1_complete"
    data: list[Stage1Result]


class Stage2Start(BaseEvent):
    type: Literal["stage2_start"] = "stage2_start"
    total: int


class Stage2Progress(BaseEvent):
    type: Literal["stage2_progress"] = "stage2_progress"
    completed: int
    total: int


class Stage2Complete(BaseEvent):
    type: Literal["stage2_complete"] = "stage2_complete"
    data: list[Stage2Result]
    metadata: AssistantMessageMetadata


class Stage3Start(BaseEvent):
    type: Literal["stage3_start"] = "stage3_start"


class Stage3Complete(BaseEvent):
    type: Literal["stage3_complete"] = "stage3_complete"
    data: Stage3Result


class TitleComplete(BaseEvent):
    type: Literal["title_complete"] = "title_complete"
    data: dict[str, Any]


class Complete(BaseEvent):
    type: Literal["complete"] = "complete"


class Error(BaseEvent):
    type: Literal["error"] = "error"
    message: str


CouncilEvent = Union[
    Stage1Start,
    Stage1Progress,
    Stage1Complete,
    Stage2Start,
    Stage2Progress,
    Stage2Complete,
    Stage3Start,
    Stage3Complete,
    TitleComplete,
    Complete,
    Error,
]

