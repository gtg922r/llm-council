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
    
    # Patch COUNCIL_MODELS in the council_service module where it's imported
    from backend.application import council_service
    monkeypatch.setattr(council_service, "COUNCIL_MODELS", ["test-model"])
    
    # Update orchestrator to use the new instances
    monkeypatch.setattr(main.orchestrator, "repo", repo)
    monkeypatch.setattr(main.orchestrator, "blob_store", store)
    monkeypatch.setattr(main.orchestrator, "llm_provider", main.llm_provider)

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

    import json
    data_lines = [line for line in lines if line.startswith("data: ")]
    events = [json.loads(line[6:]) for line in data_lines]
    for e in events:
        print(f"STREAM EVENT: {e}")

    assert any(e.get("type") == "stage_start" and e.get("stage") == 1 for e in events)
    assert any(e.get("type") == "stage_complete" and e.get("stage") == 1 for e in events)
    assert any(e.get("type") == "stage_complete" and e.get("stage") == 2 for e in events)
    assert any(e.get("type") == "stage_complete" and e.get("stage") == 3 for e in events)
    assert any(e.get("type") == "complete" for e in events)

    conversation = repo.get(conv["id"])
    assert conversation.messages[-1].role == "assistant"