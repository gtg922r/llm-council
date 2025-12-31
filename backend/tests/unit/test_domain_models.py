"""Unit tests for domain models."""

import pytest
from datetime import datetime, timezone

from backend.domain.models import (
    Conversation,
    UserMessage,
    AssistantMessage,
    Stage1Result,
    Stage2Result,
    Stage3Result,
    CouncilMetadata,
    AggregateRanking,
    FileReference,
)


class TestConversation:
    """Tests for the Conversation model."""
    
    def test_create_empty_conversation(self):
        """Test creating a new empty conversation."""
        conv = Conversation(id="test-123")
        
        assert conv.id == "test-123"
        assert conv.title == "New Conversation"
        assert conv.is_pinned is False
        assert conv.is_archived is False
        assert conv.has_unread is False
        assert conv.messages == []
    
    def test_conversation_with_messages(self):
        """Test conversation with messages."""
        user_msg = UserMessage(content="Hello")
        assistant_msg = AssistantMessage(
            stage1=[Stage1Result(model="test/model", response="Hello back", status="success")],
            stage2=[],
            stage3=Stage3Result(model="test/chairman", response="Final answer"),
            metadata=CouncilMetadata()
        )
        
        conv = Conversation(
            id="test-456",
            messages=[user_msg, assistant_msg]
        )
        
        assert len(conv.messages) == 2
        assert conv.messages[0].role == "user"
        assert conv.messages[1].role == "assistant"


class TestUserMessage:
    """Tests for the UserMessage model."""
    
    def test_user_message_simple(self):
        """Test creating a simple user message."""
        msg = UserMessage(content="What is the capital of France?")
        
        assert msg.role == "user"
        assert msg.content == "What is the capital of France?"
        assert msg.files == []
    
    def test_user_message_with_files(self):
        """Test user message with file references."""
        files = [
            FileReference(name="code.py", blob_id="abc123", size=1024),
            FileReference(name="data.json", blob_id="def456", size=512)
        ]
        msg = UserMessage(content="Analyze these files", files=files)
        
        assert len(msg.files) == 2
        assert msg.files[0].name == "code.py"
        assert msg.files[0].blob_id == "abc123"


class TestAssistantMessage:
    """Tests for the AssistantMessage model."""
    
    def test_assistant_message_with_metadata(self):
        """Test assistant message preserves metadata (persistence fix)."""
        metadata = CouncilMetadata(
            label_to_model={
                "Response A": "openai/gpt-4",
                "Response B": "anthropic/claude-3"
            },
            aggregate_rankings=[
                AggregateRanking(model="openai/gpt-4", average_rank=1.5, rankings_count=3),
                AggregateRanking(model="anthropic/claude-3", average_rank=2.0, rankings_count=3)
            ]
        )
        
        msg = AssistantMessage(
            stage1=[Stage1Result(model="openai/gpt-4", response="Answer 1", status="success")],
            stage2=[Stage2Result(model="openai/gpt-4", ranking="1. Response A", parsed_ranking=["Response A"], status="success")],
            stage3=Stage3Result(model="google/gemini-pro", response="Final synthesis"),
            metadata=metadata
        )
        
        assert msg.role == "assistant"
        assert len(msg.metadata.label_to_model) == 2
        assert len(msg.metadata.aggregate_rankings) == 2
        assert msg.metadata.aggregate_rankings[0].model == "openai/gpt-4"
        assert msg.metadata.aggregate_rankings[0].average_rank == 1.5


class TestStageResults:
    """Tests for stage result models."""
    
    def test_stage1_result(self):
        """Test Stage1Result model."""
        result = Stage1Result(
            model="openai/gpt-4",
            response="This is the answer",
            status="success"
        )
        assert result.model == "openai/gpt-4"
        assert result.status == "success"
    
    def test_stage2_result(self):
        """Test Stage2Result model."""
        result = Stage2Result(
            model="anthropic/claude-3",
            ranking="Response A is best.\n\nFINAL RANKING:\n1. Response A\n2. Response B",
            parsed_ranking=["Response A", "Response B"],
            status="success"
        )
        assert result.parsed_ranking == ["Response A", "Response B"]
    
    def test_stage3_result(self):
        """Test Stage3Result model."""
        result = Stage3Result(
            model="google/gemini-pro",
            response="The council has decided..."
        )
        assert result.model == "google/gemini-pro"


class TestSerialization:
    """Tests for model serialization."""
    
    def test_conversation_to_json(self):
        """Test conversation serializes to JSON correctly."""
        conv = Conversation(
            id="test-789",
            title="Test Conv",
            messages=[
                UserMessage(content="Hello"),
                AssistantMessage(
                    stage1=[Stage1Result(model="test/model", response="Hi", status="success")],
                    stage2=[],
                    stage3=Stage3Result(model="test/chair", response="Done"),
                    metadata=CouncilMetadata(
                        label_to_model={"Response A": "test/model"},
                        aggregate_rankings=[AggregateRanking(model="test/model", average_rank=1.0, rankings_count=1)]
                    )
                )
            ]
        )
        
        # Serialize to dict
        data = conv.model_dump()
        
        assert data["id"] == "test-789"
        assert len(data["messages"]) == 2
        assert data["messages"][1]["metadata"]["label_to_model"]["Response A"] == "test/model"
