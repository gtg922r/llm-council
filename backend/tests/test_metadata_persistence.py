"""Tests to verify that metadata (aggregate rankings) persists across save/load cycles."""

import pytest
from backend import storage


def test_add_assistant_message_with_metadata(tmp_path, monkeypatch):
    """Test that add_assistant_message saves metadata including aggregate rankings."""
    # Patch DATA_DIR to use temp directory
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    
    # Create a conversation
    conv = storage.create_conversation("test-metadata")
    
    # Add an assistant message with metadata
    stage1 = [{"model": "model1", "response": "answer", "status": "success"}]
    stage2 = [{"model": "model1", "ranking": "FINAL RANKING:\n1. Response A", "parsed_ranking": ["Response A"], "status": "success"}]
    stage3 = {"model": "chairman", "response": "synthesis"}
    metadata = {
        "label_to_model": {"Response A": "model1"},
        "aggregate_rankings": [
            {"model": "model1", "average_rank": 1.0, "rankings_count": 1}
        ]
    }
    
    storage.add_assistant_message(
        "test-metadata",
        stage1,
        stage2,
        stage3,
        metadata=metadata
    )
    
    # Reload the conversation
    loaded = storage.get_conversation("test-metadata")
    
    # Verify metadata was saved
    assert len(loaded["messages"]) == 1
    assistant_msg = loaded["messages"][0]
    assert assistant_msg["role"] == "assistant"
    assert "metadata" in assistant_msg
    assert assistant_msg["metadata"]["label_to_model"]["Response A"] == "model1"
    assert len(assistant_msg["metadata"]["aggregate_rankings"]) == 1
    assert assistant_msg["metadata"]["aggregate_rankings"][0]["model"] == "model1"
    assert assistant_msg["metadata"]["aggregate_rankings"][0]["average_rank"] == 1.0


def test_metadata_survives_reload_cycle(tmp_path, monkeypatch):
    """Test the complete cycle of saving and loading metadata (fixes amnesia bug)."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    
    # Create conversation and add message with metadata
    storage.create_conversation("amnesia-fix")
    
    metadata = {
        "label_to_model": {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-3"
        },
        "aggregate_rankings": [
            {"model": "openai/gpt-4o", "average_rank": 1.5, "rankings_count": 2},
            {"model": "anthropic/claude-3", "average_rank": 2.5, "rankings_count": 2}
        ]
    }
    
    storage.add_assistant_message(
        "amnesia-fix",
        stage1=[{"model": "m1", "response": "r1", "status": "success"}],
        stage2=[{"model": "m1", "ranking": "rank", "parsed_ranking": [], "status": "success"}],
        stage3={"model": "chairman", "response": "final"},
        metadata=metadata
    )
    
    # Load conversation - simulating page reload
    loaded = storage.get_conversation("amnesia-fix")
    
    # Verify all metadata is intact
    msg = loaded["messages"][0]
    assert msg["metadata"]["label_to_model"]["Response A"] == "openai/gpt-4o"
    assert msg["metadata"]["label_to_model"]["Response B"] == "anthropic/claude-3"
    
    rankings = msg["metadata"]["aggregate_rankings"]
    assert len(rankings) == 2
    assert rankings[0]["model"] == "openai/gpt-4o"
    assert rankings[0]["average_rank"] == 1.5
    assert rankings[1]["model"] == "anthropic/claude-3"
    assert rankings[1]["average_rank"] == 2.5


def test_add_assistant_message_without_metadata_still_works(tmp_path, monkeypatch):
    """Test backward compatibility - messages without metadata still work."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    
    storage.create_conversation("no-metadata")
    
    # Add message without metadata (backward compatibility)
    storage.add_assistant_message(
        "no-metadata",
        stage1=[{"model": "m1", "response": "r1", "status": "success"}],
        stage2=[],
        stage3={"model": "chairman", "response": "final"}
    )
    
    loaded = storage.get_conversation("no-metadata")
    msg = loaded["messages"][0]
    
    # Should work but metadata should be absent or None
    assert msg["role"] == "assistant"
    assert msg["stage3"]["response"] == "final"
    # metadata key might not exist if not provided
    assert msg.get("metadata") is None
