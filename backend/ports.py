"""Ports (abstract interfaces) for the hexagonal architecture."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Optional

from .domain.models import Conversation, ConversationMetadata


class ConversationRepository(ABC):
    @abstractmethod
    def create(self, conversation_id: str) -> Conversation: ...

    @abstractmethod
    def get(self, conversation_id: str) -> Conversation | None: ...

    @abstractmethod
    def save(self, conversation: Conversation) -> None: ...

    @abstractmethod
    def list(self) -> list[ConversationMetadata]: ...

    @abstractmethod
    def delete(self, conversation_id: str) -> None: ...

    @abstractmethod
    def duplicate(self, original_id: str, new_id: str) -> Conversation: ...


class LLMProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        timeout: float | None = None,
    ) -> Optional[dict[str, Any]]: ...

