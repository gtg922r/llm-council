"""Port interfaces for the LLM Council application.

This module defines abstract interfaces (ports) that the application layer
depends on. These interfaces are implemented by adapters in the infrastructure
layer, enabling dependency injection and testability.

The Hexagonal Architecture pattern allows us to:
1. Test business logic without real infrastructure
2. Swap implementations (e.g., JSON files → database)
3. Keep business logic clean and infrastructure-agnostic
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, AsyncIterator

from .domain.models import Conversation, UserMessage, AssistantMessage


class ConversationRepository(ABC):
    """Abstract interface for conversation persistence.
    
    Implementations handle the actual storage mechanism (JSON files, database, etc.)
    while the application layer remains storage-agnostic.
    """
    
    @abstractmethod
    def create(self, conversation_id: str) -> Conversation:
        """Create a new conversation.
        
        Args:
            conversation_id: Unique identifier for the conversation.
        
        Returns:
            The newly created Conversation.
        """
        pass
    
    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]:
        """Retrieve a conversation by ID.
        
        Args:
            conversation_id: The conversation identifier.
        
        Returns:
            The Conversation, or None if not found.
        """
        pass
    
    @abstractmethod
    def save(self, conversation: Conversation) -> None:
        """Save a conversation.
        
        Args:
            conversation: The Conversation to persist.
        """
        pass
    
    @abstractmethod
    def delete(self, conversation_id: str) -> None:
        """Delete a conversation.
        
        Args:
            conversation_id: The conversation identifier.
        """
        pass
    
    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """List all conversations (metadata only).
        
        Returns:
            List of conversation metadata dictionaries.
        """
        pass
    
    @abstractmethod
    def add_message(
        self,
        conversation_id: str,
        message: UserMessage | AssistantMessage
    ) -> None:
        """Add a message to a conversation.
        
        Args:
            conversation_id: The conversation identifier.
            message: The message to add.
        """
        pass
    
    @abstractmethod
    def update_title(self, conversation_id: str, title: str) -> None:
        """Update the conversation title.
        
        Args:
            conversation_id: The conversation identifier.
            title: The new title.
        """
        pass


class LLMProvider(ABC):
    """Abstract interface for LLM API interactions.
    
    Implementations handle the actual API calls (OpenRouter, OpenAI, etc.)
    while the application layer remains provider-agnostic.
    """
    
    @abstractmethod
    async def query(
        self,
        model: str,
        messages: List[Dict[str, str]],
        timeout: float = 120.0
    ) -> Optional[Dict[str, Any]]:
        """Query a single model.
        
        Args:
            model: The model identifier.
            messages: List of message dicts with 'role' and 'content'.
            timeout: Request timeout in seconds.
        
        Returns:
            Response dict with 'content' and optional 'reasoning_details',
            or None if the query failed.
        """
        pass
    
    @abstractmethod
    async def query_parallel(
        self,
        models: List[str],
        messages: List[Dict[str, str]]
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """Query multiple models in parallel.
        
        Args:
            models: List of model identifiers.
            messages: List of message dicts to send to each model.
        
        Returns:
            Dict mapping model identifier to response dict (or None if failed).
        """
        pass


class BlobStore(ABC):
    """Abstract interface for blob storage.
    
    Implementations handle the actual storage mechanism (local files, cloud, etc.)
    for large content that should be stored separately from conversation JSON.
    """
    
    @abstractmethod
    def save_text(self, content: str, deduplicate: bool = False) -> str:
        """Save text content and return a reference ID.
        
        Args:
            content: The text content to save.
            deduplicate: If True, use content hash for deduplication.
        
        Returns:
            A unique reference ID.
        """
        pass
    
    @abstractmethod
    def get_text(self, reference_id: str) -> Optional[str]:
        """Retrieve text content by reference ID.
        
        Args:
            reference_id: The reference ID.
        
        Returns:
            The text content, or None if not found.
        """
        pass
    
    @abstractmethod
    def delete(self, reference_id: str) -> bool:
        """Delete a blob.
        
        Args:
            reference_id: The reference ID.
        
        Returns:
            True if deleted, False if not found.
        """
        pass
    
    @abstractmethod
    def exists(self, reference_id: str) -> bool:
        """Check if a blob exists.
        
        Args:
            reference_id: The reference ID.
        
        Returns:
            True if exists.
        """
        pass
