from fastapi.testclient import TestClient

import backend.config as config
import backend.main as main


def test_send_followup_message(tmp_path, monkeypatch):
    """Sending `target_model=chairman` should reuse prior council context."""
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
            if "User Follow-up Question:" in prompt:
                return {"content": "Follow-up answer"}
            if "You are the Chairman of an LLM Council" in prompt:
                return {"content": "Initial response"}
            return {"content": "Stage 1 response"}

    client = TestClient(main.app)
    main.app.dependency_overrides[main.get_llm] = lambda: FakeLLM()

    conv = client.post("/api/conversations", json={}).json()

    client.post(f"/api/conversations/{conv['id']}/message", json={"content": "Initial Query"})

    resp = client.post(
        f"/api/conversations/{conv['id']}/message",
        json={"content": "Follow up question", "target_model": "chairman"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["stage1"] == []
    assert data["stage2"] == []
    assert data["stage3"]["response"] == "Follow-up answer"

    main.app.dependency_overrides.clear()
