"""Tests for backend/council.py resilience."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
from backend.council import stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, run_full_council, CHAIRMAN_MODEL
from backend.config import COUNCIL_MODELS

class TestCouncilResilience(unittest.IsolatedAsyncioTestCase):

    async def test_stage1_handles_exceptions(self):
        """Test Stage 1 handles exceptions from llm_provider."""
        from backend.ports import LLMProvider
        class ErrorLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                if model == COUNCIL_MODELS[0]:
                    raise RuntimeError("Unexpected error")
                return {'content': f"Response from {model}"}
            async def stream_chat(self, model, messages, **kwargs):
                yield {}
            async def chat_parallel(self, models, messages, **kwargs):
                # Simulate the error during parallel execution
                results = {}
                for m in models:
                    try:
                        results[m] = await self.chat(m, messages)
                    except Exception:
                        results[m] = None
                return results

        results = await stage1_collect_responses("Test query", llm_provider=ErrorLLM())
        
        self.assertEqual(len(results), len(COUNCIL_MODELS))
        error_results = [r for r in results if r.status == "error"]
        self.assertEqual(len(error_results), 1)

    async def test_stage2_handles_exceptions(self):
        """Test Stage 2 handles exceptions from llm_provider."""
        from backend.domain.models import Stage1Result
        from backend.ports import LLMProvider
        stage1_results = [
            Stage1Result(model=m, response=f"Response {m}", status="success")
            for m in COUNCIL_MODELS
        ]
        
        class ErrorLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                if model == COUNCIL_MODELS[0]:
                    raise RuntimeError("Stage 2 error")
                return {'content': "Ranking text\n\nFINAL RANKING:\n1. Response A"}
            async def stream_chat(self, model, messages, **kwargs):
                yield {}
            async def chat_parallel(self, models, messages, **kwargs):
                results = {}
                for m in models:
                    try:
                        results[m] = await self.chat(m, messages)
                    except Exception:
                        results[m] = None
                return results
        
        results, mapping = await stage2_collect_rankings("Test query", stage1_results, llm_provider=ErrorLLM())
        
        self.assertEqual(len(results), len(COUNCIL_MODELS))
        error_results = [r for r in results if r.status == "error"]
        self.assertEqual(len(error_results), 1)

    async def test_stage3_handles_failure(self):
        """Test Stage 3 handles chairman failure."""
        from backend.ports import LLMProvider
        class FailLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                return None
            async def stream_chat(self, model, messages, **kwargs):
                yield {}

        from backend.council import stage3_synthesize_final, CHAIRMAN_MODEL
        result = await stage3_synthesize_final("Test query", [], [], llm_provider=FailLLM())
        
        self.assertIn("Error", result['response'])
        self.assertEqual(result['model'], CHAIRMAN_MODEL)

    async def test_run_full_council_all_fail(self):
        """Test run_full_council when all models fail in Stage 1."""
        from backend.ports import LLMProvider
        class AllFailLLM(LLMProvider):
            async def chat(self, model, messages, **kwargs):
                return None
            async def stream_chat(self, model, messages, **kwargs):
                yield {}
            async def chat_parallel(self, models, messages, **kwargs):
                return {m: None for m in models}
        
        from backend.council import run_full_council, CouncilRun
        result = await run_full_council("Test query", llm_provider=AllFailLLM())
        
        self.assertIsInstance(result, CouncilRun)
        self.assertEqual(len(result.stage1_results), len(COUNCIL_MODELS))
        self.assertEqual(result.stage3_result['model'], "error")
        self.assertIn("All models failed", result.stage3_result['response'])

if __name__ == "__main__":
    unittest.main()
