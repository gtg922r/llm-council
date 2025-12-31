from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncGenerator
from .domain.models import Conversation

class ConversationRepository(ABC):
    """Port for conversation persistence."""
    
    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        pass
        
    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        """Save a conversation."""
        pass
        
    @abstractmethod
    def list(self) -> List[Dict[str, Any]]:
        """List all conversations (metadata only)."""
        pass
        
    @abstractmethod
    def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
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
