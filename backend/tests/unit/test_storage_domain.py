import pytest
import os
from datetime import datetime, timezone
from backend import storage
from backend.domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage, 
    AssistantMetadata,
    AggregateRanking
)

def test_save_load_conversation_with_metadata(tmp_path, monkeypatch):
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    
    conv_id = "test-conv"
    
    # Create metadata
    metadata = AssistantMetadata(
        label_to_model={"Response A": "gpt-4"},
        aggregate_rankings=[AggregateRanking(model="gpt-4", average_rank=1.0, rankings_count=1)]
    )
    
    # Create conversation domain model
    conv = Conversation(
        id=conv_id,
        created_at=datetime.now(timezone.utc),
        title="Test Conversation",
        messages=[
            UserMessage(content="Hello"),
            AssistantMessage(
                stage1=[],
                stage2=[],
                stage3={"model": "chairman", "response": "Hi there"},
                metadata=metadata
            )
        ]
    )
    
    # Save using storage (currently expects dict, so we'll see if it works with model_dump)
    storage.save_conversation(conv.model_dump())
    
    # Load
    loaded_data = storage.get_conversation(conv_id)
    assert loaded_data is not None
    
    # Re-instantiate domain model
    loaded_conv = Conversation(**loaded_data)
    
    assert loaded_conv.id == conv_id
    assert len(loaded_conv.messages) == 2
    assert isinstance(loaded_conv.messages[1], AssistantMessage)
    assert loaded_conv.messages[1].metadata.label_to_model["Response A"] == "gpt-4"
    assert loaded_conv.messages[1].metadata.aggregate_rankings[0].model == "gpt-4"
