from datetime import datetime, timezone

from fastapi.testclient import TestClient

import backend.main as main
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.ports import LLMProvider


def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    repo = JsonConversationRepository(str(tmp_path / "conversations"))
    blob_store = LocalFileBlobStore(str(tmp_path / "blobs"))

    class FakeLLM(LLMProvider):
        async def chat(self, *, model: str, messages: list[dict[str, str]], timeout: float | None = None):
            prompt = messages[0]["content"]
            if model == "chairman":
                return {"content": "ok"}
            if "Now provide your evaluation" in prompt:
                return {"content": "rank\n\nFINAL RANKING:\n1. Response A"}
            return {"content": "stage1"}

    llm = FakeLLM()

    conversation = {
        "id": "conv-1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "Legacy Conversation",
        "is_pinned": False,
        "is_archived": False,
        "messages": [{"role": "user", "content": "legacy"}],
    }
    # Write legacy JSON directly (no migration required).
    from pathlib import Path
    import json

    legacy_path = Path(repo._path_for("conv-1"))  # type: ignore[attr-defined]
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    legacy_path.write_text(json.dumps(conversation, indent=2), encoding="utf-8")

    previous_overrides = dict(main.app.dependency_overrides)
    main.app.dependency_overrides[main.get_repo] = lambda: repo
    main.app.dependency_overrides[main.get_blob_store] = lambda: blob_store
    main.app.dependency_overrides[main.get_llm_provider] = lambda: llm

    try:
        client = TestClient(main.app)

        get_response = client.get("/api/conversations/conv-1")
        assert get_response.status_code == 200
        assert get_response.json()["messages"][0]["content"] == "legacy"

        post_response = client.post(
            "/api/conversations/conv-1/message",
            json={"content": "new message"},
        )
        assert post_response.status_code == 200

        stored = repo.get("conv-1")
        assert stored is not None
        assert stored.messages[0].role == "user"
        assert stored.messages[-1].role == "assistant"
    finally:
        main.app.dependency_overrides = previous_overrides
