"""Tests for backward compatibility with legacy data formats.

Updated to work with the new hexagonal architecture.
"""

from datetime import datetime, timezone
import json

from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch

import backend.main as main
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.infrastructure.blob_store import BlobStore
from backend.domain.models import Stage1Result, Stage2Result, Stage3Result, CouncilMetadata


def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    blob_dir = tmp_path / "blobs"
    blob_dir.mkdir()
    
    # Create a legacy conversation file directly (without using the new models)
    legacy_conversation = {
        "id": "conv-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "has_unread": False,
        "messages": [{"role": "user", "content": "legacy"}],
    }
    
    with open(data_dir / "conv-1.json", "w") as f:
        json.dump(legacy_conversation, f)
    
    # Mock the dependencies
    repo = JsonConversationRepository(data_dir=str(data_dir))
    blob_store = BlobStore(blob_dir=str(blob_dir))
    
    # Create a mock LLM provider
    mock_llm = MagicMock()
    mock_llm.chat = AsyncMock(return_value={"content": "Mock response"})
    
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
        
        # Should be able to load legacy conversation
        get_response = client.get("/api/conversations/conv-1")
        assert get_response.status_code == 200
        assert get_response.json()["messages"][0]["content"] == "legacy"
        
        # Should be able to post new message
        post_response = client.post(
            "/api/conversations/conv-1/message",
            json={"content": "new message"},
        )
        assert post_response.status_code == 200
    finally:
        main.app.dependency_overrides.clear()


def test_legacy_assistant_message_without_metadata(tmp_path):
    """Legacy assistant messages without metadata field should load correctly."""
    data_dir = tmp_path / "conversations"
    data_dir.mkdir()
    
    # Create a legacy conversation with assistant message but no metadata field
    legacy_conversation = {
        "id": "conv-2",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy with Assistant",
        "is_pinned": False,
        "is_archived": False,
        "has_unread": False,
        "messages": [
            {"role": "user", "content": "question"},
            {
                "role": "assistant",
                "stage1": [{"model": "test", "response": "answer", "status": "success"}],
                "stage2": [],
                "stage3": {"model": "chair", "response": "final"}
                # Note: no metadata field
            }
        ],
    }
    
    with open(data_dir / "conv-2.json", "w") as f:
        json.dump(legacy_conversation, f)
    
    repo = JsonConversationRepository(data_dir=str(data_dir))
    
    # Should load without error
    conv = repo.get("conv-2")
    assert conv is not None
    assert len(conv.messages) == 2
    
    # Metadata should default to empty
    assistant_msg = conv.messages[1]
    assert assistant_msg.metadata is not None
    assert assistant_msg.metadata.label_to_model == {}
    assert assistant_msg.metadata.aggregate_rankings == []
