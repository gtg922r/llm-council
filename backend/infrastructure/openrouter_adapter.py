"""OpenRouter adapter implementing the LLMProvider port."""

from __future__ import annotations

from typing import Any, Optional

import httpx

from ..ports import LLMProvider


class OpenRouterAdapter(LLMProvider):
    def __init__(self, *, api_key: str, api_url: str):
        self._api_key = api_key
        self._api_url = api_url

    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        timeout: float | None = None,
    ) -> Optional[dict[str, Any]]:
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": model,
            "messages": messages,
        }

        max_retries = 1
        attempts = 0
        while attempts <= max_retries:
            try:
                async with httpx.AsyncClient(timeout=timeout or 120.0) as client:
                    response = await client.post(
                        self._api_url,
                        headers=headers,
                        json=payload,
                    )
                    response.raise_for_status()
                    data = response.json()
                    message = data["choices"][0]["message"]
                    return {
                        "content": message.get("content"),
                        "reasoning_details": message.get("reasoning_details"),
                    }
            except Exception as e:
                attempts += 1
                if attempts <= max_retries:
                    print(
                        f"Error querying model {model} (attempt {attempts}/{max_retries + 1}): {e}. Retrying..."
                    )
                    continue
                print(f"Error querying model {model} after {attempts} attempts: {e}")
                return None

