import httpx
import asyncio
import json
from typing import List, Dict, Any, Optional, AsyncGenerator
from ..ports import LLMProvider

class OpenRouterAdapter(LLMProvider):
    """OpenRouter implementation of LLMProvider."""
    
    def __init__(self, api_key: str, base_url: str = "https://openrouter.ai/api/v1/chat/completions"):
        self.api_key = api_key
        self.base_url = base_url
        
    async def chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Optional[Dict[str, Any]]:
        """Send a chat completion request to OpenRouter."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "HTTP-Referer": "https://github.com/symposia-ai/symposia",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
            **kwargs
        }
        
        timeout = kwargs.get("timeout", 120.0)
        max_retries = kwargs.get("max_retries", 3)
        
        async with httpx.AsyncClient(timeout=timeout) as client:
            for attempt in range(max_retries):
                try:
                    response = await client.post(
                        self.base_url,
                        headers=headers,
                        json=payload
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if 'choices' in result and len(result['choices']) > 0:
                            return result['choices'][0]['message']
                    
                    # Handle specific error codes if needed
                    await asyncio.sleep(1 * (attempt + 1))
                except Exception:
                    if attempt == max_retries - 1:
                        return None
                    await asyncio.sleep(1 * (attempt + 1))
                    
        return None

    async def stream_chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Not implemented yet, but required by port."""
        # Yield empty to satisfy AsyncGenerator type
        if False: yield {}
        raise NotImplementedError("Streaming not yet implemented in OpenRouterAdapter")

    async def chat_parallel(self, models: List[str], messages: List[Dict[str, Any]], **kwargs) -> Dict[str, Optional[Dict[str, Any]]]:
        """Query multiple models in parallel."""
        tasks = [
            self.chat(model, messages, **kwargs)
            for model in models
        ]
        
        results = await asyncio.gather(*tasks)
        return dict(zip(models, results))
