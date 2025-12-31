"""End-to-end tests for message handling.

Updated to work with the new hexagonal architecture.
"""

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock

import backend.main as main
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.infrastructure.blob_store import BlobStore


def test_send_message_end_to_end_with_files(tmp_path):
    """Posting a message with files should store files and format the prompt."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    
    repo = JsonConversationRepository(data_dir=str(data_dir))
    blob_store = BlobStore(blob_dir=str(blob_dir))
    
    # Track what prompt was sent to the LLM
    captured_prompt = None
    
    async def mock_chat(model, messages, timeout=120.0, max_retries=1):
        nonlocal captured_prompt
        captured_prompt = messages[0]["content"] if messages else None
        return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"}
    
    mock_llm = MagicMock()
    mock_llm.chat = mock_chat
    
    def get_repo():
        return repo
    
    def get_blob():
        return blob_store
    
    def get_llm():
        return mock_llm
    
    main.app.dependency_overrides[main.get_repository] = get_repo
    main.app.dependency_overrides[main.get_blob_store] = get_blob
    main.app.dependency_overrides[main.get_llm_provider] = get_llm
    
    try:
        client = TestClient(main.app)
        
        # Create conversation
        conv = client.post("/api/conversations", json={}).json()
        
        # Send message with files
        payload = {
            "content": "hello",
            "files": [{"name": "notes.txt", "content": "example", "size": 7}],
        }
        
        response = client.post(
            f"/api/conversations/{conv['id']}/message",
            json=payload,
        )
        
        assert response.status_code == 200
        
        # Verify the prompt includes the file content
        assert captured_prompt is not None
        assert "hello" in captured_prompt
        assert "notes.txt" in captured_prompt
        assert "example" in captured_prompt
        
        # Verify conversation was saved with file references
        stored = repo.get(conv["id"])
        assert len(stored.messages) == 2
        assert stored.messages[0].content == "hello"
        assert len(stored.messages[0].files) == 1
        assert stored.messages[0].files[0].name == "notes.txt"
    finally:
        main.app.dependency_overrides.clear()


def test_send_message_stores_metadata(tmp_path):
    """Message response should include and persist metadata (rankings fix)."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    
    repo = JsonConversationRepository(data_dir=str(data_dir))
    blob_store = BlobStore(blob_dir=str(blob_dir))
    
    async def mock_chat(model, messages, timeout=120.0, max_retries=1):
        return {"content": "Response text\n\nFINAL RANKING:\n1. Response A\n2. Response B"}
    
    mock_llm = MagicMock()
    mock_llm.chat = mock_chat
    
    def get_repo():
        return repo
    
    def get_blob():
        return blob_store
    
    def get_llm():
        return mock_llm
    
    main.app.dependency_overrides[main.get_repository] = get_repo
    main.app.dependency_overrides[main.get_blob_store] = get_blob
    main.app.dependency_overrides[main.get_llm_provider] = get_llm
    
    try:
        client = TestClient(main.app)
        
        # Create conversation
        conv = client.post("/api/conversations", json={}).json()
        
        # Send message
        response = client.post(
            f"/api/conversations/{conv['id']}/message",
            json={"content": "test question"},
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify metadata is in response
        assert "metadata" in data
        assert "label_to_model" in data["metadata"]
        
        # Verify metadata is persisted (the amnesia fix)
        stored = repo.get(conv["id"])
        assistant_msg = stored.messages[1]
        assert assistant_msg.metadata is not None
    finally:
        main.app.dependency_overrides.clear()
