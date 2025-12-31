"""JSON conversation repository (filesystem-backed)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from ..domain.models import Conversation, ConversationMetadata
from ..ports import ConversationRepository


class JsonConversationRepository(ConversationRepository):
    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)

    def _ensure_dir(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def _path_for(self, conversation_id: str) -> Path:
        return self._base_dir / f"{conversation_id}.json"

    def create(self, conversation_id: str) -> Conversation:
        self._ensure_dir()
        conversation = Conversation(
            id=conversation_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            title="New Conversation",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=[],
        )
        self.save(conversation)
        return conversation

    def get(self, conversation_id: str) -> Conversation | None:
        path = self._path_for(conversation_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        return Conversation.model_validate(data)

    def save(self, conversation: Conversation) -> None:
        self._ensure_dir()
        path = self._path_for(conversation.id)
        # NOTE: We intentionally keep defaults here because the message union
        # discriminator (`role`) must always be present for robust loading.
        payload = conversation.model_dump(exclude_none=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def list(self) -> list[ConversationMetadata]:
        self._ensure_dir()
        conversations: list[ConversationMetadata] = []
        for path in self._base_dir.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            conversations.append(
                ConversationMetadata(
                    id=data["id"],
                    created_at=data["created_at"],
                    title=data.get("title", "New Conversation"),
                    is_pinned=data.get("is_pinned", False),
                    is_archived=data.get("is_archived", False),
                    has_unread=data.get("has_unread", False),
                    message_count=len(data.get("messages", [])),
                )
            )
        conversations.sort(key=lambda x: x.created_at, reverse=True)
        return conversations

    def delete(self, conversation_id: str) -> None:
        path = self._path_for(conversation_id)
        if path.exists():
            path.unlink()

    def duplicate(self, original_id: str, new_id: str) -> Conversation:
        original = self.get(original_id)
        if original is None:
            raise ValueError(f"Original conversation {original_id} not found")
        duplicated = Conversation(
            id=new_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            title=f"{original.title} (Copy)",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=original.messages,
        )
        self.save(duplicated)
        return duplicated

