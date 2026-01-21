from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from .domain.models import Conversation

class ConversationRepository(ABC):
    """Port for conversation persistence.
    
    All methods require a user_id parameter for multi-tenant data isolation.
    """
    
    @abstractmethod
    def get(self, conversation_id: str, user_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID for a specific user."""
        pass
        
    @abstractmethod
    def save(self, conversation: Conversation, user_id: str) -> None:
        """Save a conversation for a specific user."""
        pass
        
    @abstractmethod
    def list(self, user_id: str) -> List[Dict[str, Any]]:
        """List all conversations for a specific user (metadata only)."""
        pass
        
    @abstractmethod
    def delete(self, conversation_id: str, user_id: str) -> None:
        """Delete a conversation for a specific user."""
        pass

class LLMProvider(ABC):
    """Port for LLM interaction."""
    
    @abstractmethod
    async def chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> Optional[Dict[str, Any]]:
        """Send a chat completion request."""
        pass
        
    @abstractmethod
    async def stream_chat(self, model: str, messages: List[Dict[str, Any]], **kwargs) -> AsyncGenerator[Dict[str, Any], None]:
        """Send a streaming chat completion request."""
        # Note: Added yield to make it a generator for type checking if needed, 
        # but abstractmethod is enough.
        yield {}
