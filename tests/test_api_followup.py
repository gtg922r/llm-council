import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from backend.main import app
import os
import shutil
from backend.storage import DATA_DIR, ensure_data_dir

client = TestClient(app)

class TestApiFollowup(unittest.TestCase):
    
    def setUp(self):
        """Setup a clean test data directory."""
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)
        ensure_data_dir()

    def tearDown(self):
        if os.path.exists(DATA_DIR):
            shutil.rmtree(DATA_DIR)

    @patch('backend.main.run_full_council')
    @patch('backend.main.chairman_followup')
    @patch('backend.main.generate_conversation_title')
    def test_send_followup_message(self, mock_title, mock_chairman, mock_council):
        """Test sending a follow-up message to the chairman."""
        # 1. Create conversation
        create_resp = client.post("/api/conversations", json={})
        conv_id = create_resp.json()["id"]

        # 2. Mock initial council run
        mock_council.return_value = (
            [{"model": "A", "response": "resp A", "status": "success"}], # Stage 1
            [{"model": "A", "ranking": "rank A", "status": "success"}], # Stage 2
            {"model": "Chairman", "response": "Initial response"},       # Stage 3
            {}                                                           # Metadata
        )
        mock_title.return_value = "Test Conv"

        # 3. Send initial message
        client.post(f"/api/conversations/{conv_id}/message", json={"content": "Initial Query"})

        # 4. Mock chairman follow-up response
        mock_chairman.return_value = {
            "model": "Chairman", 
            "response": "Follow-up answer"
        }

        # 5. Send follow-up message
        # We expect to be able to pass 'target_model': 'chairman'
        resp = client.post(
            f"/api/conversations/{conv_id}/message", 
            json={
                "content": "Follow up question",
                "target_model": "chairman"
            }
        )

        # Assertions
        assert resp.status_code == 200
        data = resp.json()
        
        # Verify structure
        assert data["stage3"]["response"] == "Follow-up answer"
        assert data["stage1"] == [] # Should be empty for follow-up
        assert data["stage2"] == [] # Should be empty for follow-up

        # Verify chairman_followup was called with correct context
        # We need to access the conversation history to verify what was passed
        # but since we are mocking, we can check the call args of mock_chairman
        
        # Check call args
        mock_chairman.assert_called_once()
        call_args = mock_chairman.call_args
        kwargs = call_args.kwargs
        # Or args if called positionally. The function def is async def chairman_followup(original_query, ...)
        # In main.py it will likely be called with named args or positional.
        
        # Let's just check the result for now to confirm the endpoint works.

if __name__ == "__main__":
    unittest.main()
