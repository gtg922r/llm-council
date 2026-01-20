"""Tests for the CouncilOrchestrator service."""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from backend.application.council_service import (
    CouncilOrchestrator,
    StageStarted,
    StageCompleted,
    TitleGenerated,
    RunCompleted
)
from backend.domain.models import Conversation, UserMessage, AssistantMessage
from backend.ports import LLMProvider, ConversationRepository


def create_mock_llm(responses=None):
    """Create a mock LLM provider with configurable responses."""
    mock_llm = MagicMock(spec=LLMProvider)
    
    if responses is None:
        responses = {"content": "Mock response"}
    
    mock_llm.chat = AsyncMock(return_value=responses)
    return mock_llm


def create_mock_repo(conversation=None):
    """Create a mock repository with an optional conversation."""
    mock_repo = MagicMock(spec=ConversationRepository)
    
    if conversation is None:
        conversation = Conversation(id="test-1", created_at=datetime.now())
    
    mock_repo.get = MagicMock(return_value=conversation)
    mock_repo.save = MagicMock()
    return mock_repo


@pytest.mark.asyncio
async def test_orchestrator_yields_stage_events():
    """Test that orchestrator yields stage start and complete events."""
    mock_llm = create_mock_llm()
    mock_repo = create_mock_repo()
    
    with patch('backend.application.council_service.COUNCIL_MODELS', ['model1', 'model2']):
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm, 
            conversation_repo=mock_repo
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Hello"):
            events.append(event)
    
    # Should have events for all 3 stages plus completion
    assert len(events) >= 4
    
    event_types = [type(e).__name__ for e in events]
    assert "StageCompleted" in event_types
    assert "RunCompleted" in event_types


@pytest.mark.asyncio
async def test_orchestrator_generates_title_on_first_message():
    """Test that title is generated for first message."""
    mock_llm = create_mock_llm({"content": "Test Title"})
    mock_repo = create_mock_repo()
    
    with patch('backend.application.council_service.COUNCIL_MODELS', ['model1']):
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm, 
            conversation_repo=mock_repo
        )
        
        events = []
        async for event in orchestrator.run_council(
            "test-1", 
            "Hello", 
            is_first_message=True
        ):
            events.append(event)
    
    # Should have TitleGenerated event
    title_events = [e for e in events if isinstance(e, TitleGenerated)]
    assert len(title_events) == 1
    assert title_events[0].title == "Test Title"


@pytest.mark.asyncio
async def test_orchestrator_no_title_on_subsequent_message():
    """Test that title is not generated for subsequent messages."""
    mock_llm = create_mock_llm()
    mock_repo = create_mock_repo()
    
    with patch('backend.application.council_service.COUNCIL_MODELS', ['model1']):
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm, 
            conversation_repo=mock_repo
        )
        
        events = []
        async for event in orchestrator.run_council(
            "test-1", 
            "Hello", 
            is_first_message=False  # Not first message
        ):
            events.append(event)
    
    # Should NOT have TitleGenerated event
    title_events = [e for e in events if isinstance(e, TitleGenerated)]
    assert len(title_events) == 0


@pytest.mark.asyncio
async def test_orchestrator_handles_all_models_failed():
    """Test graceful handling when all models fail."""
    # Create mock that returns None (simulating failed LLM calls)
    mock_llm = MagicMock(spec=LLMProvider)
    mock_llm.chat = AsyncMock(return_value=None)  # All calls return None (failure)
    mock_repo = create_mock_repo()
    
    with patch('backend.application.council_service.COUNCIL_MODELS', ['model1', 'model2']):
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm, 
            conversation_repo=mock_repo
        )
        
        events = []
        async for event in orchestrator.run_council("test-1", "Hello"):
            events.append(event)
    
    # Should still complete with error message in stage 3
    stage3_events = [e for e in events if isinstance(e, StageCompleted) and e.stage == 3]
    assert len(stage3_events) == 1
    assert "error" in str(stage3_events[0].data).lower() or "failed" in str(stage3_events[0].data).lower()


@pytest.mark.asyncio
async def test_orchestrator_saves_to_repository():
    """Test that orchestrator saves progress to repository."""
    mock_llm = create_mock_llm()
    mock_repo = create_mock_repo()
    
    with patch('backend.application.council_service.COUNCIL_MODELS', ['model1']):
        orchestrator = CouncilOrchestrator(
            llm_provider=mock_llm, 
            conversation_repo=mock_repo
        )
        
        async for _ in orchestrator.run_council("test-1", "Hello"):
            pass
    
    # Repository save should have been called multiple times
    assert mock_repo.save.call_count >= 3  # At least once per stage


@pytest.mark.asyncio
async def test_chairman_followup_requires_previous_response():
    """Test that chairman followup requires a previous assistant message."""
    mock_llm = create_mock_llm()
    # Conversation with no previous assistant message
    conversation = Conversation(
        id="test-1",
        created_at=datetime.now(),
        messages=[UserMessage(content="First question")]
    )
    mock_repo = create_mock_repo(conversation)
    
    orchestrator = CouncilOrchestrator(
        llm_provider=mock_llm, 
        conversation_repo=mock_repo
    )
    
    result = await orchestrator.chairman_followup("test-1", "Follow up")
    
    assert "error" in result["response"].lower()


@pytest.mark.asyncio
async def test_chairman_followup_with_previous_response():
    """Test successful chairman followup."""
    mock_llm = create_mock_llm({"content": "Follow-up answer"})
    
    # Conversation with previous assistant message
    conversation = Conversation(
        id="test-1",
        created_at=datetime.now(),
        messages=[
            UserMessage(content="First question"),
            AssistantMessage(
                stage1=[],
                stage2=[],
                stage3={"model": "chairman", "response": "Initial answer"}
            )
        ]
    )
    mock_repo = create_mock_repo(conversation)
    
    orchestrator = CouncilOrchestrator(
        llm_provider=mock_llm, 
        conversation_repo=mock_repo
    )
    
    result = await orchestrator.chairman_followup("test-1", "Follow up question")
    
    assert result["response"] == "Follow-up answer"
    mock_llm.chat.assert_called_once()
