import json
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from ..ports import ConversationRepository
from ..domain.models import Conversation

class JsonConversationRepository(ConversationRepository):
    """JSON-based implementation of ConversationRepository.
    
    Note: user_id parameter is accepted but ignored - this implementation
    stores all conversations in a single directory. Kept for interface
    compatibility and testing purposes.
    """
    
    def __init__(self, data_dir: str = "data/conversations"):
        self.data_dir = Path(data_dir)
        self.ensure_data_dir()
        
    def ensure_data_dir(self):
        """Ensure the data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)
        
    def get_path(self, conversation_id: str) -> Path:
        """Get the file path for a conversation."""
        return self.data_dir / f"{conversation_id}.json"
        
    def get(self, conversation_id: str, user_id: str = "") -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        path = self.get_path(conversation_id)
        if not path.exists():
            return None
            
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            try:
                return Conversation.model_validate(data)
            except Exception:
                # Handle or log validation error
                return None
                
    def save(self, conversation: Conversation, user_id: str = "") -> None:
        """Save a conversation."""
        path = self.get_path(conversation.id)
        data = conversation.model_dump(exclude_none=True)
        
        # We use default=str to handle any nested datetimes that model_dump 
        # might have missed, but Pydantic 2.x model_dump is usually enough.
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
            
    def list(self, user_id: str = "") -> List[Dict[str, Any]]:
        """List all conversations (metadata only)."""
        conversations = []
        if not self.data_dir.exists():
            return []
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = self.data_dir / filename
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        conv = Conversation.model_validate(data)
                        # Return metadata only
                        conversations.append({
                            "id": conv.id,
                            "created_at": conv.created_at,
                            "title": conv.title,
                            "is_pinned": conv.is_pinned,
                            "is_archived": conv.is_archived,
                            "has_unread": conv.has_unread,
                            "message_count": len(conv.messages)
                        })
                except Exception:
                    continue
                    
        # Sort by creation time, newest first
        conversations.sort(key=lambda x: x["created_at"], reverse=True)
        return conversations
        
    def delete(self, conversation_id: str, user_id: str = "") -> None:
        """Delete a conversation."""
        path = self.get_path(conversation_id)
        if path.exists():
            os.remove(path)
