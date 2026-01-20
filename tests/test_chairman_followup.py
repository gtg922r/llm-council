"""Tests for chairman follow-up functionality."""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from backend.config import CHAIRMAN_MODEL
from backend.application.prompts import build_chairman_followup_prompt
from backend.application.council_service import CouncilOrchestrator
from backend.domain.models import (
    Stage1Result, 
    Stage2Result, 
    Conversation,
    UserMessage,
    AssistantMessage
)
from backend.ports import LLMProvider, ConversationRepository


class TestChairmanFollowupPrompt(unittest.TestCase):
    """Test the pure prompt building function."""
    
    def test_followup_prompt_contains_all_context(self):
        """Test that the followup prompt contains all necessary context."""
        original_query = "What is 2+2?"
        stage1_results = [
            Stage1Result(model="ModelA", response="The answer is 4.", status="success"),
            Stage1Result(model="ModelB", response="2+2 = 4", status="success")
        ]
        stage2_results = [
            Stage2Result(
                model="ModelA", 
                ranking="FINAL RANKING:\n1. Response A\n2. Response B", 
                parsed_ranking=["Response A", "Response B"], 
                status="success"
            ),
            Stage2Result(
                model="ModelB", 
                ranking="FINAL RANKING:\n1. Response A\n2. Response B", 
                parsed_ranking=["Response A", "Response B"], 
                status="success"
            )
        ]
        stage3_response = "Based on the council, the answer is 4."
        followup_query = "Are you absolutely sure?"

        prompt = build_chairman_followup_prompt(
            original_query=original_query,
            stage1_results=stage1_results,
            stage2_results=stage2_results,
            stage3_response=stage3_response,
            followup_query=followup_query
        )

        # Check that the prompt contains all necessary context
        self.assertIn("Original Question: What is 2+2?", prompt)
        self.assertIn("STAGE 1 - Individual Responses:", prompt)
        self.assertIn("Model: ModelA", prompt)
        self.assertIn("The answer is 4.", prompt)
        self.assertIn("STAGE 2 - Peer Rankings:", prompt)
        self.assertIn("FINAL RANKING:", prompt)
        self.assertIn("Chairman's Initial Response:", prompt)
        self.assertIn("Based on the council, the answer is 4.", prompt)
        self.assertIn("User Follow-up Question: Are you absolutely sure?", prompt)


class TestChairmanFollowupIntegration(unittest.IsolatedAsyncioTestCase):
    """Integration tests for chairman follow-up through the orchestrator."""
    
    async def test_chairman_followup_via_orchestrator(self):
        """Test chairman followup through the orchestrator."""
        expected_response_text = "Yes, strictly speaking, 2+2 is 4 in standard arithmetic."
        
        # Create mock LLM
        class MockLLM(LLMProvider):
            def __init__(self):
                self.captured_messages = None
                
            async def chat(self, model, messages, **kwargs):
                self.captured_messages = messages
                return {"content": expected_response_text}
                
            async def stream_chat(self, model, messages, **kwargs):
                yield {"content": expected_response_text}

        mock_llm = MockLLM()
        
        # Create conversation with previous council response
        conversation = Conversation(
            id="test-1",
            created_at=datetime.now(),
            messages=[
                UserMessage(content="What is 2+2?"),
                AssistantMessage(
                    stage1=[
                        Stage1Result(model="ModelA", response="The answer is 4.", status="success"),
                        Stage1Result(model="ModelB", response="2+2 = 4", status="success")
                    ],
                    stage2=[
                        Stage2Result(
                            model="ModelA", 
                            ranking="FINAL RANKING:\n1. Response A", 
                            parsed_ranking=["Response A"], 
                            status="success"
                        )
                    ],
                    stage3={
                        "model": CHAIRMAN_MODEL,
                        "response": "Based on the council, the answer is 4."
                    }
                )
            ]
        )
        
        # Create mock repo
        mock_repo = MagicMock(spec=ConversationRepository)
        mock_repo.get.return_value = conversation
        
        # Create orchestrator and call followup
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm,
            conversation_repo=mock_repo
        )
        
        result = await orchestrator.chairman_followup(
            conversation_id="test-1",
            followup_query="Are you absolutely sure?"
        )
        
        # Assertions
        self.assertEqual(result["model"], CHAIRMAN_MODEL)
        self.assertEqual(result["response"], expected_response_text)
        
        # Verify LLM was called
        self.assertIsNotNone(mock_llm.captured_messages)
        prompt = mock_llm.captured_messages[0]["content"]
        self.assertIn("Are you absolutely sure?", prompt)


if __name__ == "__main__":
    unittest.main()
