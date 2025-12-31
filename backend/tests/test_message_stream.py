from fastapi.testclient import TestClient
from datetime import datetime, timezone
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
    from backend.infrastructure.json_repository import JsonConversationRepository
    from backend.infrastructure.blob_store import BlobStore
    from backend.ports import LLMProvider
    
    data_dir = tmp_path / "conversations"
    blob_dir = tmp_path / "blobs"
    repo = JsonConversationRepository(data_dir=str(data_dir))
    store = BlobStore(blob_dir=str(blob_dir))
    
    class MockLLM(LLMProvider):
        async def chat(self, model, messages, **kwargs):
            return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"}
        async def stream_chat(self, model, messages, **kwargs):
            yield {"content": "Mock response"}
        async def chat_parallel(self, models, messages, **kwargs):
            return {m: {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"} for m in models}

    monkeypatch.setattr(main, "conversation_repo", repo)
    monkeypatch.setattr(main, "blob_store", store)
    monkeypatch.setattr(main, "llm_provider", MockLLM())
    monkeypatch.setattr(main, "COUNCIL_MODELS", ["test-model"])

    client = TestClient(main.app)
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
    for line in data_lines:
        print(f"STREAM DATA: {line}")

    assert any("\"type\": \"stage1_start\"" in line for line in data_lines)
    assert any("\"type\": \"stage2_complete\"" in line for line in data_lines)
    assert any("\"type\": \"stage3_complete\"" in line for line in data_lines)
    assert any("\"type\": \"title_complete\"" in line for line in data_lines)
    assert any("\"type\": \"complete\"" in line for line in data_lines)

    conversation = repo.get(conv["id"])
    assert conversation.messages[-1].role == "assistant"