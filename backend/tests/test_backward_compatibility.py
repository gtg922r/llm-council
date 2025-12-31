from datetime import datetime, timezone
from fastapi.testclient import TestClient
import backend.main as main
import backend.storage as storage
import backend.infrastructure.blob_store as blob_store_module
import backend.application.council_service as council_service_module

def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    monkeypatch.setattr(main.repository, "data_dir", str(tmp_path))
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(blob_store_module, "BLOB_DIR", str(tmp_path / "blobs"))

    monkeypatch.setattr(council_service_module, "COUNCIL_MODELS", ["test-model"])

    conversation = {
        "id": "conv-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "messages": [{"role": "user", "content": "legacy"}],
    }
    storage.save_conversation(conversation)

    async def fake_query(model, messages, timeout=30.0):
        return {"content": "ok\n\nFINAL RANKING:\n1. Response A"}

    monkeypatch.setattr(main.llm_provider, "query", fake_query)
    
    async def fake_title(_content):
        return "Mock Title"
    monkeypatch.setattr(main, "generate_conversation_title", fake_title)

    client = TestClient(main.app)

    get_response = client.get("/api/conversations/conv-1")
    assert get_response.status_code == 200
    assert get_response.json()["messages"][0]["content"] == "legacy"

    post_response = client.post(
        "/api/conversations/conv-1/message",
        json={"content": "new message"},
    )
    assert post_response.status_code == 200

    stored = storage.get_conversation("conv-1")
    # Check that files is either None or missing
    msg = stored["messages"][0]
    assert msg.get("files") is None
    assert stored["messages"][-1]["role"] == "assistant"
