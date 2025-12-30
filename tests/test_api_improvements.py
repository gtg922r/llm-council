import pytest
from fastapi.testclient import TestClient
from backend.main import app
import os
import shutil
from backend.storage import DATA_DIR, ensure_data_dir

client = TestClient(app)

@pytest.fixture(autouse=True)
def setup_test_data():
    """Setup a clean test data directory."""
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)
    ensure_data_dir()
    yield
    if os.path.exists(DATA_DIR):
        shutil.rmtree(DATA_DIR)

def test_list_conversations_includes_flags():
    """Test GET /api/conversations includes is_pinned, is_archived, has_unread."""
    # Create a conversation
    client.post("/api/conversations", json={})
    
    response = client.get("/api/conversations")
    assert response.status_code == 200
    conversations = response.json()
    assert len(conversations) == 1
    assert "is_pinned" in conversations[0]
    assert "is_archived" in conversations[0]
    assert "has_unread" in conversations[0]

def test_get_conversation_includes_has_unread():
    """Test GET /api/conversations/{id} includes has_unread."""
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]

    response = client.get(f"/api/conversations/{conv_id}")
    assert response.status_code == 200
    assert "has_unread" in response.json()

def test_update_conversation_flags():
    """Test PATCH /api/conversations/{id} updates flags."""
    # Create a conversation
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]
    
    # Update is_pinned
    patch_resp = client.patch(f"/api/conversations/{conv_id}", json={"is_pinned": True})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_pinned"] is True
    
    # Update is_archived
    patch_resp = client.patch(f"/api/conversations/{conv_id}", json={"is_archived": True})
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_archived"] is True

def test_duplicate_conversation_api():
    """Test POST /api/conversations/{id}/duplicate."""
    # Create original
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]
    
    # Duplicate
    dup_resp = client.post(f"/api/conversations/{conv_id}/duplicate")
    assert dup_resp.status_code == 200
    new_conv = dup_resp.json()
    assert new_conv["id"] != conv_id
    assert "(Copy)" in new_conv["title"]

def test_delete_conversation_api():
    """Test DELETE /api/conversations/{id}."""
    # Create a conversation
    create_resp = client.post("/api/conversations", json={})
    conv_id = create_resp.json()["id"]
    
    # Delete it
    del_resp = client.delete(f"/api/conversations/{conv_id}")
    assert del_resp.status_code == 200
    
    # Verify it's gone
    get_resp = client.get(f"/api/conversations/{conv_id}")
    assert get_resp.status_code == 404
