"""Port interfaces (abstract contracts) for the application layer.

These interfaces define the contracts that infrastructure adapters must implement.
This enables dependency injection and testability.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator
from .domain.models import (
    Conversation,
    ConversationMetadata,
    Message,
)


class ConversationRepository(ABC):
    """Abstract interface for conversation persistence."""
    
    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID."""
        pass
    
    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        """Persist a conversation."""
        pass
    
    @abstractmethod
    def list(self) -> List[ConversationMetadata]:
        """List all conversations (metadata only)."""
        pass
    
    @abstractmethod
    def delete(self, conversation_id: str) -> None:
        """Delete a conversation."""
        pass


class BlobStorePort(ABC):
    """Abstract interface for blob (file content) storage."""
    
    @abstractmethod
    def save_text(self, content: str) -> str:
        """Save text content and return a reference ID."""
        pass
    
    @abstractmethod
    def get_text(self, reference_id: str) -> Optional[str]:
        """Retrieve text content by reference ID."""
        pass
    
    @abstractmethod
    def delete(self, reference_id: str) -> None:
        """Delete a blob by reference ID."""
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM API interactions."""
    
    @abstractmethod
    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Send a chat request to an LLM model.
        
        Args:
            model: Model identifier
            messages: List of message dicts with 'role' and 'content'
            timeout: Request timeout in seconds
            
        Returns:
            Response dict with 'content' and optional 'reasoning_details',
            or None if the request failed.
        """
        pass
    
    @abstractmethod
    async def chat_parallel(
        self,
        models: List[str],
        messages: List[Dict[str, str]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Send chat requests to multiple models in parallel.
        
        Args:
            models: List of model identifiers
            messages: List of message dicts to send to each model
            
        Returns:
            Dict mapping model identifier to response dict (or None if failed)
        """
        pass
