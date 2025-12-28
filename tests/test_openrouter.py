"""Tests for backend/openrouter.py."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock
import httpx
from backend.openrouter import query_model

class TestOpenRouter(unittest.IsolatedAsyncioTestCase):

    @patch('httpx.AsyncClient.post')
    async def test_query_model_retry_on_failure(self, mock_post):
        """Test that query_model retries once on transient failure."""
        # First call fails with 503, second succeeds
        mock_post.side_effect = [
            MagicMock(status_code=503, raise_for_status=MagicMock(side_effect=httpx.HTTPStatusError("503", request=MagicMock(), response=MagicMock(status_code=503)))),
            MagicMock(status_code=200, json=lambda: {"choices": [{"message": {"content": "Success"}}]})
        ]
        
        result = await query_model("test-model", [{"role": "user", "content": "hi"}])
        
        self.assertEqual(result['content'], "Success")
        self.assertEqual(mock_post.call_count, 2)

    @patch('httpx.AsyncClient.post')
    async def test_query_model_max_retries(self, mock_post):
        """Test that query_model stops after 1 retry (2 total attempts)."""
        # Both calls fail
        mock_post.side_effect = httpx.HTTPStatusError("500", request=MagicMock(), response=MagicMock(status_code=500))
        
        result = await query_model("test-model", [{"role": "user", "content": "hi"}])
        
        self.assertIsNone(result)
        self.assertEqual(mock_post.call_count, 2)

    @patch('httpx.AsyncClient.post')
    async def test_query_model_timeout(self, mock_post):
        """Test that query_model handles timeout."""
        mock_post.side_effect = httpx.TimeoutException("Timeout")
        
        result = await query_model("test-model", [{"role": "user", "content": "hi"}], timeout=0.1)
        
        self.assertIsNone(result)
        # It should still retry on timeout? Let's decide. Usually yes.
        # If we implement retries for all Exceptions, it will retry.
        self.assertEqual(mock_post.call_count, 2)

if __name__ == "__main__":
    unittest.main()
