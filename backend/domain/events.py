"""Domain events for the LLM Council workflow.

These events represent significant state changes during a council run.
They are yielded by the CouncilService and can be consumed by:
- FastAPI SSE endpoints (for streaming updates)
- Non-streaming endpoints (collecting all events into a final result)
- Test code (for verifying workflow behavior)
"""

from typing import List, Dict, Any, Optional, Literal, Union
from pydantic import BaseModel, Field

from .models import (
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking
)


# =============================================================================
# Base Event
# =============================================================================

class DomainEvent(BaseModel):
    """Base class for all domain events."""
    
    type: str
    """The event type identifier."""


# =============================================================================
# Stage 1 Events
# =============================================================================

class Stage1Started(DomainEvent):
    """Emitted when Stage 1 (individual responses) begins."""
    
    type: Literal["stage1_start"] = "stage1_start"
    total: int
    """Total number of models being queried."""


class Stage1Progress(DomainEvent):
    """Emitted when a model completes in Stage 1."""
    
    type: Literal["stage1_progress"] = "stage1_progress"
    completed: int
    """Number of models that have completed."""
    
    total: int
    """Total number of models."""


class Stage1Complete(DomainEvent):
    """Emitted when Stage 1 is complete."""
    
    type: Literal["stage1_complete"] = "stage1_complete"
    data: List[Stage1Response]
    """All Stage 1 responses."""


# =============================================================================
# Stage 2 Events
# =============================================================================

class Stage2Started(DomainEvent):
    """Emitted when Stage 2 (peer rankings) begins."""
    
    type: Literal["stage2_start"] = "stage2_start"
    total: int
    """Total number of models being queried for rankings."""


class Stage2Progress(DomainEvent):
    """Emitted when a model completes ranking in Stage 2."""
    
    type: Literal["stage2_progress"] = "stage2_progress"
    completed: int
    """Number of models that have completed ranking."""
    
    total: int
    """Total number of models."""


class Stage2Complete(DomainEvent):
    """Emitted when Stage 2 is complete."""
    
    type: Literal["stage2_complete"] = "stage2_complete"
    data: List[Stage2Ranking]
    """All Stage 2 rankings."""
    
    metadata: CouncilMetadata
    """Metadata including label mappings and aggregate rankings."""


# =============================================================================
# Stage 3 Events
# =============================================================================

class Stage3Started(DomainEvent):
    """Emitted when Stage 3 (synthesis) begins."""
    
    type: Literal["stage3_start"] = "stage3_start"


class Stage3Complete(DomainEvent):
    """Emitted when Stage 3 is complete."""
    
    type: Literal["stage3_complete"] = "stage3_complete"
    data: Stage3Synthesis
    """The chairman's synthesis."""


# =============================================================================
# Other Events
# =============================================================================

class TitleGenerated(DomainEvent):
    """Emitted when a conversation title is generated."""
    
    type: Literal["title_complete"] = "title_complete"
    title: str
    """The generated title."""


class CouncilComplete(DomainEvent):
    """Emitted when the entire council run is complete."""
    
    type: Literal["complete"] = "complete"


class CouncilError(DomainEvent):
    """Emitted when an error occurs during the council run."""
    
    type: Literal["error"] = "error"
    message: str
    """Error message."""


# Type alias for any event type
Event = Union[
    Stage1Started, Stage1Progress, Stage1Complete,
    Stage2Started, Stage2Progress, Stage2Complete,
    Stage3Started, Stage3Complete,
    TitleGenerated, CouncilComplete, CouncilError
]
