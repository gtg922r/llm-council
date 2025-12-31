import tempfile
import unittest

from fastapi.testclient import TestClient

import backend.main as main
from backend.application.council_service import CouncilOrchestrator
from backend.infrastructure.blob_store import LocalFileBlobStore
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.ports import LLMProvider


class TestApiFollowup(unittest.TestCase):
    def test_send_followup_message(self):
        """Sending a follow-up to the chairman should skip stages 1/2."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = JsonConversationRepository(f"{tmp}/conversations")
            blob_store = LocalFileBlobStore(f"{tmp}/blobs")

            class FakeLLM(LLMProvider):
                async def chat(self, *, model: str, messages: list[dict[str, str]], timeout: float | None = None):
                    prompt = messages[0]["content"]
                    if model == "google/gemini-2.5-flash":
                        return {"content": "Test Conv"}
                    if model == "chairman":
                        if "User Follow-up Question:" in prompt:
                            return {"content": "Follow-up answer"}
                        return {"content": "Initial response"}
                    if "Now provide your evaluation" in prompt:
                        return {"content": "rank\n\nFINAL RANKING:\n1. Response A"}
                    return {"content": "resp A"}

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

            try:
                client = TestClient(main.app)

                create_resp = client.post("/api/conversations", json={})
                conv_id = create_resp.json()["id"]

                client.post(
                    f"/api/conversations/{conv_id}/message",
                    json={"content": "Initial Query"},
                )

                resp = client.post(
                    f"/api/conversations/{conv_id}/message",
                    json={"content": "Follow up question", "target_model": "chairman"},
                )

                assert resp.status_code == 200
                data = resp.json()
                assert data["stage3"]["response"] == "Follow-up answer"
                assert data["stage1"] == []
                assert data["stage2"] == []
            finally:
                main.app.dependency_overrides = previous_overrides
