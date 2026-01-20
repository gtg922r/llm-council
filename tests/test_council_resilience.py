"""Tests for council resilience and error handling."""

import unittest
from unittest.mock import MagicMock
from datetime import datetime

from backend.application.council_service import CouncilOrchestrator, StageCompleted
from backend.domain.models import Conversation
from backend.config import COUNCIL_MODELS, CHAIRMAN_MODEL
from backend.ports import LLMProvider, ConversationRepository


class TestCouncilResilience(unittest.IsolatedAsyncioTestCase):
    """Test resilience of the council orchestrator."""

    def _create_mock_repo(self):
        """Create a mock repository."""
        mock_repo = MagicMock(spec=ConversationRepository)
        mock_repo.get.return_value = Conversation(id="test-1", created_at=datetime.now())
        return mock_repo

    async def test_stage1_handles_partial_failures(self):
        """Test Stage 1 continues when some models fail."""
        
        class PartialFailLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                # First model fails, others succeed
                if model == COUNCIL_MODELS[0]:
                    return None
                return {'content': f"Response from {model}"}
            
            async def stream_chat(self, model, messages, **kwargs):
                yield {}

        orchestrator = CouncilOrchestrator(
            llm_provider=PartialFailLLM(),
            conversation_repo=self._create_mock_repo()
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Test query"):
            events.append(event)
        
        # Find stage 1 completion
        stage1_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 1]
        self.assertEqual(len(stage1_events), 1)
        
        # Should have results for all models
        stage1_data = stage1_events[0].data
        self.assertEqual(len(stage1_data), len(COUNCIL_MODELS))
        
        # First model should have error status
        error_results = [r for r in stage1_data if r['status'] == 'error']
        self.assertEqual(len(error_results), 1)
        
        # Should still complete all stages
        stage3_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 3]
        self.assertEqual(len(stage3_events), 1)

    async def test_stage2_handles_partial_failures(self):
        """Test Stage 2 continues when some ranking models fail."""
        call_count = {}
        
        class PartialFailStage2LLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                call_count[model] = call_count.get(model, 0) + 1
                # First call is stage 1, second is stage 2
                if call_count.get(model, 0) == 2 and model == COUNCIL_MODELS[0]:
                    return None  # Fail on stage 2
                return {'content': "Response\n\nFINAL RANKING:\n1. Response A"}
            
            async def stream_chat(self, model, messages, **kwargs):
                yield {}

        orchestrator = CouncilOrchestrator(
            llm_provider=PartialFailStage2LLM(),
            conversation_repo=self._create_mock_repo()
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Test query"):
            events.append(event)
        
        # Find stage 2 completion
        stage2_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 2]
        self.assertEqual(len(stage2_events), 1)
        
        stage2_data = stage2_events[0].data
        error_results = [r for r in stage2_data if r['status'] == 'error']
        self.assertEqual(len(error_results), 1)

    async def test_stage3_handles_chairman_failure(self):
        """Test Stage 3 returns error message when chairman fails."""
        call_count = [0]
        
        class ChairmanFailLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                call_count[0] += 1
                # Stages 1 and 2 succeed, stage 3 (chairman) fails
                # With N council models, we have N calls for stage 1, N for stage 2
                total_stage1_2_calls = len(COUNCIL_MODELS) * 2
                if call_count[0] > total_stage1_2_calls:
                    return None  # Chairman fails
                return {'content': "Response\n\nFINAL RANKING:\n1. Response A"}
            
            async def stream_chat(self, model, messages, **kwargs):
                yield {}

        orchestrator = CouncilOrchestrator(
            llm_provider=ChairmanFailLLM(),
            conversation_repo=self._create_mock_repo()
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Test query"):
            events.append(event)
        
        # Find stage 3 completion
        stage3_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 3]
        self.assertEqual(len(stage3_events), 1)
        
        stage3_data = stage3_events[0].data
        self.assertEqual(stage3_data['model'], CHAIRMAN_MODEL)
        self.assertIn("Error", stage3_data['response'])

    async def test_all_stage1_failures_returns_error(self):
        """Test that all Stage 1 failures returns error in Stage 3."""
        
        class AllFailLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                return None  # All models fail
            
            async def stream_chat(self, model, messages, **kwargs):
                yield {}

        orchestrator = CouncilOrchestrator(
            llm_provider=AllFailLLM(),
            conversation_repo=self._create_mock_repo()
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Test query"):
            events.append(event)
        
        # Should still complete with error
        stage3_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 3]
        self.assertEqual(len(stage3_events), 1)
        
        stage3_data = stage3_events[0].data
        self.assertEqual(stage3_data['model'], "error")
        self.assertIn("All models failed", stage3_data['response'])


if __name__ == "__main__":
    unittest.main()
