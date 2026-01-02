import pytest
from unittest.mock import MagicMock, AsyncMock
from backend.application.council_service import CouncilOrchestrator
from backend.domain.models import Conversation, UserMessage
from backend.ports import LLMProvider, ConversationRepository
from datetime import datetime

@pytest.mark.asyncio
async def test_orchestrator_yields_events():
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.chat_parallel = AsyncMock(return_value={})
    mock_llm.chat = AsyncMock(return_value={"content": "result"})
    
    mock_repo = MagicMock(spec=ConversationRepository)
    mock_repo.get = MagicMock(return_value=Conversation(id="1", created_at=datetime.now()))
    
    orchestrator = CouncilOrchestrator(llm_provider=mock_llm, conversation_repo=mock_repo)
    
    events = []
    async for event in orchestrator.run_council("1", "Hello"):
        events.append(event)
        
    assert len(events) > 0
    # Check for basic event types
    event_types = [type(e).__name__ for e in events]
    assert "StageStarted" in event_types
    assert "StageCompleted" in event_types
