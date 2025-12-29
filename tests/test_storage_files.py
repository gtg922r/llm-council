import pytest
import os
import shutil
from backend.storage import (
    create_conversation, 
    get_conversation, 
    add_user_message,
    DATA_DIR,
    ensure_data_dir
)

@pytest.fixture(autouse=True)
def setup_test_data():
    """Setup a clean test data directory."""
    # Use a temporary directory for testing if possible, 
    # but the storage module uses a fixed DATA_DIR from config.
    # We'll just clear it for now.
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    ensure_data_dir()
    yield
    # Cleanup after test
    # if os.path.exists(DATA_DIR):
    #     shutil.rmtree(DATA_DIR)

def test_add_user_message_with_files():
    """Test that add_user_message correctly stores file objects."""
    conv_id = "test-files-conv"
    create_conversation(conv_id)
    
    files = [
        {"name": "test.txt", "content": "file content", "size": 12},
        {"name": "script.py", "content": "print('hi')"}
    ]
    
    add_user_message(conv_id, "hello with files", files=files)
    
    conv = get_conversation(conv_id)
    assert len(conv["messages"]) == 1
    msg = conv["messages"][0]
    assert msg["content"] == "hello with files"
    assert "files" in msg
    assert len(msg["files"]) == 2
    assert msg["files"][0]["name"] == "test.txt"
    assert msg["files"][0]["size"] == 12

def test_add_user_message_without_files_backward_compatibility():
    """Test that add_user_message still works without files argument."""
    conv_id = "test-no-files-conv"
    create_conversation(conv_id)
    
    # Should not raise TypeError even if 'files' is not passed
    add_user_message(conv_id, "hello without files")
    
    conv = get_conversation(conv_id)
    assert len(conv["messages"]) == 1
    msg = conv["messages"][0]
    assert msg["content"] == "hello without files"
    # It's okay if 'files' is missing or None
    assert msg.get("files") is None
