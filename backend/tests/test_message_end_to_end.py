from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main


def test_send_message_end_to_end_with_files(tmp_path, monkeypatch):
    """Posting a message with files should store blob refs and format the prompt."""
    conversations_dir = tmp_path / "conversations"
    blobs_dir = tmp_path / "blobs"
    monkeypatch.setattr(config, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(config, "BLOB_DIR", str(blobs_dir))
    monkeypatch.setattr(config, "COUNCIL_MODELS", ["test-model"])
    monkeypatch.setattr(config, "CHAIRMAN_MODEL", "test-chairman")

    captured = {"stage1_prompt": None}

    class FakeLLM:
        async def chat(self, model, messages, *, timeout=None):
            prompt = messages[0]["content"]
            if "Generate a very short title" in prompt:
                return {"content": "Mock Title"}
            if "You are evaluating different responses" in prompt:
                return {"content": "Eval\n\nFINAL RANKING:\n1. Response A"}
            if "You are the Chairman of an LLM Council" in prompt:
                return {"content": "Final synthesis"}
            captured["stage1_prompt"] = prompt
            return {"content": "Stage 1 response"}

    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM()
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
    assert response.json()["stage3"]["response"] == "Final synthesis"

    conversation = client.get(f"/api/conversations/{conv['id']}").json()
    assert conversation["messages"][0]["files"][0]["name"] == "notes.txt"
    assert "reference_id" in conversation["messages"][0]["files"][0]
    assert conversation["messages"][-1]["role"] == "assistant"

    assert captured["stage1_prompt"].startswith("hello\n\n--- FILE: notes.txt ---")

    main.app.dependency_overrides.clear()
