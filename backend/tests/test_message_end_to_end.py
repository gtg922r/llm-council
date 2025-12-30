from fastapi.testclient import TestClient

import backend.main as main
from backend import storage


def test_send_message_end_to_end_with_files(tmp_path, monkeypatch):
    """Posting a message with files should store files and format the prompt."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.storage, "DATA_DIR", str(tmp_path))

    captured = {}

    async def fake_run_full_council(prompt_content):
        captured["prompt"] = prompt_content
        return [], [], {"response": "ok"}, {}

    monkeypatch.setattr(main, "run_full_council", fake_run_full_council)

    client = TestClient(main.app)
    conv = client.post("/api/conversations", json={}).json()

    payload = {
        "content": "hello",
        "files": [{"name": "notes.txt", "content": "example", "size": 7}],
    }

    response = client.post(
        f"/api/conversations/{conv['id']}/message",
        json=payload,
    )

    assert response.status_code == 200
    assert response.json()["stage3"]["response"] == "ok"

    conversation = storage.get_conversation(conv["id"])
    assert conversation["messages"][0]["files"] == payload["files"]
    assert conversation["messages"][-1]["role"] == "assistant"
    assert captured["prompt"].startswith("hello\n\n--- FILE: notes.txt ---")
