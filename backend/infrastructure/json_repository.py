import os
import json
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime, timezone
from ..domain.models import Conversation
from ..ports import ConversationRepository
from ..config import DATA_DIR

class JsonConversationRepository(ConversationRepository):
    def __init__(self, data_dir: str = DATA_DIR):
        self.data_dir = data_dir
        self._ensure_data_dir()

    def _ensure_data_dir(self):
        Path(self.data_dir).mkdir(parents=True, exist_ok=True)

    def _get_path(self, conversation_id: str) -> str:
        return os.path.join(self.data_dir, f"{conversation_id}.json")

    def create(self, conversation_id: str) -> Conversation:
        conversation = Conversation(
            id=conversation_id,
            created_at=datetime.now(timezone.utc).isoformat(),
            title="New Conversation"
        )
        self.save(conversation)
        return conversation

    def get(self, conversation_id: str) -> Optional[Conversation]:
        path = self._get_path(conversation_id)
        if not os.path.exists(path):
            return None
        
        try:
            with open(path, 'r') as f:
                data = json.load(f)
            return Conversation(**data)
        except Exception as e:
            print(f"Error loading conversation {conversation_id}: {e}")
            return None

    def save(self, conversation: Conversation):
        path = self._get_path(conversation.id)
        with open(path, 'w') as f:
            f.write(conversation.model_dump_json(indent=2))

    def list_metadata(self) -> List[Dict[str, Any]]:
        conversations = []
        if not os.path.exists(self.data_dir):
            return []
            
        for filename in os.listdir(self.data_dir):
            if filename.endswith('.json'):
                path = os.path.join(self.data_dir, filename)
                try:
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
                except Exception as e:
                    print(f"Error reading conversation {filename}: {e}")

        conversations.sort(key=lambda x: x["created_at"], reverse=True)
        return conversations

    def delete(self, conversation_id: str):
        path = self._get_path(conversation_id)
        if os.path.exists(path):
            os.remove(path)
