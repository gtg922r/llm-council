from typing import List, Dict, Any, Optional, AsyncGenerator
from ..ports import LLMProvider
from ..openrouter import query_model as or_query_model

class OpenRouterAdapter(LLMProvider):
    async def query(self, model: str, messages: List[Dict[str, str]], timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        return await or_query_model(model, messages, timeout)
    
    async def query_stream(self, model: str, messages: List[Dict[str, str]], timeout: float = 30.0) -> AsyncGenerator[str, None]:
        raise NotImplementedError("Streaming not yet implemented")
