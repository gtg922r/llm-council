from fastapi.testclient import TestClient

import backend.main as main
from backend.application.council_service import CouncilOrchestrator
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.ports import LLMProvider


def _collect_event_lines(response):
    lines = []
    for line in response.iter_lines():
        if not line:
            continue
        if isinstance(line, bytes):
            line = line.decode("utf-8")
        lines.append(line)
    return lines


def test_send_message_stream_emits_expected_events(tmp_path):
    """Streaming endpoint should emit domain events and store messages."""
    repo = JsonConversationRepository(str(tmp_path / "conversations"))
    blob_store = LocalFileBlobStore(str(tmp_path / "blobs"))

    class FakeLLM(LLMProvider):
        async def chat(self, *, model: str, messages: list[dict[str, str]], timeout: float | None = None):
            prompt = messages[0]["content"]
            if model == "google/gemini-2.5-flash":
                return {"content": "Mock Title"}
            if model == "chairman":
                return {"content": "final"}
            if "Now provide your evaluation" in prompt:
                return {"content": "Mock response\n\nFINAL RANKING:\n1. Response A"}
            return {"content": "Mock response"}

    llm = FakeLLM()
    service = CouncilOrchestrator(
        repo=repo,
        llm=llm,
        blob_store=blob_store,
        council_models=["test-model"],
        chairman_model="chairman",
    )

    previous_overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_repo] = lambda: repo
    main.app.dependency_overrides[main.get_blob_store] = lambda: blob_store
    main.app.dependency_overrides[main.get_llm_provider] = lambda: llm
    main.app.dependency_overrides[main.get_council_service] = lambda: service

    client = TestClient(main.app)
    try:
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
        assert any(
            '"type":"stage_started"' in line or '"type": "stage_started"' in line
            for line in data_lines
        )
        assert any(
            '"type":"stage_completed"' in line or '"type": "stage_completed"' in line
            for line in data_lines
        )
        assert any(
            '"type":"title_updated"' in line or '"type": "title_updated"' in line
            for line in data_lines
        )
        assert any(
            '"type":"run_completed"' in line or '"type": "run_completed"' in line
            for line in data_lines
        )

        conversation = repo.get(conv["id"])
        assert conversation is not None
        assert conversation.messages[-1].role == "assistant"
    finally:
        main.app.dependency_overrides = previous_overrides
