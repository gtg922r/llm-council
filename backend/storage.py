"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from .config import DATA_DIR
from .domain.models import (
    Conversation, UserMessage, AssistantMessage, Message
)


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
        message["files"] = files

    conversation["messages"].append(message)

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Dict[str, Any]],
    stage2: List[Dict[str, Any]],
    stage3: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
):
    """
    Add an assistant message with all 3 stages to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
        metadata: Optional metadata including label_to_model and aggregate_rankings
    """
    conversation = get_conversation(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    message = {
        "role": "assistant",
        "stage1": stage1,
        "stage2": stage2,
        "stage3": stage3
    }
    
    # Include metadata if provided (fixes persistence of aggregate rankings)
    if metadata is not None:
        message["metadata"] = metadata

    conversation["messages"].append(message)
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


# =============================================================================
# Typed API (using Domain Models)
# =============================================================================

def create_conversation_typed(conversation_id: str) -> Conversation:
    """
    Create a new conversation using domain models.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        New Conversation domain model
    """
    ensure_data_dir()

    conversation = Conversation(
        id=conversation_id,
        created_at=datetime.now(timezone.utc),
        title="New Conversation",
        is_pinned=False,
        is_archived=False,
        has_unread=False,
        messages=[]
    )

    # Save to file
    save_conversation_typed(conversation)

    return conversation


def get_conversation_typed(conversation_id: str) -> Optional[Conversation]:
    """
    Load a conversation from storage as a domain model.

    Args:
        conversation_id: Unique identifier for the conversation

    Returns:
        Conversation domain model or None if not found
    """
    path = get_conversation_path(conversation_id)

    if not os.path.exists(path):
        return None

    with open(path, 'r') as f:
        data = json.load(f)
    
    # Parse messages - discriminate by 'role' field
    messages: List[Union[UserMessage, AssistantMessage]] = []
    for msg_data in data.get("messages", []):
        if msg_data.get("role") == "user":
            messages.append(UserMessage.model_validate(msg_data))
        elif msg_data.get("role") == "assistant":
            messages.append(AssistantMessage.model_validate(msg_data))
    
    # Build conversation - handle datetime parsing
    created_at_str = data["created_at"]
    if isinstance(created_at_str, str):
        # Handle ISO format with 'Z' suffix (UTC indicator)
        if created_at_str.endswith('Z'):
            created_at_str = created_at_str[:-1] + '+00:00'
        created_at = datetime.fromisoformat(created_at_str)
    else:
        created_at = created_at_str
    
    return Conversation(
        id=data["id"],
        created_at=created_at,
        title=data.get("title", "New Conversation"),
        is_pinned=data.get("is_pinned", False),
        is_archived=data.get("is_archived", False),
        has_unread=data.get("has_unread", False),
        messages=messages
    )


def save_conversation_typed(conversation: Conversation):
    """
    Save a conversation to storage using domain models.

    Args:
        conversation: Conversation domain model to save
    """
    ensure_data_dir()

    path = get_conversation_path(conversation.id)
    
    # Serialize conversation to JSON-compatible dict
    data = conversation.model_dump(mode='json')
    
    with open(path, 'w') as f:
        json.dump(data, f, indent=2)


def add_message_typed(
    conversation_id: str,
    message: Union[UserMessage, AssistantMessage]
):
    """
    Add a message to a conversation using domain models.

    Args:
        conversation_id: Conversation identifier
        message: UserMessage or AssistantMessage to add
    """
    conversation = get_conversation_typed(conversation_id)
    if conversation is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation.messages.append(message)
    
    # Mark as having unread if it's an assistant message
    if isinstance(message, AssistantMessage):
        conversation.has_unread = True

    save_conversation_typed(conversation)
