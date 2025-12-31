from datetime import datetime, timezone

from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main
from backend import storage


def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    conversations_dir = tmp_path / "conversations"
    blobs_dir = tmp_path / "blobs"
    monkeypatch.setattr(config, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(config, "BLOB_DIR", str(blobs_dir))
    monkeypatch.setattr(storage, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(storage, "BLOB_DIR", str(blobs_dir))
    monkeypatch.setattr(config, "COUNCIL_MODELS", ["test-model"])
    monkeypatch.setattr(config, "CHAIRMAN_MODEL", "test-chairman")

    conversation = {
        "id": "conv-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "messages": [{"role": "user", "content": "legacy"}],
    }
    storage.save_conversation(conversation)

    class FakeLLM:
        async def chat(self, model, messages, *, timeout=None):
            prompt = messages[0]["content"]
            if "You are evaluating different responses" in prompt:
                return {"content": "Eval\n\nFINAL RANKING:\n1. Response A"}
            if "You are the Chairman of an LLM Council" in prompt:
                return {"content": "Final synthesis"}
            if "Generate a very short title" in prompt:
                return {"content": "Mock Title"}
            return {"content": "Stage 1 response"}

    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM()

    get_response = client.get("/api/conversations/conv-1")
    assert get_response.status_code == 200
    assert get_response.json()["messages"][0]["content"] == "legacy"

    post_response = client.post(
        "/api/conversations/conv-1/message",
        json={"content": "new message"},
    )
    assert post_response.status_code == 200

    stored = storage.get_conversation("conv-1")
    # Legacy messages may round-trip with an explicit empty `files` list after model validation.
    assert stored["messages"][0].get("files") in (None, [])
    assert stored["messages"][-1]["role"] == "assistant"

    main.app.dependency_overrides.clear()
