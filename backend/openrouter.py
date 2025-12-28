"""OpenRouter API client for making LLM requests."""

import httpx
from typing import List, Dict, Any, Optional
from .config import OPENROUTER_API_KEY, OPENROUTER_API_URL


async def query_model(
    model: str,
    messages: List[Dict[str, str]],
    timeout: float = 120.0,
    max_retries: int = 1
) -> Optional[Dict[str, Any]]:
    """
    Query a single model via OpenRouter API.

    Args:
        model: OpenRouter model identifier (e.g., "openai/gpt-4o")
        messages: List of message dicts with 'role' and 'content'
        timeout: Request timeout in seconds
        max_retries: Number of retries on failure

    Returns:
        Response dict with 'content' and optional 'reasoning_details', or None if failed
    """
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
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
                    OPENROUTER_API_URL,
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
                # Small backoff could be added here if needed
                continue
            else:
                print(f"Error querying model {model} after {attempts} attempts: {e}")
                return None



async def query_models_parallel(
    models: List[str],
    messages: List[Dict[str, str]]
) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Query multiple models in parallel.

    Args:
        models: List of OpenRouter model identifiers
        messages: List of message dicts to send to each model

    Returns:
        Dict mapping model identifier to response dict (or None if failed)
    """
    import asyncio

    # Create tasks for all models
    tasks = [query_model(model, messages) for model in models]

    # Wait for all to complete, catching exceptions
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Map models to their responses, handling any raised exceptions
    mapped_responses = {}
    for model, result in zip(models, results):
        if isinstance(result, Exception):
            print(f"Exception raised while querying model {model}: {result}")
            mapped_responses[model] = None
        else:
            mapped_responses[model] = result

    return mapped_responses

