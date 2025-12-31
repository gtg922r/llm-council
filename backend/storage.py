"""Compatibility helpers for JSON-backed conversation persistence.

The refactor introduces `JsonConversationRepository` + `LocalFileBlobStore` as the
preferred infrastructure adapters. This module remains as a thin wrapper to avoid
breaking imports in older tests/scripts.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from . import config
from .domain.models import AssistantMessage, AssistantMessageMetadata, Conversation, FileAttachment, Stage3Result, UserMessage
from .infrastructure.blob_store import LocalFileBlobStore
from .infrastructure.json_repository import JsonConversationRepository

# Overridable in tests via monkeypatch
DATA_DIR = config.DATA_DIR
BLOB_DIR = config.BLOB_DIR


def _repo() -> JsonConversationRepository:
    return JsonConversationRepository(DATA_DIR)


def _blobs() -> LocalFileBlobStore:
    return LocalFileBlobStore(BLOB_DIR)


def ensure_data_dir():
    _repo()  # constructor ensures directory


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    return _repo().create(conversation_id).model_dump(mode="json", exclude_none=True)


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    conv = _repo().get(conversation_id)
    return None if conv is None else conv.model_dump(mode="json", exclude_none=True)


def save_conversation(conversation: Dict[str, Any]):
    conv = Conversation.model_validate(conversation)
    _repo().save(conv)


def list_conversations() -> List[Dict[str, Any]]:
    return [c.model_dump(mode="json", exclude_none=True) for c in _repo().list()]


def add_user_message(conversation_id: str, content: str, files: Optional[List[Dict[str, Any]]] = None):
    repo = _repo()
    conv = repo.get(conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    attachments: list[FileAttachment] = []
    for f in files or []:
        name = f.get("name")
        raw_content = f.get("content")
        if not name or raw_content is None:
            continue
        ref_id = _blobs().save_text(str(raw_content))
        attachments.append(FileAttachment(name=str(name), reference_id=ref_id, size=f.get("size")))

    conv.messages.append(UserMessage(content=content, files=attachments))
    repo.save(conv)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Dict[str, Any] | None = None,
):
    repo = _repo()
    conv = repo.get(conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    def _normalize_stage1(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if "response" not in item and "content" in item:
                item = dict(item)
                item["response"] = item.pop("content")
            item.setdefault("status", "success")
            normalized.append(item)
        return normalized

    def _normalize_stage2(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        normalized: List[Dict[str, Any]] = []
        for item in items:
            if "ranking" not in item and "content" in item:
                item = dict(item)
                item["ranking"] = item.pop("content")
            item.setdefault("parsed_ranking", [])
            item.setdefault("status", "success")
            normalized.append(item)
        return normalized

    stage3_model = stage3.get("model") or "unknown"
    stage3_text = stage3.get("response") or stage3.get("content") or ""
    stage3_obj = Stage3Result(model=stage3_model, response=stage3_text)

    conv.messages.append(
        AssistantMessage(
            stage1=_normalize_stage1(stage1),
            stage2=_normalize_stage2(stage2),
            stage3=stage3_obj,
            metadata=AssistantMessageMetadata.model_validate(metadata or {}),
        )
    )
    conv.has_unread = True
    repo.save(conv)


def update_conversation_title(conversation_id: str, title: str):
    repo = _repo()
    conv = repo.get(conversation_id)
    if conv is None:
        raise ValueError(f"Conversation {conversation_id} not found")
    conv.title = title
    repo.save(conv)


def duplicate_conversation(original_id: str, new_id: str) -> Dict[str, Any]:
    return _repo().duplicate(original_id, new_id).model_dump(mode="json")


def delete_conversation(conversation_id: str):
    _repo().delete(conversation_id)
