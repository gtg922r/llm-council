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
