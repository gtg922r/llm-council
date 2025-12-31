"""OpenRouter adapter implementing the LLMProvider port."""

from __future__ import annotations

from typing import Any, Optional

from ..openrouter import query_model
from ..ports import LLMProvider


class OpenRouterAdapter(LLMProvider):
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        timeout: float | None = None,
    ) -> Optional[dict[str, Any]]:
        if timeout is None:
            return await query_model(model, messages)
        return await query_model(model, messages, timeout=timeout)

