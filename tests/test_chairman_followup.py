import unittest
from unittest.mock import patch, AsyncMock
from backend.council import chairman_followup, CHAIRMAN_MODEL

class TestChairmanFollowup(unittest.IsolatedAsyncioTestCase):
    
    async def test_chairman_followup_context_construction(self):
        """
        Test that the chairman_followup function correctly constructs the context
        including original query, council results, initial response, and follow-up.
        """
        # Mock data
        original_query = "What is 2+2?"
        stage1_results = [
            {"model": "ModelA", "response": "The answer is 4.", "status": "success"},
            {"model": "ModelB", "response": "2+2 = 4", "status": "success"}
        ]
        stage2_results = [
            {"model": "ModelA", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B", "status": "success"},
            {"model": "ModelB", "ranking": "FINAL RANKING:\n1. Response A\n2. Response B", "status": "success"}
        ]
        stage3_response = "Based on the council, the answer is 4."
        followup_query = "Are you absolutely sure?"

        # Mock OpenRouter response
        expected_response_text = "Yes, strictly speaking, 2+2 is 4 in standard arithmetic."
        
        with patch('backend.council.query_model', new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {"content": expected_response_text}

            # Call the function
            result = await chairman_followup(
                original_query=original_query,
                stage1_results=stage1_results,
                stage2_results=stage2_results,
                stage3_response=stage3_response,
                followup_query=followup_query
            )

            # Assertions
            self.assertEqual(result["model"], CHAIRMAN_MODEL)
            self.assertEqual(result["response"], expected_response_text)

            # Verify the prompt construction
            args, _ = mock_query.call_args
            model_id, messages = args
            prompt = messages[0]["content"]
            
            # Check that the prompt contains all necessary context
            self.assertIn("Original Question: What is 2+2?", prompt)
            self.assertIn("STAGE 1 - Individual Responses:", prompt)
            self.assertIn("Model: ModelA", prompt)
            self.assertIn("The answer is 4.", prompt) # Stage 1 content
            self.assertIn("STAGE 2 - Peer Rankings:", prompt)
            self.assertIn("FINAL RANKING:", prompt) # Stage 2 content
            self.assertIn("Chairman's Initial Response:", prompt)
            self.assertIn("Based on the council, the answer is 4.", prompt) # Stage 3 content
            self.assertIn("User Follow-up Question: Are you absolutely sure?", prompt)

if __name__ == "__main__":
    unittest.main()