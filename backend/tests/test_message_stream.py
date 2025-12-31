from fastapi.testclient import TestClient
import json
import pytest
import backend.main as main
import backend.infrastructure.blob_store as blob_store_module
import backend.application.council_service as council_service_module

def _collect_event_lines(response):
    lines = []
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        lines.append(line)
    return lines

@pytest.mark.asyncio
async def test_send_message_stream_emits_expected_events(tmp_path, monkeypatch):
    """Streaming endpoint should emit stage events and store files."""
    monkeypatch.setattr(main.repository, "data_dir", str(tmp_path))
    monkeypatch.setattr(blob_store_module, "BLOB_DIR", str(tmp_path / "blobs"))
    
    monkeypatch.setattr(council_service_module, "COUNCIL_MODELS", ["test-model"])

    async def fake_query(model, messages, timeout=30.0):
        return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"}

    monkeypatch.setattr(main.llm_provider, "query", fake_query)
    
    async def fake_title(_content):
        return "Mock Title"
    monkeypatch.setattr(main, "generate_conversation_title", fake_title)

    client = TestClient(main.app)
    conv_response = client.post("/api/conversations", json={})
    assert conv_response.status_code == 200
    conv = conv_response.json()

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

    data_lines = [line[6:] for line in lines if line.startswith("data: ")]
    events = [json.loads(line) for line in data_lines]
    
    # Check for event types
    assert any(e["type"] == "stage1_start" for e in events)
    assert any(e["type"] == "stage2_complete" for e in events)
    assert any(e["type"] == "stage3_complete" for e in events)
    assert any(e["type"] == "complete" for e in events)

    conversation = main.repository.get(conv["id"])
    assert conversation.messages[-1].role == "assistant"
    assert conversation.messages[-2].role == "user"
    assert len(conversation.messages[-2].files) == 1
    assert conversation.messages[-2].files[0].name == "notes.txt"
    assert conversation.messages[-2].files[0].file_reference_id is not None
