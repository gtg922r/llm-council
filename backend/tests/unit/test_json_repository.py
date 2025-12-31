"""Unit tests for the JsonConversationRepository."""

import pytest
import json
from datetime import datetime, timezone

from backend.infrastructure.json_repository import JsonConversationRepository
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


class TestJsonConversationRepository:
    """Tests for the JsonConversationRepository class."""
    
    @pytest.fixture
    def temp_data_dir(self, tmp_path):
        """Create a temporary data directory."""
        data_dir = tmp_path / "conversations"
        data_dir.mkdir()
        return str(data_dir)
    
    @pytest.fixture
    def repo(self, temp_data_dir):
        """Create a repository with temp directory."""
        return JsonConversationRepository(data_dir=temp_data_dir)
    
    def test_save_and_get_conversation(self, repo):
        """Test saving and retrieving a conversation."""
        conv = Conversation(
            id="test-123",
            title="Test Conversation",
            messages=[
                UserMessage(content="Hello"),
                AssistantMessage(
                    stage1=[Stage1Result(model="m1", response="Hi", status="success")],
                    stage2=[],
                    stage3=Stage3Result(model="chair", response="Final"),
                    metadata=CouncilMetadata()
                )
            ]
        )
        
        repo.save(conv)
        
        retrieved = repo.get("test-123")
        
        assert retrieved is not None
        assert retrieved.id == "test-123"
        assert retrieved.title == "Test Conversation"
        assert len(retrieved.messages) == 2
        assert retrieved.messages[0].content == "Hello"
    
    def test_get_nonexistent_conversation(self, repo):
        """Test retrieving a non-existent conversation."""
        result = repo.get("nonexistent")
        assert result is None
    
    def test_list_conversations(self, repo):
        """Test listing all conversations."""
        for i in range(3):
            conv = Conversation(id=f"conv-{i}", title=f"Conversation {i}")
            repo.save(conv)
        
        metadata_list = repo.list()
        
        assert len(metadata_list) == 3
        # Should be sorted by creation time, newest first
        # Since all created at roughly same time, order might vary
        ids = {m.id for m in metadata_list}
        assert ids == {"conv-0", "conv-1", "conv-2"}
    
    def test_delete_conversation(self, repo):
        """Test deleting a conversation."""
        conv = Conversation(id="to-delete", title="Will be deleted")
        repo.save(conv)
        
        # Verify it exists
        assert repo.get("to-delete") is not None
        
        # Delete it
        repo.delete("to-delete")
        
        # Verify it's gone
        assert repo.get("to-delete") is None
    
    def test_delete_nonexistent_conversation(self, repo):
        """Test deleting a non-existent conversation doesn't raise."""
        repo.delete("nonexistent")  # Should not raise
    
    def test_metadata_persistence(self, repo):
        """Test that metadata is persisted correctly (the amnesia fix)."""
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
        
        conv = Conversation(
            id="metadata-test",
            messages=[
                UserMessage(content="Test"),
                AssistantMessage(
                    stage1=[],
                    stage2=[],
                    stage3=Stage3Result(model="chair", response="Done"),
                    metadata=metadata
                )
            ]
        )
        
        repo.save(conv)
        
        # Reload and verify metadata is preserved
        retrieved = repo.get("metadata-test")
        
        assert retrieved is not None
        assistant_msg = retrieved.messages[1]
        assert isinstance(assistant_msg, AssistantMessage)
        
        assert assistant_msg.metadata.label_to_model["Response A"] == "openai/gpt-4"
        assert len(assistant_msg.metadata.aggregate_rankings) == 2
        assert assistant_msg.metadata.aggregate_rankings[0].average_rank == 1.5
    
    def test_file_references_persistence(self, repo):
        """Test that file references are persisted correctly."""
        conv = Conversation(
            id="files-test",
            messages=[
                UserMessage(
                    content="Check these files",
                    files=[
                        FileReference(name="code.py", blob_id="abc123", size=1024),
                        FileReference(name="data.json", blob_id="def456", size=512)
                    ]
                )
            ]
        )
        
        repo.save(conv)
        
        retrieved = repo.get("files-test")
        
        assert retrieved is not None
        user_msg = retrieved.messages[0]
        assert isinstance(user_msg, UserMessage)
        assert len(user_msg.files) == 2
        assert user_msg.files[0].name == "code.py"
        assert user_msg.files[0].blob_id == "abc123"
    
    def test_update_conversation(self, repo):
        """Test updating an existing conversation."""
        conv = Conversation(id="update-test", title="Original Title")
        repo.save(conv)
        
        # Update title
        conv.title = "Updated Title"
        conv.is_pinned = True
        repo.save(conv)
        
        retrieved = repo.get("update-test")
        
        assert retrieved.title == "Updated Title"
        assert retrieved.is_pinned is True
