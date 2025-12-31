"""Unit tests for JsonConversationRepository."""

import pytest
from datetime import datetime, timezone

from backend.domain.models import (
    Conversation, UserMessage, AssistantMessage,
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking
)
from backend.infrastructure.json_repository import JsonConversationRepository


class TestJsonConversationRepository:
    """Tests for the JsonConversationRepository."""

    @pytest.fixture
    def temp_repo(self, tmp_path):
        """Create a repository with a temporary directory."""
        data_dir = tmp_path / "conversations"
        return JsonConversationRepository(str(data_dir))

    def test_create_conversation(self, temp_repo):
        """Test creating a new conversation."""
        conversation = temp_repo.create("test-123")
        
        assert conversation.id == "test-123"
        assert conversation.title == "New Conversation"
        assert len(conversation.messages) == 0

    def test_get_existing_conversation(self, temp_repo):
        """Test retrieving an existing conversation."""
        temp_repo.create("test-456")
        
        loaded = temp_repo.get("test-456")
        
        assert loaded is not None
        assert loaded.id == "test-456"

    def test_get_nonexistent_returns_none(self, temp_repo):
        """Test that getting a nonexistent conversation returns None."""
        result = temp_repo.get("nonexistent")
        
        assert result is None

    def test_save_and_load_preserves_data(self, temp_repo):
        """Test that save/load cycle preserves all data."""
        metadata = CouncilMetadata(
            label_to_model={"Response A": "model1"},
            aggregate_rankings=[AggregateRanking(model="model1", average_rank=1.0, rankings_count=1)]
        )
        
        conversation = Conversation(
            id="full-test",
            title="Full Test",
            messages=[
                UserMessage(content="Hello"),
                AssistantMessage(
                    stage1=[Stage1Response(model="m1", response="hi", status="success")],
                    stage2=[Stage2Ranking(model="m1", ranking="rank", parsed_ranking=["Response A"], status="success")],
                    stage3=Stage3Synthesis(model="chairman", response="synthesis"),
                    metadata=metadata
                )
            ]
        )
        
        temp_repo.save(conversation)
        loaded = temp_repo.get("full-test")
        
        assert loaded.title == "Full Test"
        assert len(loaded.messages) == 2
        assert loaded.messages[1].metadata.label_to_model["Response A"] == "model1"

    def test_delete_removes_conversation(self, temp_repo):
        """Test that delete removes the conversation."""
        temp_repo.create("to-delete")
        assert temp_repo.get("to-delete") is not None
        
        temp_repo.delete("to-delete")
        
        assert temp_repo.get("to-delete") is None

    def test_list_all_returns_metadata(self, temp_repo):
        """Test listing all conversations."""
        temp_repo.create("conv-1")
        temp_repo.create("conv-2")
        
        all_convs = temp_repo.list_all()
        
        assert len(all_convs) == 2
        ids = [c["id"] for c in all_convs]
        assert "conv-1" in ids
        assert "conv-2" in ids

    def test_add_message_user(self, temp_repo):
        """Test adding a user message."""
        temp_repo.create("msg-test")
        
        temp_repo.add_message("msg-test", UserMessage(content="Hello"))
        
        loaded = temp_repo.get("msg-test")
        assert len(loaded.messages) == 1
        assert loaded.messages[0].content == "Hello"

    def test_add_message_assistant_sets_unread(self, temp_repo):
        """Test that adding an assistant message sets has_unread."""
        temp_repo.create("unread-test")
        
        temp_repo.add_message(
            "unread-test",
            AssistantMessage(
                stage1=[],
                stage2=[],
                stage3=Stage3Synthesis(model="m", response="r")
            )
        )
        
        loaded = temp_repo.get("unread-test")
        assert loaded.has_unread is True

    def test_update_title(self, temp_repo):
        """Test updating conversation title."""
        temp_repo.create("title-test")
        
        temp_repo.update_title("title-test", "New Title")
        
        loaded = temp_repo.get("title-test")
        assert loaded.title == "New Title"

    def test_duplicate_conversation(self, temp_repo):
        """Test duplicating a conversation."""
        original = temp_repo.create("original")
        temp_repo.add_message("original", UserMessage(content="Test"))
        temp_repo.update_title("original", "Original Title")
        
        duplicate = temp_repo.duplicate("original", "duplicate")
        
        assert duplicate.id == "duplicate"
        assert duplicate.title == "Original Title (Copy)"
        assert len(duplicate.messages) == 1
        assert duplicate.messages[0].content == "Test"

    def test_update_flags(self, temp_repo):
        """Test updating conversation flags."""
        temp_repo.create("flags-test")
        
        updated = temp_repo.update_flags(
            "flags-test",
            is_pinned=True,
            is_archived=True,
            has_unread=False
        )
        
        assert updated.is_pinned is True
        assert updated.is_archived is True
        assert updated.has_unread is False

    def test_update_flags_partial(self, temp_repo):
        """Test that partial flag updates don't affect other flags."""
        temp_repo.create("partial-flags")
        
        temp_repo.update_flags("partial-flags", is_pinned=True)
        
        loaded = temp_repo.get("partial-flags")
        assert loaded.is_pinned is True
        assert loaded.is_archived is False  # Unchanged
