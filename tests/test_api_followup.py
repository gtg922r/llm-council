"""Tests for API follow-up endpoint."""

import unittest
from unittest.mock import patch, MagicMock, AsyncMock
from fastapi.testclient import TestClient
from datetime import datetime

from backend.main import app
from backend.domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage,
    Stage1Result,
    Stage2Result,
    AssistantMetadata
)
from backend.application.council_service import StageCompleted, RunCompleted

client = TestClient(app)


class TestApiFollowup(unittest.TestCase):
    """Test follow-up message functionality via API."""
    
    def test_send_followup_message(self):
        """Test sending a follow-up message to the chairman."""
        # Mock the orchestrator for initial council run
        with patch('backend.main.orchestrator') as mock_orchestrator:
            # Mock repository for the initial setup
            with patch('backend.main.conversation_repo') as mock_repo:
                with patch('backend.main.blob_store') as mock_blob:
                    # Create a conversation with previous assistant response
                    conv = Conversation(
                        id="test-followup-1",
                        created_at=datetime.now(),
                        messages=[
                            UserMessage(content="Initial Query"),
                            AssistantMessage(
                                stage1=[Stage1Result(model="A", response="resp A", status="success")],
                                stage2=[Stage2Result(model="A", ranking="rank A", parsed_ranking=["Response A"], status="success")],
                                stage3={"model": "Chairman", "response": "Initial response"},
                                metadata=AssistantMetadata()
                            )
                        ]
                    )
                    mock_repo.get.return_value = conv
                    mock_repo.save.return_value = None
                    mock_blob.save_text.return_value = "ref123"
                    
                    # Mock chairman followup
                    async def mock_followup(conversation_id, followup_query, attachments=None):
                        return {
                            "model": "Chairman",
                            "response": "Follow-up answer"
                        }
                    mock_orchestrator.chairman_followup = AsyncMock(side_effect=mock_followup)
                    
                    # Send follow-up message
                    resp = client.post(
                        "/api/conversations/test-followup-1/message",
                        json={
                            "content": "Follow up question",
                            "target_model": "chairman"
                        }
                    )
                    
                    # Assertions
                    self.assertEqual(resp.status_code, 200)
                    data = resp.json()
                    
                    # Verify structure
                    self.assertEqual(data["stage3"]["response"], "Follow-up answer")
                    self.assertEqual(data["stage1"], [])  # Empty for follow-up
                    self.assertEqual(data["stage2"], [])  # Empty for follow-up
                    
                    # Verify chairman_followup was called
                    mock_orchestrator.chairman_followup.assert_called_once()

    def test_send_regular_message_uses_full_council(self):
        """Test that non-followup messages use full council process."""
        with patch('backend.main.orchestrator') as mock_orchestrator:
            with patch('backend.main.conversation_repo') as mock_repo:
                with patch('backend.main.blob_store') as mock_blob:
                    # Create empty conversation
                    conv = Conversation(
                        id="test-regular-1",
                        created_at=datetime.now(),
                        messages=[]
                    )
                    mock_repo.get.return_value = conv
                    mock_repo.save.return_value = None
                    
                    # Mock run_council
                    async def mock_run_council(conv_id, content, attachments=None, is_first_message=False):
                        yield StageCompleted(stage=1, data=[{"model": "A", "response": "R", "status": "success"}])
                        yield StageCompleted(stage=2, data=[], metadata={"label_to_model": {}, "aggregate_rankings": []})
                        yield StageCompleted(stage=3, data={"model": "C", "response": "Final"})
                        yield RunCompleted()
                    
                    mock_orchestrator.run_council = mock_run_council
                    
                    # Send regular message (no target_model)
                    resp = client.post(
                        "/api/conversations/test-regular-1/message",
                        json={"content": "Regular question"}
                    )
                    
                    self.assertEqual(resp.status_code, 200)
                    data = resp.json()
                    
                    # Should have full results
                    self.assertEqual(len(data["stage1"]), 1)
                    self.assertEqual(data["stage3"]["response"], "Final")


if __name__ == "__main__":
    unittest.main()
