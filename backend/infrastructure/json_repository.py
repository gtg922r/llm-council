"""JSON file-based conversation repository.

Implements the ConversationRepository port using local JSON files.
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Union

from ..ports import ConversationRepository
from ..domain.models import (
    Conversation,
    ConversationMetadata,
    UserMessage,
    AssistantMessage,
    Stage1Result,
    Stage2Result,
    Stage3Result,
    CouncilMetadata,
    AggregateRanking,
    FileReference,
    Message,
)
from ..config import DATA_DIR


def _parse_message(data: dict) -> Message:
    """Parse a raw dict into a typed Message."""
    role = data.get("role")
    
    if role == "user":
        # Parse file references if present
        files = []
        for f in data.get("files", []):
            if isinstance(f, dict):
                # Check if it's a FileReference or legacy inline file
                if "blob_id" in f:
                    files.append(FileReference(**f))
                else:
                    # Legacy format - inline file (will be migrated on save)
                    files.append(FileReference(
                        name=f.get("name", "unknown"),
                        blob_id="",  # Will be empty for legacy data
                        size=f.get("size")
                    ))
        return UserMessage(
            content=data.get("content", ""),
            files=files
        )
    
    elif role == "assistant":
        # Parse stage results
        stage1 = [Stage1Result(**r) for r in data.get("stage1", [])]
        stage2 = [Stage2Result(**r) for r in data.get("stage2", [])]
        
        stage3_data = data.get("stage3")
        stage3 = Stage3Result(**stage3_data) if stage3_data else None
        
        # Parse metadata (the key fix for persistence amnesia)
        metadata_data = data.get("metadata", {})
        aggregate_rankings = [
            AggregateRanking(**r) for r in metadata_data.get("aggregate_rankings", [])
        ]
        metadata = CouncilMetadata(
            label_to_model=metadata_data.get("label_to_model", {}),
            aggregate_rankings=aggregate_rankings
        )
        
        return AssistantMessage(
            stage1=stage1,
            stage2=stage2,
            stage3=stage3,
            metadata=metadata
        )
    
    # Fallback for unknown role
    raise ValueError(f"Unknown message role: {role}")


class JsonConversationRepository(ConversationRepository):
    """JSON file-based implementation of conversation storage."""
    
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = Path(data_dir)
        self._ensure_dir()
    
    def _ensure_dir(self) -> None:
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.data_dir / f"{conversation_id}.json"
    
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        path = self._get_path(conversation_id)
        
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Parse messages
        messages = []
        for msg_data in data.get("messages", []):
            try:
                messages.append(_parse_message(msg_data))
            except ValueError as e:
                print(f"Warning: Skipping malformed message: {e}")
                continue
        
        # Parse datetime
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
        elif not isinstance(created_at, datetime):
            created_at = datetime.now(timezone.utc)
        
        return Conversation(
            id=data["id"],
            created_at=created_at,
            title=data.get("title", "New Conversation"),
            is_pinned=data.get("is_pinned", False),
            is_archived=data.get("is_archived", False),
            has_unread=data.get("has_unread", False),
            messages=messages
        )
    
    def save(self, conversation: Conversation) -> None:
        """Persist a conversation to JSON."""
        self._ensure_dir()
        
        path = self._get_path(conversation.id)
        
        # Serialize messages
        messages_data = []
        for msg in conversation.messages:
            if isinstance(msg, UserMessage):
                msg_dict = {
                    "role": "user",
                    "content": msg.content,
                }
                if msg.files:
                    msg_dict["files"] = [
                        {"name": f.name, "blob_id": f.blob_id, "size": f.size}
                        for f in msg.files
                    ]
                messages_data.append(msg_dict)
            elif isinstance(msg, AssistantMessage):
                msg_dict = {
                    "role": "assistant",
                    "stage1": [r.model_dump() for r in msg.stage1],
                    "stage2": [r.model_dump() for r in msg.stage2],
                    "stage3": msg.stage3.model_dump() if msg.stage3 else None,
                    "metadata": {
                        "label_to_model": msg.metadata.label_to_model,
                        "aggregate_rankings": [
                            r.model_dump() for r in msg.metadata.aggregate_rankings
                        ]
                    }
                }
                messages_data.append(msg_dict)
        
        # Build the full document
        doc = {
            "id": conversation.id,
            "created_at": conversation.created_at.isoformat(),
            "title": conversation.title,
            "is_pinned": conversation.is_pinned,
            "is_archived": conversation.is_archived,
            "has_unread": conversation.has_unread,
            "messages": messages_data
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(doc, f, indent=2)
    
    def list(self) -> List[ConversationMetadata]:
        """List all conversations (metadata only)."""
        self._ensure_dir()
        
        conversations = []
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = self.data_dir / filename
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Parse datetime
                created_at = data.get("created_at")
                if isinstance(created_at, str):
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                elif not isinstance(created_at, datetime):
                    created_at = datetime.now(timezone.utc)
                
                conversations.append(ConversationMetadata(
                    id=data["id"],
                    created_at=created_at,
                    title=data.get("title", "New Conversation"),
                    is_pinned=data.get("is_pinned", False),
                    is_archived=data.get("is_archived", False),
                    has_unread=data.get("has_unread", False),
                    message_count=len(data.get("messages", []))
                ))
        
        # Sort by creation time, newest first
        conversations.sort(key=lambda x: x.created_at, reverse=True)
        
        return conversations
    
    def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        path = self._get_path(conversation_id)
        
        if path.exists():
            os.remove(path)
