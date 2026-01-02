import pytest
from unittest.mock import patch, MagicMock
from backend.infrastructure.openrouter_adapter import OpenRouterAdapter

@pytest.mark.asyncio
async def test_openrouter_adapter_chat():
    adapter = OpenRouterAdapter(api_key="test-key")
    
    messages = [{"role": "user", "content": "Hi"}]
    expected_response = {"content": "Hello"}
    
    with patch("httpx.AsyncClient.post") as mock_post:
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "choices": [{"message": expected_response}]
        }
        mock_post.return_value = mock_resp
        
        result = await adapter.chat("test-model", messages)
        assert result == expected_response
