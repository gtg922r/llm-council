"""Unit tests for the CouncilService."""

import pytest
from unittest.mock import AsyncMock, MagicMock

from backend.application.council_service import (
    CouncilService,
    parse_ranking_from_text,
    calculate_aggregate_rankings,
)
from backend.domain.models import (
    Stage1Result,
    Stage2Result,
    AggregateRanking,
)


class TestParseRankingFromText:
    """Tests for parse_ranking_from_text function."""
    
    def test_parse_standard_format(self):
        """Test parsing standard FINAL RANKING format."""
        text = """Response A is great because...
Response B has issues with...

FINAL RANKING:
1. Response A
2. Response C
3. Response B"""
        
        result = parse_ranking_from_text(text)
        
        assert result == ["Response A", "Response C", "Response B"]
    
    def test_parse_with_extra_text(self):
        """Test parsing with extra explanatory text."""
        text = """Here's my evaluation...

FINAL RANKING:
1. Response B - best overall
2. Response A - good but...
3. Response C - needs work"""
        
        result = parse_ranking_from_text(text)
        
        assert result == ["Response B", "Response A", "Response C"]
    
    def test_parse_fallback_no_header(self):
        """Test fallback when no FINAL RANKING header."""
        text = "Response B is best, then Response A, finally Response C"
        
        result = parse_ranking_from_text(text)
        
        assert result == ["Response B", "Response A", "Response C"]
    
    def test_parse_empty_text(self):
        """Test parsing empty text."""
        result = parse_ranking_from_text("")
        assert result == []


class TestCalculateAggregateRankings:
    """Tests for calculate_aggregate_rankings function."""
    
    def test_aggregate_rankings(self):
        """Test calculating aggregate rankings from multiple evaluations."""
        stage2_results = [
            Stage2Result(
                model="model1",
                ranking="FINAL RANKING:\n1. Response A\n2. Response B",
                parsed_ranking=["Response A", "Response B"],
                status="success"
            ),
            Stage2Result(
                model="model2",
                ranking="FINAL RANKING:\n1. Response B\n2. Response A",
                parsed_ranking=["Response B", "Response A"],
                status="success"
            ),
        ]
        
        label_to_model = {
            "Response A": "openai/gpt-4",
            "Response B": "anthropic/claude-3"
        }
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        # Both should have average rank of 1.5 (each got 1st and 2nd once)
        assert len(result) == 2
        for agg in result:
            assert agg.average_rank == 1.5
            assert agg.rankings_count == 2
    
    def test_aggregate_with_error_rankings(self):
        """Test aggregate ignores error rankings."""
        stage2_results = [
            Stage2Result(
                model="model1",
                ranking="FINAL RANKING:\n1. Response A",
                parsed_ranking=["Response A"],
                status="success"
            ),
            Stage2Result(
                model="model2",
                ranking="Error: failed",
                parsed_ranking=[],
                status="error"
            ),
        ]
        
        label_to_model = {"Response A": "openai/gpt-4"}
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        assert len(result) == 1
        assert result[0].model == "openai/gpt-4"
        assert result[0].rankings_count == 1


class TestCouncilService:
    """Tests for the CouncilService class."""
    
    @pytest.fixture
    def mock_llm_provider(self):
        """Create a mock LLM provider."""
        provider = MagicMock()
        provider.chat = AsyncMock(return_value={"content": "Mock response"})
        provider.chat_parallel = AsyncMock(return_value={
            "model1": {"content": "Response 1"},
            "model2": {"content": "Response 2"},
        })
        return provider
    
    @pytest.fixture
    def council_service(self, mock_llm_provider):
        """Create a CouncilService with mock provider."""
        return CouncilService(
            llm_provider=mock_llm_provider,
            council_models=["model1", "model2"],
            chairman_model="chairman"
        )
    
    @pytest.mark.asyncio
    async def test_run_council_yields_events(self, council_service, mock_llm_provider):
        """Test that run_council yields appropriate events."""
        # Setup mock responses
        mock_llm_provider.chat = AsyncMock(side_effect=[
            {"content": "Model 1 response"},  # Stage 1 - model1
            {"content": "Model 2 response"},  # Stage 1 - model2
            {"content": "FINAL RANKING:\n1. Response A\n2. Response B"},  # Stage 2 - model1
            {"content": "FINAL RANKING:\n1. Response B\n2. Response A"},  # Stage 2 - model2
            {"content": "Chairman synthesis"},  # Stage 3
        ])
        
        events = []
        async for event in council_service.run_council("Test question"):
            events.append(event)
        
        # Verify we got expected event types
        event_types = [e.type for e in events]
        assert "stage1_start" in event_types
        assert "stage1_complete" in event_types
        assert "stage2_start" in event_types
        assert "stage2_complete" in event_types
        assert "stage3_start" in event_types
        assert "stage3_complete" in event_types
        assert "complete" in event_types
    
    @pytest.mark.asyncio
    async def test_run_followup(self, council_service, mock_llm_provider):
        """Test chairman follow-up response."""
        mock_llm_provider.chat = AsyncMock(return_value={"content": "Follow-up answer"})
        
        result = await council_service.run_followup(
            original_query="Original question",
            stage1_results=[Stage1Result(model="m1", response="Answer", status="success")],
            stage2_results=[Stage2Result(model="m1", ranking="Ranking", parsed_ranking=[], status="success")],
            stage3_response="Initial chairman response",
            followup_query="Follow-up question"
        )
        
        assert result.response == "Follow-up answer"
        assert result.model == "chairman"
