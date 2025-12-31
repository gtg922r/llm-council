"""Tests for the follow-up API endpoint.

Updated to work with the new hexagonal architecture.
"""

import unittest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient
from backend.main import app, get_repository, get_blob_store, get_llm_provider
from backend.infrastructure.json_repository import JsonConversationRepository
from backend.infrastructure.blob_store import BlobStore
import tempfile
import shutil


class TestApiFollowup(unittest.TestCase):
    
    def setUp(self):
        """Setup a clean test data directory with dependency injection."""
        self.temp_dir = tempfile.mkdtemp()
        self.data_dir = f"{self.temp_dir}/conversations"
        self.blob_dir = f"{self.temp_dir}/blobs"
        
        import os
        os.makedirs(self.data_dir, exist_ok=True)
        os.makedirs(self.blob_dir, exist_ok=True)
        
        self.repo = JsonConversationRepository(data_dir=self.data_dir)
        self.blob_store = BlobStore(blob_dir=self.blob_dir)
        
        # Track call count for different stages
        self.call_count = 0
        
        async def mock_chat(model, messages, timeout=120.0, max_retries=1):
            self.call_count += 1
            content = messages[0]["content"] if messages else ""
            
            # Title generation
            if "title" in content.lower():
                return {"content": "Test Title"}
            
            # Follow-up response (will be called for chairman follow-up)
            if "follow-up" in content.lower() or "followup" in content.lower() or "Chairman" in content:
                return {"content": "Follow-up answer"}
            
            # Regular stage responses
            return {"content": "Response text\n\nFINAL RANKING:\n1. Response A"}
        
        self.mock_llm = MagicMock()
        self.mock_llm.chat = mock_chat
        
        # Set up dependency overrides
        app.dependency_overrides[get_repository] = lambda: self.repo
        app.dependency_overrides[get_blob_store] = lambda: self.blob_store
        app.dependency_overrides[get_llm_provider] = lambda: self.mock_llm
        
        self.client = TestClient(app)

    def tearDown(self):
        """Clean up."""
        app.dependency_overrides.clear()
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_send_followup_message(self):
        """Test sending a follow-up message to the chairman."""
        # 1. Create conversation
        create_resp = self.client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        # 2. Send initial message (this triggers full council run)
        initial_resp = self.client.post(
            f"/api/conversations/{conv_id}/message",
            json={"content": "Initial Query"}
        )
        assert initial_resp.status_code == 200

        # 3. Send follow-up message with target_model: "chairman"
        resp = self.client.post(
            f"/api/conversations/{conv_id}/message",
            json={
                "content": "Follow up question",
                "target_model": "chairman"
            }
        )

        # Assertions
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify structure - follow-up should have empty stages 1 and 2
        assert data["stage1"] == []
        assert data["stage2"] == []
        assert "stage3" in data
        
        # Verify conversation was saved with both messages
        stored = self.repo.get(conv_id)
        assert len(stored.messages) == 4  # user + assistant + user + assistant


if __name__ == "__main__":
    unittest.main()
