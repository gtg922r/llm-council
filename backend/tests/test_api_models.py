from backend.main import ConversationMetadata, Conversation, CreateConversationRequest
import pytest

def test_conversation_metadata_model():
    """Test that ConversationMetadata includes has_unread."""
    data = {
        "id": "123",
        "created_at": "2024-01-01",
        "title": "Test",
        "is_pinned": False,
        "is_archived": False,
        "message_count": 5,
        "has_unread": True
    }
    model = ConversationMetadata(**data)
    assert model.has_unread is True

def test_conversation_model():
    """Test that Conversation includes has_unread."""
    data = {
        "id": "123",
        "created_at": "2024-01-01",
        "title": "Test",
        "is_pinned": False,
        "is_archived": False,
        "messages": [],
        "has_unread": True
    }
    model = Conversation(**data)
    assert model.has_unread is True
