from datetime import datetime, timezone

from fastapi.testclient import TestClient

import backend.main as main
from backend import storage


def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.storage, "DATA_DIR", str(tmp_path))

    conversation = {
        "id": "conv-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "messages": [{"role": "user", "content": "legacy"}],
    }
    storage.save_conversation(conversation)

    async def fake_run_full_council(_prompt_content):
        return [], [], {"response": "ok"}, {}

    monkeypatch.setattr(main, "run_full_council", fake_run_full_council)

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
    assert "files" not in stored["messages"][0]
    assert stored["messages"][-1]["role"] == "assistant"
