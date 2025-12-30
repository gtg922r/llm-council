from fastapi.testclient import TestClient
from backend.main import app
from backend import storage
import pytest

client = TestClient(app)

def test_patch_conversation_unread_status():
    """Test updating the has_unread status via API."""
    conv_id = "test_api_unread_patch"
    
    # Setup
    try:
        storage.delete_conversation(conv_id)
    except:
        pass
        
    storage.create_conversation(conv_id)
    # Manually set to unread
    c = storage.get_conversation(conv_id)
    c["has_unread"] = True
    storage.save_conversation(c)
    
    # Verify setup
    response = client.get(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    assert response.json()["has_unread"] is True
    
    # Patch to mark as read
    response = client.patch(f"/api/conversations/{conv_id}", json={"has_unread": False})
    
    assert response.status_code == 200
    data = response.json()
    assert data["has_unread"] is False
    
    # Cleanup
    storage.delete_conversation(conv_id)
