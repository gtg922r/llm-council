import pytest
import os
import shutil
from backend.storage import (
    create_conversation, 
    get_conversation, 
    list_conversations, 
    DATA_DIR,
    ensure_data_dir
)

@pytest.fixture(autouse=True)
def setup_test_data():
    """Setup a clean test data directory."""
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    ensure_data_dir()
    yield
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

def test_create_conversation_includes_new_fields():
    """Test that new conversations have is_pinned and is_archived fields."""
    conv_id = "test-conv-1"
    conv = create_conversation(conv_id)
    
    assert "is_pinned" in conv
    assert conv["is_pinned"] is False
    assert "is_archived" in conv
    assert conv["is_archived"] is False

def test_list_conversations_includes_new_fields():
    """Test that conversation metadata includes is_pinned and is_archived."""
    conv_id = "test-conv-2"
    create_conversation(conv_id)
    
    conversations = list_conversations()
    assert len(conversations) == 1
    
    meta = conversations[0]
    assert "is_pinned" in meta
    assert meta["is_pinned"] is False
    assert "is_archived" in meta
    assert meta["is_archived"] is False

def test_duplicate_conversation():
    """Test duplicating an existing conversation."""
    from backend.storage import duplicate_conversation
    
    # Create original
    original_id = "original-conv"
    create_conversation(original_id)
    
    # Add a message
    from backend.storage import add_user_message
    add_user_message(original_id, "Hello world")
    
    # Duplicate
    new_id = "duplicated-conv"
    duplicated = duplicate_conversation(original_id, new_id)
    
    assert duplicated["id"] == new_id
    assert duplicated["title"] == "New Conversation (Copy)"
    assert len(duplicated["messages"]) == 1
    assert duplicated["messages"][0]["content"] == "Hello world"
    
    # Verify original still exists
    original = get_conversation(original_id)
    assert original["id"] == original_id
    assert len(original["messages"]) == 1
