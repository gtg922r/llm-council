"""OpenRouter API adapter implementing the LLMProvider port."""

import asyncio
from typing import List, Dict, Any, Optional

import httpx

from ..ports import LLMProvider
from ..config import OPENROUTER_API_KEY, OPENROUTER_API_URL


class OpenRouterAdapter(LLMProvider):
    """OpenRouter API implementation of the LLM provider."""
    
    def __init__(
        self,
        api_key: str = OPENROUTER_API_KEY,
        api_url: str = OPENROUTER_API_URL
    ):
        self.api_key = api_key
        self.api_url = api_url
    
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0,
        max_retries: int = 1
    ) -> Optional[Dict[str, Any]]:
        """Send a chat request to an LLM model via OpenRouter.
        
        Args:
            model: OpenRouter model identifier (e.g., "openai/gpt-4o")
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            max_retries: Number of retries on failure
            
        Returns:
            Response dict with 'content' and optional 'reasoning_details',
            or None if failed.
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        payload = {
            "model": model,
            "messages": messages,
        }
        
        attempts = 0
        while attempts <= max_retries:
            try:
                async with httpx.AsyncClient(timeout=timeout) as client:
                    response = await client.post(
                        self.api_url,
                        headers=headers,
                        json=payload
                    )
                    response.raise_for_status()
                    
                    data = response.json()
                    message = data['choices'][0]['message']
                    
                    return {
                        'content': message.get('content'),
                        'reasoning_details': message.get('reasoning_details')
                    }
            
            except Exception as e:
                attempts += 1
                if attempts <= max_retries:
                    print(f"Error querying model {model} (attempt {attempts}/{max_retries + 1}): {e}. Retrying...")
                    continue
                else:
                    print(f"Error querying model {model} after {attempts} attempts: {e}")
                    return None
    
    async def chat_parallel(
        self,
        models: List[str],
        messages: List[Dict[str, str]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Send chat requests to multiple models in parallel.
        
        Args:
            models: List of OpenRouter model identifiers
            messages: List of message dicts to send to each model
            
        Returns:
            Dict mapping model identifier to response dict (or None if failed)
        """
        tasks = [self.chat(model, messages) for model in models]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        mapped_responses = {}
        for model, result in zip(models, results):
            if isinstance(result, Exception):
                print(f"Exception raised while querying model {model}: {result}")
                mapped_responses[model] = None
            else:
                mapped_responses[model] = result
        
        return mapped_responses
