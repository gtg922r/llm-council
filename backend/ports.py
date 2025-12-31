from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, AsyncGenerator
from .domain.models import Conversation, Message, UserMessage, AssistantMessage

class ConversationRepository(ABC):
    @abstractmethod
    def create(self, conversation_id: str) -> Conversation:
        pass

    @abstractmethod
    def get(self, conversation_id: str) -> Optional[Conversation]:
        pass

    @abstractmethod
    def save(self, conversation: Conversation):
        pass

    @abstractmethod
    def list_metadata(self) -> List[Dict[str, Any]]:
        pass

    @abstractmethod
    def delete(self, conversation_id: str):
        pass

class LLMProvider(ABC):
    @abstractmethod
    async def query(self, model: str, messages: List[Dict[str, str]], timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        pass
    
    @abstractmethod
    async def query_stream(self, model: str, messages: List[Dict[str, str]], timeout: float = 30.0) -> AsyncGenerator[str, None]:
        pass
