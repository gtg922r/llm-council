"""Tests for streaming message endpoint.

Updated to work with the new hexagonal architecture.
"""

from fastapi.testclient import TestClient
from unittest.mock import MagicMock

import backend.main as main
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.infrastructure.blob_store import BlobStore


def _collect_event_lines(response):
    lines = []
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        lines.append(line)
    return lines


def test_send_message_stream_emits_expected_events(tmp_path):
    """Streaming endpoint should emit stage events and store files."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    
    repo = JsonConversationRepository(data_dir=str(data_dir))
    blob_store = BlobStore(blob_dir=str(blob_dir))
    
    async def mock_chat(model, messages, timeout=120.0, max_retries=1):
        if "title" in messages[0]["content"].lower():
            return {"content": "Mock Title"}
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
        
        # Send message with streaming
        payload = {
            "content": "hello",
            "files": [{"name": "notes.txt", "content": "example", "size": 7}],
        }
        
        with client.stream(
            "POST",
            f"/api/conversations/{conv['id']}/message/stream",
            json=payload,
        ) as response:
            assert response.status_code == 200
            lines = _collect_event_lines(response)
        
        data_lines = [line for line in lines if line.startswith("data: ")]
        
        # Verify expected events are emitted
        assert any('"type": "stage1_start"' in line or '"type":"stage1_start"' in line for line in data_lines)
        assert any('"type": "stage2_complete"' in line or '"type":"stage2_complete"' in line for line in data_lines)
        assert any('"type": "stage3_complete"' in line or '"type":"stage3_complete"' in line for line in data_lines)
        assert any('"type": "complete"' in line or '"type":"complete"' in line for line in data_lines)
        
        # Verify conversation was saved
        stored = repo.get(conv["id"])
        assert len(stored.messages) == 2
        assert stored.messages[1].role == "assistant"
    finally:
        main.app.dependency_overrides.clear()


def test_stream_includes_metadata_in_stage2_complete(tmp_path):
    """Stage2 complete event should include metadata for the frontend."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    
    repo = JsonConversationRepository(data_dir=str(data_dir))
    blob_store = BlobStore(blob_dir=str(blob_dir))
    
    async def mock_chat(model, messages, timeout=120.0, max_retries=1):
        if "title" in messages[0]["content"].lower():
            return {"content": "Mock Title"}
        return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A\n2. Response B"}
    
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
        conv = client.post("/api/conversations", json={}).json()
        
        with client.stream(
            "POST",
            f"/api/conversations/{conv['id']}/message/stream",
            json={"content": "test"},
        ) as response:
            lines = _collect_event_lines(response)
        
        # Find stage2_complete event
        stage2_lines = [
            line for line in lines 
            if "stage2_complete" in line
        ]
        assert len(stage2_lines) > 0
        
        # Verify it includes metadata
        stage2_line = stage2_lines[0]
        assert "metadata" in stage2_line
        assert "label_to_model" in stage2_line
    finally:
        main.app.dependency_overrides.clear()
