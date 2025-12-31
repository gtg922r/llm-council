"""JSON conversation repository (filesystem) implementing the ConversationRepository port."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..domain.models import Conversation, ConversationSummary
from ..ports import ConversationRepository


class JsonConversationRepository(ConversationRepository):
    def __init__(self, conversations_dir: str | Path):
        self._dir = Path(conversations_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def _path(self, conversation_id: str) -> Path:
        return self._dir / f"{conversation_id}.json"

    def create(self, conversation_id: str) -> Conversation:
        conversation = Conversation(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            title="New Conversation",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=[],
        )
        self.save(conversation)
        return conversation

    def get(self, conversation_id: str) -> Optional[Conversation]:
        path = self._path(conversation_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        # Defensive defaults for legacy JSON fields.
        data.setdefault("is_pinned", False)
        data.setdefault("is_archived", False)
        data.setdefault("has_unread", False)
        data.setdefault("messages", [])
        return Conversation.model_validate(data)

    def save(self, conversation: Conversation) -> None:
        path = self._path(conversation.id)
        payload = conversation.model_dump(mode="json", exclude_none=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list(self) -> list[ConversationSummary]:
        items: list[ConversationSummary] = []
        for path in sorted(self._dir.glob("*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            items.append(
                ConversationSummary(
                    id=data["id"],
                    created_at=data["created_at"],
                    title=data.get("title", "New Conversation"),
                    is_pinned=data.get("is_pinned", False),
                    is_archived=data.get("is_archived", False),
                    has_unread=data.get("has_unread", False),
                    message_count=len(data.get("messages", [])),
                )
            )
        # Newest first
        items.sort(key=lambda x: x.created_at, reverse=True)
        return items

    def delete(self, conversation_id: str) -> None:
        path = self._path(conversation_id)
        if path.exists():
            path.unlink()

    def duplicate(self, original_id: str, new_id: str) -> Conversation:
        original = self.get(original_id)
        if original is None:
            raise ValueError(f"Original conversation {original_id} not found")
        duplicated = Conversation(
            id=new_id,
            created_at=datetime.now(timezone.utc),
            title=f"{original.title} (Copy)",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=list(original.messages),
        )
        self.save(duplicated)
        return duplicated

