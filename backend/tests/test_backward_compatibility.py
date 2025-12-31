from datetime import datetime, timezone

from fastapi.testclient import TestClient

import backend.main as main
from backend import storage


def test_backward_compatibility_with_legacy_messages(tmp_path, monkeypatch):
    """Legacy conversations without files should still load and accept new messages."""
    from backend.infrastructure.json_repository import JsonConversationRepository
    from backend.domain.models import Conversation as ConversationModel
    
    data_dir = tmp_path / "conversations"
    repo = JsonConversationRepository(data_dir=str(data_dir))
    monkeypatch.setattr(main, "conversation_repo", repo)

    conversation = ConversationModel(
        id="conv-1",
        created_at=datetime.now(timezone.utc),
        title="Legacy Conversation",
        messages=[{"role": "user", "content": "legacy"}]
    )
    repo.save(conversation)

    async def fake_run_full_council(_prompt_content, llm_provider=None):
        from backend.domain.models import CouncilRun, AssistantMetadata
        return CouncilRun(
            stage1_results=[],
            stage2_results=[],
            stage3_result={"response": "ok"},
            metadata=AssistantMetadata()
        )

    monkeypatch.setattr(main, "run_full_council", fake_run_full_council)

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
    assert stored.messages[0].content == "legacy"
    assert stored.messages[-1].role == "assistant"
