"""Tests for backend/council.py resilience."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
from backend.council import stage1_collect_responses, stage2_collect_rankings, stage3_synthesize_final, run_full_council, CHAIRMAN_MODEL
from backend.config import COUNCIL_MODELS

class TestCouncilResilience(unittest.IsolatedAsyncioTestCase):

    @patch('backend.openrouter.query_model')
    async def test_stage1_handles_exceptions(self, mock_query):
        """Test Stage 1 handles exceptions from query_model."""
        # One model raises exception, others succeed
        def side_effect(model, messages, timeout=120.0, max_retries=1):
            if model == COUNCIL_MODELS[0]:
                raise RuntimeError("Unexpected error")
            return {'content': f"Response from {model}"}
        
        mock_query.side_effect = side_effect
        
        results = await stage1_collect_responses("Test query")
        
        # We expect ALL models to be present
        self.assertEqual(len(results), len(COUNCIL_MODELS))
        error_results = [r for r in results if r.get('status') == "error"]
        self.assertEqual(len(error_results), 1)

    @patch('backend.openrouter.query_model')
    async def test_stage2_handles_exceptions(self, mock_query):
        """Test Stage 2 handles exceptions from query_model."""
        stage1_results = [
            {"model": m, "response": f"Response {m}", "status": "success"}
            for m in COUNCIL_MODELS
        ]
        
        # One model fails in Stage 2
        def side_effect(model, messages, timeout=120.0, max_retries=1):
            if model == COUNCIL_MODELS[0]:
                raise RuntimeError("Stage 2 error")
            return {'content': "Ranking text\n\nFINAL RANKING:\n1. Response A"}
        
        mock_query.side_effect = side_effect
        
        results, mapping = await stage2_collect_rankings("Test query", stage1_results)
        
        self.assertEqual(len(results), len(COUNCIL_MODELS))
        error_results = [r for r in results if r.get('status') == "error"]
        self.assertEqual(len(error_results), 1)

    @patch('backend.council.query_model')
    async def test_stage3_handles_failure(self, mock_query):
        """Test Stage 3 handles chairman failure."""
        mock_query.return_value = None
        
        from backend.council import stage3_synthesize_final, CHAIRMAN_MODEL
        result = await stage3_synthesize_final("Test query", [], [])
        
        self.assertIn("Error", result['response'])
        self.assertEqual(result['model'], CHAIRMAN_MODEL)

    @patch('backend.openrouter.query_model')
    @patch('backend.council.query_model')
    async def test_run_full_council_all_fail(self, mock_council_query, mock_openrouter_query):
        """Test run_full_council when all models fail in Stage 1."""
        mock_council_query.return_value = None
        mock_openrouter_query.return_value = None
        
        from backend.council import run_full_council
        stage1, stage2, stage3, metadata = await run_full_council("Test query")
        
        self.assertEqual(len(stage1), len(COUNCIL_MODELS))
        self.assertEqual(stage3['model'], "error")
        self.assertIn("All models failed", stage3['response'])

if __name__ == "__main__":
    unittest.main()
