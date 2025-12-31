from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main


def _collect_event_lines(response):
    lines = []
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        lines.append(line)
    return lines


def test_send_message_stream_emits_expected_events(tmp_path, monkeypatch):
    """Streaming endpoint should emit stage events and store files."""
    conversations_dir = tmp_path / "conversations"
    blobs_dir = tmp_path / "blobs"
    monkeypatch.setattr(config, "DATA_DIR", str(conversations_dir))
    monkeypatch.setattr(config, "BLOB_DIR", str(blobs_dir))
    monkeypatch.setattr(config, "COUNCIL_MODELS", ["test-model"])
    monkeypatch.setattr(config, "CHAIRMAN_MODEL", "test-chairman")

    class FakeLLM:
        async def chat(self, model, messages, *, timeout=None):
            prompt = messages[0]["content"]
            if "Generate a very short title" in prompt:
                return {"content": "Mock Title"}
            if "You are evaluating different responses" in prompt:
                return {"content": "Eval\n\nFINAL RANKING:\n1. Response A"}
            if "You are the Chairman of an LLM Council" in prompt:
                return {"content": "Final synthesis"}
            return {"content": "Stage 1 response"}

    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM()
    conv = client.post("/api/conversations", json={}).json()

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
    assert any('"type": "stage1_start"' in line for line in data_lines)
    assert any('"type": "stage2_complete"' in line for line in data_lines)
    assert any('"type": "stage3_complete"' in line for line in data_lines)
    assert any('"type": "title_complete"' in line for line in data_lines)
    assert any('"type": "complete"' in line for line in data_lines)

    conversation = client.get(f"/api/conversations/{conv['id']}").json()
    assert conversation["messages"][-1]["role"] == "assistant"

    main.app.dependency_overrides.clear()
