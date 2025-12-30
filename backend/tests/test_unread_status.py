import os
import pytest
from backend import storage

def test_create_conversation_has_default_unread_status():
    """Test that a new conversation has has_unread=False by default."""
    conv_id = "test_unread_init"
    # Ensure cleanup
    try:
        storage.delete_conversation(conv_id)
    except:
        pass

    conv = storage.create_conversation(conv_id)
    assert "has_unread" in conv
    assert conv["has_unread"] is False
    
    # Check persistence
    loaded = storage.get_conversation(conv_id)
    assert loaded["has_unread"] is False
    
    # Cleanup
    storage.delete_conversation(conv_id)

def test_list_conversations_includes_unread_status():
    """Test that listing conversations includes the has_unread field."""
    conv_id = "test_unread_list"
    try:
        storage.delete_conversation(conv_id)
    except:
        pass
        
    storage.create_conversation(conv_id)
    
    convs = storage.list_conversations()
    target = next((c for c in convs if c["id"] == conv_id), None)
    
    assert target is not None
    assert "has_unread" in target
    assert target["has_unread"] is False
    
    storage.delete_conversation(conv_id)

def test_duplicate_conversation_has_default_unread_status():
    """Test that duplicating a conversation initializes has_unread to False."""
    orig_id = "test_unread_dup_orig"
    new_id = "test_unread_dup_new"
    
    try:
        storage.delete_conversation(orig_id)
        storage.delete_conversation(new_id)
    except:
        pass
        
    storage.create_conversation(orig_id)
    
    dup = storage.duplicate_conversation(orig_id, new_id)
    
    assert "has_unread" in dup
    assert dup["has_unread"] is False
    
    # Cleanup
    storage.delete_conversation(orig_id)
    storage.delete_conversation(new_id)
