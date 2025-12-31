"""Unit tests for CouncilService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.application.council_service import (
    CouncilService, parse_ranking_from_text, calculate_aggregate_rankings,
    create_assistant_message_from_council_run
)
from backend.domain.models import (
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking, CouncilRun
)
from backend.domain.events import (
    Stage1Started, Stage1Progress, Stage1Complete,
    Stage2Started, Stage2Progress, Stage2Complete,
    Stage3Started, Stage3Complete, CouncilComplete, CouncilError
)
from backend.ports import LLMProvider


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""
    
    def __init__(self, responses=None):
        """Initialize with optional predefined responses."""
        self.responses = responses or {}
        self.queries = []  # Track all queries
    
    async def query(self, model, messages, timeout=120.0):
        self.queries.append((model, messages))
        if model in self.responses:
            return self.responses[model]
        return {"content": f"Response from {model}"}
    
    async def query_parallel(self, models, messages):
        results = {}
        for model in models:
            results[model] = await self.query(model, messages)
        return results


class TestParseRankingFromText:
    """Tests for ranking text parsing."""

    def test_parse_standard_format(self):
        """Test parsing a properly formatted ranking."""
        text = """Response A is best...

FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
        
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_parse_without_numbers(self):
        """Test parsing ranking without numbered list."""
        text = """Evaluation...

FINAL RANKING:
Response B
Response A"""
        
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A"]


class TestCalculateAggregateRankings:
    """Tests for aggregate ranking calculation."""

    def test_calculate_aggregates(self):
        """Test calculating aggregate rankings."""
        stage2_results = [
            Stage2Ranking(model="m1", ranking="", parsed_ranking=["Response A", "Response B"], status="success"),
            Stage2Ranking(model="m2", ranking="", parsed_ranking=["Response B", "Response A"], status="success"),
        ]
        label_to_model = {"Response A": "modelA", "Response B": "modelB"}
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        assert len(result) == 2
        # Both should have average rank of 1.5
        assert all(r.average_rank == 1.5 for r in result)


class TestCouncilServiceEvents:
    """Tests for the CouncilService event-driven workflow."""

    @pytest.mark.asyncio
    async def test_run_council_yields_all_events(self):
        """Test that run_council yields all expected event types."""
        mock_provider = MockLLMProvider({
            "model1": {"content": "Response 1"},
            "model2": {"content": "Response 2"},
            "chairman": {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1", "model2"],
            chairman_model="chairman"
        )
        
        events = []
        async for event in service.run_council("What is 2+2?"):
            events.append(event)
        
        # Check we got all event types
        event_types = [e.type for e in events]
        
        assert "stage1_start" in event_types
        assert "stage1_progress" in event_types
        assert "stage1_complete" in event_types
        assert "stage2_start" in event_types
        assert "stage2_progress" in event_types
        assert "stage2_complete" in event_types
        assert "stage3_start" in event_types
        assert "stage3_complete" in event_types
        assert "complete" in event_types

    @pytest.mark.asyncio
    async def test_run_council_batch_returns_council_run(self):
        """Test that run_council_batch returns a complete CouncilRun."""
        mock_provider = MockLLMProvider({
            "model1": {"content": "Response 1"},
            "chairman": {"content": "Synthesis"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1"],
            chairman_model="chairman"
        )
        
        result = await service.run_council_batch("What is 2+2?")
        
        assert isinstance(result, CouncilRun)
        assert result.user_query == "What is 2+2?"
        assert len(result.stage1) == 1
        assert result.stage3 is not None
        assert result.metadata is not None

    @pytest.mark.asyncio
    async def test_stage1_complete_contains_results(self):
        """Test that Stage1Complete event contains all results."""
        mock_provider = MockLLMProvider({
            "model1": {"content": "Answer 1"},
            "model2": {"content": "Answer 2"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1", "model2"],
            chairman_model="chairman"
        )
        
        stage1_complete = None
        async for event in service.run_council("Test"):
            if isinstance(event, Stage1Complete):
                stage1_complete = event
                break
        
        assert stage1_complete is not None
        assert len(stage1_complete.data) == 2
        assert all(isinstance(r, Stage1Response) for r in stage1_complete.data)

    @pytest.mark.asyncio
    async def test_stage2_complete_contains_metadata(self):
        """Test that Stage2Complete event contains metadata."""
        mock_provider = MockLLMProvider({
            "model1": {"content": "Answer"},
            "chairman": {"content": "FINAL RANKING:\n1. Response A"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1"],
            chairman_model="chairman"
        )
        
        stage2_complete = None
        async for event in service.run_council("Test"):
            if isinstance(event, Stage2Complete):
                stage2_complete = event
                break
        
        assert stage2_complete is not None
        assert stage2_complete.metadata is not None
        assert "Response A" in stage2_complete.metadata.label_to_model

    @pytest.mark.asyncio
    async def test_handles_model_failure_gracefully(self):
        """Test that service handles model failures gracefully."""
        mock_provider = MockLLMProvider({
            "model1": {"content": "Answer"},
            "model2": None,  # Failure
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1", "model2"],
            chairman_model="chairman"
        )
        
        events = []
        async for event in service.run_council("Test"):
            events.append(event)
        
        stage1_complete = next(e for e in events if isinstance(e, Stage1Complete))
        
        # Should have both results
        assert len(stage1_complete.data) == 2
        
        # One success, one error
        statuses = [r.status for r in stage1_complete.data]
        assert "success" in statuses
        assert "error" in statuses

    @pytest.mark.asyncio
    async def test_all_failures_yields_error(self):
        """Test that all models failing yields an error event."""
        mock_provider = MockLLMProvider({
            "model1": None,
            "model2": None,
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1", "model2"],
            chairman_model="chairman"
        )
        
        events = []
        async for event in service.run_council("Test"):
            events.append(event)
        
        # Should have an error event
        error_events = [e for e in events if isinstance(e, CouncilError)]
        assert len(error_events) == 1
        assert "All models failed" in error_events[0].message


class TestCouncilServiceHelpers:
    """Tests for CouncilService helper methods."""

    @pytest.mark.asyncio
    async def test_generate_title(self):
        """Test title generation."""
        mock_provider = MockLLMProvider({
            "google/gemini-2.5-flash": {"content": "Math Question"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1"],
            chairman_model="chairman"
        )
        
        title = await service.generate_title("What is 2+2?")
        
        assert title == "Math Question"

    @pytest.mark.asyncio
    async def test_chairman_followup(self):
        """Test chairman followup response."""
        mock_provider = MockLLMProvider({
            "chairman": {"content": "Follow-up answer"},
        })
        
        service = CouncilService(
            llm_provider=mock_provider,
            council_models=["model1"],
            chairman_model="chairman"
        )
        
        result = await service.chairman_followup(
            original_query="What is 2+2?",
            stage1_results=[Stage1Response(model="m1", response="4", status="success")],
            stage2_results=[],
            stage3_response="The answer is 4.",
            followup_query="Are you sure?"
        )
        
        assert isinstance(result, Stage3Synthesis)
        assert result.response == "Follow-up answer"


class TestCreateAssistantMessage:
    """Tests for creating AssistantMessage from CouncilRun."""

    def test_create_assistant_message_from_council_run(self):
        """Test converting CouncilRun to AssistantMessage."""
        run = CouncilRun(
            user_query="Test",
            stage1=[Stage1Response(model="m1", response="r1", status="success")],
            stage2=[Stage2Ranking(model="m1", ranking="rank", parsed_ranking=["Response A"], status="success")],
            stage3=Stage3Synthesis(model="chairman", response="synthesis"),
            metadata=CouncilMetadata(
                label_to_model={"Response A": "m1"},
                aggregate_rankings=[]
            )
        )
        
        message = create_assistant_message_from_council_run(run)
        
        assert message.role == "assistant"
        assert len(message.stage1) == 1
        assert message.stage3.response == "synthesis"
        assert message.metadata.label_to_model["Response A"] == "m1"
