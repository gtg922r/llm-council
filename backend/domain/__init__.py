"""Domain layer - pure data models and business rules."""

from .models import (
    # Core models
    Conversation,
    ConversationMetadata,
    UserMessage,
    AssistantMessage,
    Message,
    # File handling
    FileReference,
    FileContext,
    # Stage results
    Stage1Result,
    Stage2Result,
    Stage3Result,
    # Metadata
    CouncilMetadata,
    AggregateRanking,
    # Domain Events
    DomainEvent,
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
    CouncilEvent,
)

__all__ = [
    # Core models
    "Conversation",
    "ConversationMetadata",
    "UserMessage",
    "AssistantMessage",
    "Message",
    # File handling
    "FileReference",
    "FileContext",
    # Stage results
    "Stage1Result",
    "Stage2Result",
    "Stage3Result",
    # Metadata
    "CouncilMetadata",
    "AggregateRanking",
    # Domain Events
    "DomainEvent",
    "Stage1Started",
    "Stage1Progress",
    "Stage1Complete",
    "Stage2Started",
    "Stage2Progress",
    "Stage2Complete",
    "Stage3Started",
    "Stage3Complete",
    "TitleGenerated",
    "CouncilComplete",
    "CouncilError",
    "CouncilEvent",
]
