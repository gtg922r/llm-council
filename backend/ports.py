"""Ports (interfaces) for the hexagonal architecture.

Application services depend on these abstractions instead of concrete infrastructure.
"""

from __future__ import annotations

from typing import Any, Optional, Protocol, runtime_checkable

from .domain.models import Conversation, ConversationSummary


@runtime_checkable
class ConversationRepository(Protocol):
    def create(self, conversation_id: str) -> Conversation: ...

    def get(self, conversation_id: str) -> Optional[Conversation]: ...

    def save(self, conversation: Conversation) -> None: ...

    def list(self) -> list[ConversationSummary]: ...

    def delete(self, conversation_id: str) -> None: ...

    def duplicate(self, original_id: str, new_id: str) -> Conversation: ...


@runtime_checkable
class BlobStore(Protocol):
    def save_text(self, content: str) -> str: ...

    def get_text(self, reference_id: str) -> str: ...


@runtime_checkable
class LLMProvider(Protocol):
    async def chat(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        timeout: float | None = None,
    ) -> Optional[dict[str, Any]]: ...

