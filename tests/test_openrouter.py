"""Tests for the OpenRouterAdapter."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock, AsyncMock
import httpx

from backend.infrastructure.openrouter_adapter import OpenRouterAdapter


class TestOpenRouterAdapter(unittest.IsolatedAsyncioTestCase):
    """Test the OpenRouter adapter implementation."""

    @patch('httpx.AsyncClient.post')
    async def test_chat_returns_message_content(self, mock_post):
        """Test successful chat returns message content."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Hello, world!"}}]
        }
        mock_post.return_value = mock_response
        
        adapter = OpenRouterAdapter(api_key="test-key")
        result = await adapter.chat("test-model", [{"role": "user", "content": "hi"}])
        
        self.assertEqual(result["content"], "Hello, world!")

    @patch('httpx.AsyncClient.post')
    async def test_chat_retries_on_failure(self, mock_post):
        """Test that chat retries on transient failure."""
        # First call fails with 503, second succeeds
        fail_response = MagicMock()
        fail_response.status_code = 503
        
        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {
            "choices": [{"message": {"content": "Success"}}]
        }
        
        mock_post.side_effect = [fail_response, success_response]
        
        adapter = OpenRouterAdapter(api_key="test-key")
        result = await adapter.chat(
            "test-model", 
            [{"role": "user", "content": "hi"}],
            max_retries=3
        )
        
        self.assertEqual(result["content"], "Success")
        self.assertEqual(mock_post.call_count, 2)

    @patch('httpx.AsyncClient.post')
    async def test_chat_returns_none_after_max_retries(self, mock_post):
        """Test that chat returns None after max retries."""
        fail_response = MagicMock()
        fail_response.status_code = 500
        mock_post.return_value = fail_response
        
        adapter = OpenRouterAdapter(api_key="test-key")
        result = await adapter.chat(
            "test-model", 
            [{"role": "user", "content": "hi"}],
            max_retries=2
        )
        
        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('httpx.AsyncClient.post')
    async def test_chat_handles_timeout(self, mock_post):
        """Test that chat handles timeout exceptions."""
        mock_post.side_effect = httpx.TimeoutException("Timeout")
        
        adapter = OpenRouterAdapter(api_key="test-key")
        result = await adapter.chat(
            "test-model", 
            [{"role": "user", "content": "hi"}],
            max_retries=2
        )
        
        self.assertIsNone(result)

    @patch('httpx.AsyncClient.post')
    async def test_chat_parallel_queries_all_models(self, mock_post):
        """Test chat_parallel queries all models."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "Response"}}]
        }
        mock_post.return_value = mock_response
        
        adapter = OpenRouterAdapter(api_key="test-key")
        models = ["model-a", "model-b", "model-c"]
        
        results = await adapter.chat_parallel(
            models, 
            [{"role": "user", "content": "hi"}]
        )
        
        self.assertEqual(len(results), 3)
        for model in models:
            self.assertIn(model, results)
            self.assertEqual(results[model]["content"], "Response")

    @patch('httpx.AsyncClient.post')
    async def test_chat_parallel_handles_partial_failures(self, mock_post):
        """Test chat_parallel handles partial failures."""
        call_count = [0]
        
        async def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                raise httpx.TimeoutException("Timeout")
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {
                "choices": [{"message": {"content": "Response"}}]
            }
            return mock_response
        
        mock_post.side_effect = side_effect
        
        adapter = OpenRouterAdapter(api_key="test-key")
        models = ["model-a", "model-b"]
        
        results = await adapter.chat_parallel(
            models, 
            [{"role": "user", "content": "hi"}],
            max_retries=1
        )
        
        self.assertEqual(len(results), 2)
        # One should have failed (None), one should have succeeded
        values = list(results.values())
        self.assertTrue(None in values or any(v is None for v in values))


if __name__ == "__main__":
    unittest.main()
