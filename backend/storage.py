"""JSON-based storage for conversations."""

import json
import os
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional, Union
from pathlib import Path
from .config import DATA_DIR
from .infrastructure.blob_store import BlobStore
from .domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage, 
    AssistantMetadata,
    Stage1Result,
    Stage2Result,
    Attachment
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

    conversation = Conversation(
        id=conversation_id,
        created_at=datetime.now(timezone.utc),
        title="New Conversation",
        messages=[]
    )

    # Save to file
    save_conversation(conversation)

    return conversation.model_dump()


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
        data = json.load(f)
        # Validate through Pydantic to ensure all fields (including metadata) are present
        try:
            conv = Conversation.model_validate(data)
            return conv.model_dump(exclude_none=True)
        except Exception as e:
            # Fallback for legacy data if needed, or just return as is
            # For this refactor, we want to ensure it matches the model
            return data


def save_conversation(conversation: Union[Dict[str, Any], Conversation]):
    """
    Save a conversation to storage.

    Args:
        conversation: Conversation dict or object to save
    """
    ensure_data_dir()

    if isinstance(conversation, Conversation):
        conversation_id = conversation.id
        data = conversation.model_dump(exclude_none=True)
    else:
        conversation_id = conversation['id']
        data = conversation

    # Custom JSON encoder to handle datetime if we were using raw dicts with datetime objects
    # But Pydantic's model_dump handles it.
    
    path = get_conversation_path(conversation_id)
    with open(path, 'w') as f:
        json.dump(data, f, indent=2, default=str)


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
                try:
                    data = json.load(f)
                    # Use Pydantic to validate and handle defaults
                    conv = Conversation.model_validate(data)
                    # Return metadata only
                    conversations.append({
                        "id": conv.id,
                        "created_at": conv.created_at.isoformat() if isinstance(conv.created_at, datetime) else conv.created_at,
                        "title": conv.title,
                        "is_pinned": conv.is_pinned,
                        "is_archived": conv.is_archived,
                        "has_unread": conv.has_unread,
                        "message_count": len(conv.messages)
                    })
                except Exception:
                    # Skip malformed files
                    continue

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
    data = get_conversation(conversation_id)
    if data is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation = Conversation.model_validate(data)
    
    blob_store = BlobStore()
    
    attachments = []
    if files:
        for f in files:
            # Save content to blob store if present
            file_content = f.get("content", "")
            ref_id = blob_store.save_text(file_content)
            
            attachments.append(Attachment(
                filename=f.get("name") or f.get("filename", "unnamed"),
                content_type=f.get("content_type", "text/plain"),
                file_reference_id=ref_id,
                size=f.get("size")
            ))

    message = UserMessage(
        content=content,
        files=attachments
    )
    
    conversation.messages.append(message)

    save_conversation(conversation)


def add_assistant_message(
    conversation_id: str,
    stage1: List[Union[Dict[str, Any], Stage1Result]],
    stage2: List[Union[Dict[str, Any], Stage2Result]],
    stage3: Dict[str, Any],
    metadata: Optional[Union[Dict[str, Any], AssistantMetadata]] = None
):
    """
    Add an assistant message with all 3 stages and metadata to a conversation.

    Args:
        conversation_id: Conversation identifier
        stage1: List of individual model responses
        stage2: List of model rankings
        stage3: Final synthesized response
        metadata: Optional metadata (label map, aggregate rankings)
    """
    data = get_conversation(conversation_id)
    if data is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation = Conversation.model_validate(data)

    # Convert inputs to models if they are dicts
    s1 = [Stage1Result.model_validate(i) if isinstance(i, dict) else i for i in stage1]
    s2 = [Stage2Result.model_validate(i) if isinstance(i, dict) else i for i in stage2]
    
    meta = AssistantMetadata()
    if metadata:
        meta = AssistantMetadata.model_validate(metadata) if isinstance(metadata, dict) else metadata

    message = AssistantMessage(
        stage1=s1,
        stage2=s2,
        stage3=stage3,
        metadata=meta
    )

    conversation.messages.append(message)
    conversation.has_unread = True

    save_conversation(conversation)


def update_conversation_title(conversation_id: str, title: str):
    """
    Update the title of a conversation.

    Args:
        conversation_id: Conversation identifier
        title: New title for the conversation
    """
    data = get_conversation(conversation_id)
    if data is None:
        raise ValueError(f"Conversation {conversation_id} not found")

    conversation = Conversation.model_validate(data)
    conversation.title = title
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
    data = get_conversation(original_id)
    if data is None:
        raise ValueError(f"Original conversation {original_id} not found")

    original = Conversation.model_validate(data)
    
    new_conversation = Conversation(
        id=new_id,
        created_at=datetime.now(timezone.utc),
        title=f"{original.title} (Copy)",
        messages=original.messages.copy()
    )

    save_conversation(new_conversation)
    return new_conversation.model_dump()


def delete_conversation(conversation_id: str):
    """
    Permanently delete a conversation.

    Args:
        conversation_id: ID of the conversation to delete
    """
    path = get_conversation_path(conversation_id)
    if os.path.exists(path):
        os.remove(path)
