"""Reproduction script for LLM Council error handling."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
import backend.council
import backend.openrouter

class TestResilience(unittest.IsolatedAsyncioTestCase):
    
    @patch('backend.council.query_model')
    async def test_stage1_partial_failure(self, mock_query):
        """Test Stage 1 when some models fail."""
        # We need to know what COUNCIL_MODELS are
        from backend.config import COUNCIL_MODELS
        
        # Mock behavior: First model fails (None), others succeed
        def side_effect(model, messages, timeout=120.0):
            if model == COUNCIL_MODELS[0]:
                return None
            return {'content': f"Response from {model}"}
        
        mock_query.side_effect = side_effect
        
        # Also need to mock query_models_parallel because it's imported in council.py
        async def mock_parallel(models, messages):
            tasks = [backend.council.query_model(m, messages) for m in models]
            responses = await asyncio.gather(*tasks)
            return {m: r for m, r in zip(models, responses)}
            
        with patch('backend.council.query_models_parallel', side_effect=mock_parallel):
            results = await backend.council.stage1_collect_responses("Test query")
        
        print(f"\nStage 1 results with partial failure: {len(results)}/{len(COUNCIL_MODELS)} succeeded")
        for r in results:
            print(f" - {r['model']}: {r['response'][:20]}...")
            
        self.assertEqual(len(results), len(COUNCIL_MODELS) - 1)
        self.assertGreater(len(results), 0)

    @patch('backend.council.query_model')
    async def test_full_council_resilience(self, mock_query):
        """Test full council when some models fail at different stages."""
        from backend.config import COUNCIL_MODELS, CHAIRMAN_MODEL
        
        # Mock query_model to fail for certain models or based on prompt content
        def side_effect(model, messages, timeout=120.0):
            prompt = messages[0]['content']
            # Simulate failure in Stage 1 for the first model
            if model == COUNCIL_MODELS[0] and "evaluat" not in prompt and "Chairman" not in prompt:
                return None
            # Simulate failure in Stage 2 for the second model
            if model == COUNCIL_MODELS[1] and "evaluat" in prompt:
                return None
            
            if "evaluat" in prompt:
                return {'content': "Evaluation text\n\nFINAL RANKING:\n1. Response A"}
            if "Chairman" in prompt:
                return {'content': "Final synthesis"}
            
            return {'content': f"Response from {model}"}

        mock_query.side_effect = side_effect
        
        async def mock_parallel(models, messages):
            tasks = [backend.council.query_model(m, messages) for m in models]
            responses = await asyncio.gather(*tasks)
            return {m: r for m, r in zip(models, responses)}

        with patch('backend.council.query_models_parallel', side_effect=mock_parallel):
            stage1, stage2, stage3, metadata = await backend.council.run_full_council("Test query")
        
        print(f"\nFull Council Results:")
        print(f"Stage 1: {len(stage1)} responses")
        print(f"Stage 2: {len(stage2)} rankings")
        print(f"Stage 3: {stage3['model']} - {stage3['response']}")
        
        self.assertEqual(len(stage1), len(COUNCIL_MODELS) - 1)
        self.assertEqual(len(stage2), len(COUNCIL_MODELS) - 1) # Second model failed in Stage 2
        self.assertEqual(stage3['response'], "Final synthesis")

if __name__ == "__main__":
    unittest.main()