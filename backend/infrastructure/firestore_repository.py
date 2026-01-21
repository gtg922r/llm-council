"""Firestore-based conversation repository."""

from datetime import datetime
from typing import List, Optional

from firebase_admin import firestore
from google.cloud.firestore_v1 import FieldFilter

from ..ports import ConversationRepository
from ..domain.models import Conversation, UserMessage, AssistantMessage
from .firebase_auth import get_firebase_app


class FirestoreConversationRepository(ConversationRepository):
    """Firestore implementation of ConversationRepository.
    
    Data structure:
        users/{user_id}/conversations/{conversation_id}
    """
    
    def __init__(self):
        # Ensure Firebase is initialized
        get_firebase_app()
        self._db = firestore.client()
    
    def _get_user_conversations_ref(self, user_id: str):
        """Get reference to user's conversations collection."""
        return self._db.collection('users').document(user_id).collection('conversations')
    
    def _conversation_to_dict(self, conversation: Conversation) -> dict:
        """Convert Conversation model to Firestore document."""
        return {
            'id': conversation.id,
            'created_at': conversation.created_at,
            'title': conversation.title,
            'is_pinned': conversation.is_pinned,
            'is_archived': conversation.is_archived,
            'has_unread': conversation.has_unread,
            'messages': [self._message_to_dict(m) for m in conversation.messages]
        }
    
    def _message_to_dict(self, message) -> dict:
        """Convert message to dict for Firestore."""
        if isinstance(message, UserMessage):
            return {
                'role': 'user',
                'content': message.content,
                'files': [f.model_dump() for f in message.files] if message.files else []
            }
        elif isinstance(message, AssistantMessage):
            return {
                'role': 'assistant',
                'stage1': message.stage1,
                'stage2': message.stage2,
                'stage3': message.stage3,
                'metadata': message.metadata.model_dump() if message.metadata else None
            }
        else:
            # Fallback for dict messages
            return dict(message) if hasattr(message, '__iter__') else {'data': str(message)}
    
    def _dict_to_conversation(self, doc_dict: dict) -> Conversation:
        """Convert Firestore document to Conversation model."""
        messages = []
        for msg_dict in doc_dict.get('messages', []):
            if msg_dict.get('role') == 'user':
                messages.append(UserMessage(
                    content=msg_dict.get('content', ''),
                    files=msg_dict.get('files', [])
                ))
            elif msg_dict.get('role') == 'assistant':
                messages.append(AssistantMessage(
                    stage1=msg_dict.get('stage1'),
                    stage2=msg_dict.get('stage2'),
                    stage3=msg_dict.get('stage3'),
                    metadata=msg_dict.get('metadata')
                ))
        
        created_at = doc_dict.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at)
        
        return Conversation(
            id=doc_dict['id'],
            created_at=created_at,
            title=doc_dict.get('title', 'New Conversation'),
            is_pinned=doc_dict.get('is_pinned', False),
            is_archived=doc_dict.get('is_archived', False),
            has_unread=doc_dict.get('has_unread', False),
            messages=messages
        )
    
    def list(self, user_id: str) -> List[dict]:
        """List all conversations for a user (metadata only)."""
        conversations_ref = self._get_user_conversations_ref(user_id)
        docs = conversations_ref.order_by('created_at', direction=firestore.Query.DESCENDING).stream()
        
        result = []
        for doc in docs:
            data = doc.to_dict()
            created_at = data.get('created_at')
            if hasattr(created_at, 'isoformat'):
                created_at = created_at.isoformat()
            
            result.append({
                'id': data['id'],
                'created_at': created_at,
                'title': data.get('title', 'New Conversation'),
                'is_pinned': data.get('is_pinned', False),
                'is_archived': data.get('is_archived', False),
                'has_unread': data.get('has_unread', False),
                'message_count': len(data.get('messages', []))
            })
        
        return result
    
    def get(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Get a specific conversation by ID."""
        doc_ref = self._get_user_conversations_ref(user_id).document(conversation_id)
        doc = doc_ref.get()
        
        if not doc.exists:
            return None
        
        return self._dict_to_conversation(doc.to_dict())
    
    def save(self, conversation: Conversation, user_id: str) -> None:
        """Save (create or update) a conversation."""
        doc_ref = self._get_user_conversations_ref(user_id).document(conversation.id)
        doc_ref.set(self._conversation_to_dict(conversation))
    
    def delete(self, conversation_id: str, user_id: str) -> None:
        """Delete a conversation."""
        doc_ref = self._get_user_conversations_ref(user_id).document(conversation_id)
        doc_ref.delete()
