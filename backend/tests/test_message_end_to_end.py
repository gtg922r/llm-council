from fastapi.testclient import TestClient

import backend.main as main
from backend.application.council_service import CouncilOrchestrator
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.ports import LLMProvider


def test_send_message_end_to_end_with_files(tmp_path):
    """Posting a message with files should store files and format the prompt."""
    repo = JsonConversationRepository(str(tmp_path / "conversations"))
    blob_store = LocalFileBlobStore(str(tmp_path / "blobs"))
    captured: dict[str, str] = {}

    class FakeLLM(LLMProvider):
        async def chat(self, *, model: str, messages: list[dict[str, str]], timeout: float | None = None):
            prompt = messages[0]["content"]
            if model == "google/gemini-2.5-flash":
                return {"content": "Mock Title"}
            if model == "chairman":
                return {"content": "ok"}
            if "Now provide your evaluation" in prompt:
                return {"content": "rank\n\nFINAL RANKING:\n1. Response A"}
            captured["stage1_prompt"] = prompt
            return {"content": "stage1"}

    llm = FakeLLM()
    service = CouncilOrchestrator(
        repo=repo,
        llm=llm,
        blob_store=blob_store,
        council_models=["council-1"],
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

        response = client.post(
            f"/api/conversations/{conv['id']}/message",
            json=payload,
        )

        assert response.status_code == 200
        assert response.json()["stage3"]["response"] == "ok"

        conversation = repo.get(conv["id"])
        assert conversation is not None
        assert conversation.messages[0].role == "user"
        assert conversation.messages[-1].role == "assistant"

        stored_files = conversation.messages[0].files
        assert stored_files[0].name == "notes.txt"
        assert stored_files[0].size == 7
        assert blob_store.get_text(stored_files[0].file_reference_id) == "example"

        assert captured["stage1_prompt"].startswith("hello\n\n--- FILE: notes.txt ---")
    finally:
        main.app.dependency_overrides = previous_overrides
