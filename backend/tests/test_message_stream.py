from fastapi.testclient import TestClient

import backend.main as main
from backend import storage


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
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main.storage, "DATA_DIR", str(tmp_path))
    monkeypatch.setattr(main, "COUNCIL_MODELS", ["test-model"])

    async def fake_query_model(_model, _messages):
        return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"}

    async def fake_stage3(_prompt, _stage1, _stage2):
        return {"response": "final"}

    async def fake_title(_content):
        return "Mock Title"

    monkeypatch.setattr(main, "query_model", fake_query_model)
    monkeypatch.setattr(main, "stage3_synthesize_final", fake_stage3)
    monkeypatch.setattr(main, "generate_conversation_title", fake_title)
    monkeypatch.setattr(main, "parse_ranking_from_text", lambda _text: ["Response A"])
    monkeypatch.setattr(main, "calculate_aggregate_rankings", lambda *_args, **_kwargs: [])

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
    assert any('"type": "stage1_start"' in line for line in data_lines)
    assert any('"type": "stage2_complete"' in line for line in data_lines)
    assert any('"type": "stage3_complete"' in line for line in data_lines)
    assert any('"type": "title_complete"' in line for line in data_lines)
    assert any('"type": "complete"' in line for line in data_lines)

    conversation = storage.get_conversation(conv["id"])
    assert conversation["messages"][-1]["role"] == "assistant"
