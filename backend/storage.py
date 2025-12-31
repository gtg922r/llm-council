"""JSON-based storage for conversations.

Note: During the architecture refactor this module is kept as a compatibility
shim for tests and existing imports. New code should prefer the repository and
blob-store adapters under `backend/infrastructure/`.
"""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from pathlib import Path
from .config import DATA_DIR, DATA_BLOBS_DIR
from .infrastructure.blob_store import LocalFileBlobStore


def _get_blob_store() -> LocalFileBlobStore:
    # Lazily bind to the current DATA_BLOBS_DIR so tests can monkeypatch it.
    return LocalFileBlobStore(DATA_BLOBS_DIR)


def ensure_data_dir():
    """Ensure the data directory exists."""
    Path(DATA_DIR).mkdir(parents=True, exist_ok=True)


def get_conversation_path(conversation_id: str) -> str:
    """Get the file path for a conversation."""
    return os.path.join(DATA_DIR, f"{conversation_id}.json")


def create_conversation(conversation_id: str) -> Dict[str, Any]:
    """
    Create a new conversation.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New conversation dict
    """
    ensure_data_dir()

    conversation = {
        "id": conversation_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": "New Conversation",
        "is_pinned": False,
        "is_archived": False,
        "has_unread": False,
        "messages": []
    }

    # Save to file
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)

    return conversation


def get_conversation(conversation_id: str) -> Optional[Dict[str, Any]]:
    """
    Load a conversation from storage.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation dict or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        return json.load(f)


def save_conversation(conversation: Dict[str, Any]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation['id'])
    with open(path, 'w') as f:
        json.dump(conversation, f, indent=2)


def list_conversations() -> List[Dict[str, Any]]:
    """
    List all conversations (metadata only).

    Returns:
        List of conversation metadata dicts
    """
    ensure_data_dir()

    conversations = []
    for filename in os.listdir(DATA_DIR):
        if filename.endswith('.json'):
            path = os.path.join(DATA_DIR, filename)
            with open(path, 'r') as f:
                data = json.load(f)
                # Return metadata only
                conversations.append({
                    "id": data["id"],
                    "created_at": data["created_at"],
                    "title": data.get("title", "New Conversation"),
                    "is_pinned": data.get("is_pinned", False),
                    "is_archived": data.get("is_archived", False),
                    "has_unread": data.get("has_unread", False),
                    "message_count": len(data["messages"])
                })

    # Sort by creation time, newest first
    conversations.sort(key=lambda x: x["created_at"], reverse=True)

    return conversations


def add_user_message(
    conversation_id: str,
    content: str,
    files: Optional[List[Dict[str, Any]]] = None
):
    """
    Add a user message to a conversation.

    Args:
        conversation_id: Conversation identifier
        content: User message content
        files: Optional list of file context dicts
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = {
        "role": "user",
        "content": content
    }
    if files is not None:
        # Store large file contents out-of-line (blob store) and persist only
        # a reference ID in the conversation JSON.
        processed_files: list[dict[str, Any]] = []
        for file in files:
            name = file.get("name")
            size = file.get("size")
            if not name:
                raise ValueError("File context must include a name.")

            if "file_reference_id" in file:
                processed_files.append(
                    {"name": name, "file_reference_id": file["file_reference_id"], "size": size}
                )
                continue

            if "content" in file:
                reference_id = _get_blob_store().save_text(str(file["content"]))
                processed_files.append(
                    {"name": name, "file_reference_id": reference_id, "size": size}
                )
                continue

            raise ValueError("File context must include either content or file_reference_id.")

        message["files"] = processed_files

    conversation["messages"].append(message)

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None,
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["messages"].append({
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3,
        # Persisted metadata fixes "persistence amnesia" (rankings + label map).
        "metadata": metadata or {},
    })
    conversation["has_unread"] = True

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation["title"] = title
    save_conversation(conversation)


def duplicate_conversation(original_id: str, new_id: str) -> Dict[str, Any]:
    """
    Duplicate an existing conversation.

    Args:
        original_id: ID of the conversation to duplicate
        new_id: ID for the new conversation

    Returns:
        The new duplicated conversation
    """
    original = get_conversation(original_id)
    if original is None:
        raise ValueError(f"Original conversation {original_id} not found")

    new_conversation = {
        "id": new_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "title": f"{original.get('title', 'New Conversation')} (Copy)",
        "is_pinned": False,
        "is_archived": False,
        "has_unread": False,
        "messages": original["messages"].copy()
    }

    save_conversation(new_conversation)
    return new_conversation


def delete_conversation(conversation_id: str):
    """
    Permanently delete a conversation.

    Args:
        conversation_id: ID of the conversation to delete
    """
    path = get_conversation_path(conversation_id)
    if os.path.exists(path):
        os.remove(path)


def get_file_text(file_reference_id: str) -> str:
    """Resolve a stored file attachment from the blob store."""
    return _get_blob_store().get_text(file_reference_id)
