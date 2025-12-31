"""Unit tests for storage.py with domain models."""

import pytest
import tempfile
import shutil
import os
from pathlib import Path

from backend.domain.models import (
    Conversation, UserMessage, AssistantMessage,
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking, FileAttachment
)


class TestStorageWithDomainModels:
    """Tests for storage operations using domain models."""

    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory for tests."""
        data_dir = tmp_path / "conversations"
        data_dir.mkdir(parents=True)
        return str(data_dir)

    def test_save_and_load_conversation_with_metadata(self, temp_data_dir, monkeypatch):
        """Test that conversation with metadata saves and loads correctly."""
        # Patch DATA_DIR
        monkeypatch.setattr("backend.storage.DATA_DIR", temp_data_dir)
        
        from backend import storage
        
        # Create a conversation with domain models
        conversation = Conversation(
            id="test-123",
            title="Test Conversation",
            messages=[
                UserMessage(content="What is 2+2?"),
                AssistantMessage(
                    stage1=[Stage1Response(model="openai/gpt-4o", response="4", status="success")],
                    stage2=[Stage2Ranking(model="openai/gpt-4o", ranking="FINAL RANKING:\n1. Response A", parsed_ranking=["Response A"], status="success")],
                    stage3=Stage3Synthesis(model="google/gemini-2.5-pro", response="The answer is 4."),
                    metadata=CouncilMetadata(
                        label_to_model={"Response A": "openai/gpt-4o"},
                        aggregate_rankings=[AggregateRanking(model="openai/gpt-4o", average_rank=1.0, rankings_count=1)]
                    )
                )
            ]
        )
        
        # Save using typed function
        storage.save_conversation_typed(conversation)
        
        # Load back using typed function
        loaded = storage.get_conversation_typed("test-123")
        
        assert loaded is not None
        assert loaded.id == "test-123"
        assert len(loaded.messages) == 2
        
        # Check user message
        assert loaded.messages[0].role == "user"
        assert loaded.messages[0].content == "What is 2+2?"
        
        # Check assistant message with metadata
        assistant_msg = loaded.messages[1]
        assert assistant_msg.role == "assistant"
        assert assistant_msg.metadata is not None
        assert assistant_msg.metadata.label_to_model["Response A"] == "openai/gpt-4o"
        assert len(assistant_msg.metadata.aggregate_rankings) == 1
        assert assistant_msg.metadata.aggregate_rankings[0].average_rank == 1.0

    def test_metadata_persists_across_reload(self, temp_data_dir, monkeypatch):
        """Test that metadata survives a full save/load cycle (fixes amnesia bug)."""
        monkeypatch.setattr("backend.storage.DATA_DIR", temp_data_dir)
        
        from backend import storage
        
        # Create conversation with metadata
        metadata = CouncilMetadata(
            label_to_model={"Response A": "model1", "Response B": "model2"},
            aggregate_rankings=[
                AggregateRanking(model="model1", average_rank=1.5, rankings_count=2),
                AggregateRanking(model="model2", average_rank=2.5, rankings_count=2),
            ]
        )
        
        conversation = Conversation(
            id="amnesia-test",
            title="Amnesia Test",
            messages=[
                UserMessage(content="Test query"),
                AssistantMessage(
                    stage1=[
                        Stage1Response(model="model1", response="r1", status="success"),
                        Stage1Response(model="model2", response="r2", status="success"),
                    ],
                    stage2=[
                        Stage2Ranking(model="model1", ranking="rank1", parsed_ranking=["Response A", "Response B"], status="success"),
                    ],
                    stage3=Stage3Synthesis(model="chairman", response="synthesis"),
                    metadata=metadata
                )
            ]
        )
        
        # Save
        storage.save_conversation_typed(conversation)
        
        # Load
        loaded = storage.get_conversation_typed("amnesia-test")
        
        # Verify metadata is intact
        assistant_msg = loaded.messages[1]
        assert assistant_msg.metadata.label_to_model["Response A"] == "model1"
        assert assistant_msg.metadata.label_to_model["Response B"] == "model2"
        assert len(assistant_msg.metadata.aggregate_rankings) == 2
        assert assistant_msg.metadata.aggregate_rankings[0].model == "model1"
        assert assistant_msg.metadata.aggregate_rankings[0].average_rank == 1.5

    def test_create_conversation_typed(self, temp_data_dir, monkeypatch):
        """Test creating a new conversation using typed API."""
        monkeypatch.setattr("backend.storage.DATA_DIR", temp_data_dir)
        
        from backend import storage
        
        conversation = storage.create_conversation_typed("new-conv-123")
        
        assert isinstance(conversation, Conversation)
        assert conversation.id == "new-conv-123"
        assert conversation.title == "New Conversation"
        assert len(conversation.messages) == 0

    def test_add_messages_typed(self, temp_data_dir, monkeypatch):
        """Test adding messages using typed API."""
        monkeypatch.setattr("backend.storage.DATA_DIR", temp_data_dir)
        
        from backend import storage
        
        # Create conversation
        storage.create_conversation_typed("msg-test")
        
        # Add user message
        user_msg = UserMessage(content="Hello")
        storage.add_message_typed("msg-test", user_msg)
        
        # Add assistant message with metadata
        assistant_msg = AssistantMessage(
            stage1=[Stage1Response(model="m1", response="hi", status="success")],
            stage2=[],
            stage3=Stage3Synthesis(model="chairman", response="hello back"),
            metadata=CouncilMetadata(
                label_to_model={"Response A": "m1"},
                aggregate_rankings=[]
            )
        )
        storage.add_message_typed("msg-test", assistant_msg)
        
        # Load and verify
        loaded = storage.get_conversation_typed("msg-test")
        assert len(loaded.messages) == 2
        assert loaded.messages[0].content == "Hello"
        assert loaded.messages[1].stage3.response == "hello back"

    def test_list_conversations_returns_metadata(self, temp_data_dir, monkeypatch):
        """Test that list_conversations returns proper metadata."""
        monkeypatch.setattr("backend.storage.DATA_DIR", temp_data_dir)
        
        from backend import storage
        
        # Create multiple conversations
        conv1 = Conversation(id="conv-1", title="First")
        conv2 = Conversation(id="conv-2", title="Second", is_pinned=True)
        
        storage.save_conversation_typed(conv1)
        storage.save_conversation_typed(conv2)
        
        # List conversations
        conversations = storage.list_conversations()
        
        assert len(conversations) == 2
        
        # Find the pinned one
        pinned = [c for c in conversations if c.get("is_pinned")]
        assert len(pinned) == 1
        assert pinned[0]["title"] == "Second"
