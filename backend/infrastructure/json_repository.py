"""JSON-based conversation repository implementation.

This module provides a filesystem-based implementation of the ConversationRepository
interface, storing conversations as JSON files.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from backend.ports import ConversationRepository
from backend.domain.models import (
    Conversation, UserMessage, AssistantMessage
)


class JsonConversationRepository(ConversationRepository):
    """JSON file-based implementation of ConversationRepository.
    
    Stores each conversation as a separate JSON file in a configured directory.
    """
    
    def __init__(self, data_dir: str = "data/conversations"):
        """Initialize the repository.
        
        Args:
            data_dir: Directory path where conversation files will be stored.
        """
        self.data_dir = Path(data_dir)
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.data_dir / f"{conversation_id}.json"
    
    def _parse_datetime(self, dt_str: str) -> datetime:
        """Parse a datetime string, handling 'Z' suffix."""
        if dt_str.endswith('Z'):
            dt_str = dt_str[:-1] + '+00:00'
        return datetime.fromisoformat(dt_str)
    
    def _parse_messages(
        self, messages_data: List[Dict[str, Any]]
    ) -> List[Union[UserMessage, AssistantMessage]]:
        """Parse message data into domain models."""
        messages: List[Union[UserMessage, AssistantMessage]] = []
        for msg_data in messages_data:
            if msg_data.get("role") == "user":
                messages.append(UserMessage.model_validate(msg_data))
            elif msg_data.get("role") == "assistant":
                messages.append(AssistantMessage.model_validate(msg_data))
        return messages
    
    def create(self, conversation_id: str) -> Conversation:
        """Create a new conversation."""
        self._ensure_dir()
        
        conversation = Conversation(
            id=conversation_id,
            created_at=datetime.now(timezone.utc),
            title="New Conversation",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=[]
        )
        
        self.save(conversation)
        return conversation
    
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        path = self._get_path(conversation_id)
        
        if not path.exists():
            return None
        
        with open(path, 'r') as f:
            data = json.load(f)
        
        messages = self._parse_messages(data.get("messages", []))
        
        return Conversation(
            id=data["id"],
            created_at=self._parse_datetime(data["created_at"]) if isinstance(data["created_at"], str) else data["created_at"],
            title=data.get("title", "New Conversation"),
            is_pinned=data.get("is_pinned", False),
            is_archived=data.get("is_archived", False),
            has_unread=data.get("has_unread", False),
            messages=messages
        )
    
    def save(self, conversation: Conversation) -> None:
        """Save a conversation."""
        self._ensure_dir()
        
        path = self._get_path(conversation.id)
        data = conversation.model_dump(mode='json')
        
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)
    
    def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        path = self._get_path(conversation_id)
        if path.exists():
            path.unlink()
    
    def list_all(self) -> List[Dict[str, Any]]:
        """List all conversations (metadata only)."""
        self._ensure_dir()
        
        conversations = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = self.data_dir / filename
                with open(path, 'r') as f:
                    data = json.load(f)
                    conversations.append({
                        "id": data["id"],
                        "created_at": data["created_at"],
                        "title": data.get("title", "New Conversation"),
                        "is_pinned": data.get("is_pinned", False),
                        "is_archived": data.get("is_archived", False),
                        "has_unread": data.get("has_unread", False),
                        "message_count": len(data.get("messages", []))
                    })
        
        # Sort by creation time, newest first
        conversations.sort(key=lambda x: x["created_at"], reverse=True)
        
        return conversations
    
    def add_message(
        self,
        conversation_id: str,
        message: UserMessage | AssistantMessage
    ) -> None:
        """Add a message to a conversation."""
        conversation = self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation.messages.append(message)
        
        # Mark as having unread if it's an assistant message
        if isinstance(message, AssistantMessage):
            conversation.has_unread = True
        
        self.save(conversation)
    
    def update_title(self, conversation_id: str, title: str) -> None:
        """Update the conversation title."""
        conversation = self.get(conversation_id)
        if conversation is None:
            raise ValueError(f"Conversation {conversation_id} not found")
        
        conversation.title = title
        self.save(conversation)
    
    def duplicate(self, original_id: str, new_id: str) -> Conversation:
        """Duplicate an existing conversation.
        
        Args:
            original_id: ID of the conversation to duplicate.
            new_id: ID for the new conversation.
        
        Returns:
            The new duplicated Conversation.
        """
        original = self.get(original_id)
        if original is None:
            raise ValueError(f"Original conversation {original_id} not found")
        
        new_conversation = Conversation(
            id=new_id,
            created_at=datetime.now(timezone.utc),
            title=f"{original.title} (Copy)",
            is_pinned=False,
            is_archived=False,
            has_unread=False,
            messages=list(original.messages)
        )
        
        self.save(new_conversation)
        return new_conversation
    
    def update_flags(
        self,
        conversation_id: str,
        is_pinned: Optional[bool] = None,
        is_archived: Optional[bool] = None,
        has_unread: Optional[bool] = None
    ) -> Optional[Conversation]:
        """Update conversation flags.
        
        Args:
            conversation_id: The conversation identifier.
            is_pinned: New pinned status (if not None).
            is_archived: New archived status (if not None).
            has_unread: New unread status (if not None).
        
        Returns:
            The updated Conversation, or None if not found.
        """
        conversation = self.get(conversation_id)
        if conversation is None:
            return None
        
        if is_pinned is not None:
            conversation.is_pinned = is_pinned
        if is_archived is not None:
            conversation.is_archived = is_archived
        if has_unread is not None:
            conversation.has_unread = has_unread
        
        self.save(conversation)
        return conversation
