"""Unit tests for council.py with domain models."""

import pytest
from unittest.mock import AsyncMock, patch

from backend.domain.models import (
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking, CouncilRun
)


class TestParseRankingFromText:
    """Tests for parsing rankings from model text."""

    def test_parse_ranking_standard_format(self):
        """Test parsing a properly formatted ranking."""
        from backend.council import parse_ranking_from_text
        
        text = """Response A is the best because...
Response B has issues with...

FINAL RANKING:
1. Response A
2. Response B
3. Response C"""
        
        result = parse_ranking_from_text(text)
        assert result == ["Response A", "Response B", "Response C"]

    def test_parse_ranking_no_numbers(self):
        """Test parsing ranking without numbered list."""
        from backend.council import parse_ranking_from_text
        
        text = """Evaluation here...

FINAL RANKING:
Response B
Response A"""
        
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A"]

    def test_parse_ranking_fallback_without_header(self):
        """Test fallback parsing when FINAL RANKING header is missing."""
        from backend.council import parse_ranking_from_text
        
        text = "I rank Response C first, then Response A, and finally Response B."
        
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]


class TestCalculateAggregateRankings:
    """Tests for aggregate ranking calculation."""

    def test_calculate_aggregate_rankings(self):
        """Test calculating aggregate rankings from Stage2 results."""
        from backend.council import calculate_aggregate_rankings
        
        stage2_results = [
            {
                "model": "model1",
                "ranking": "FINAL RANKING:\n1. Response A\n2. Response B",
                "parsed_ranking": ["Response A", "Response B"],
                "status": "success"
            },
            {
                "model": "model2", 
                "ranking": "FINAL RANKING:\n1. Response B\n2. Response A",
                "parsed_ranking": ["Response B", "Response A"],
                "status": "success"
            }
        ]
        label_to_model = {
            "Response A": "openai/gpt-4o",
            "Response B": "anthropic/claude-3"
        }
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        # Both should have average rank of 1.5 (one first place, one second place)
        assert len(result) == 2
        for entry in result:
            assert entry["average_rank"] == 1.5
            assert entry["rankings_count"] == 2


class TestStage1CollectResponses:
    """Tests for Stage 1 response collection."""

    @pytest.mark.asyncio
    async def test_stage1_returns_domain_models(self):
        """Test that Stage 1 returns a list of Stage1Response models."""
        from backend.council import stage1_collect_responses_typed
        
        mock_response = {"content": "Test response"}
        
        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "model1": mock_response,
                "model2": mock_response
            }
            
            results = await stage1_collect_responses_typed("test query", ["model1", "model2"])
            
            assert len(results) == 2
            assert all(isinstance(r, Stage1Response) for r in results)
            assert all(r.status == "success" for r in results)

    @pytest.mark.asyncio
    async def test_stage1_handles_failures(self):
        """Test that Stage 1 handles model failures gracefully."""
        from backend.council import stage1_collect_responses_typed
        
        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_query:
            mock_query.return_value = {
                "model1": {"content": "Success"},
                "model2": None  # Failed
            }
            
            results = await stage1_collect_responses_typed("test query", ["model1", "model2"])
            
            assert len(results) == 2
            success_results = [r for r in results if r.status == "success"]
            error_results = [r for r in results if r.status == "error"]
            assert len(success_results) == 1
            assert len(error_results) == 1


class TestRunFullCouncilTyped:
    """Tests for the typed full council run."""

    @pytest.mark.asyncio
    async def test_run_full_council_returns_council_run(self):
        """Test that run_full_council_typed returns a CouncilRun model."""
        from backend.council import run_full_council_typed
        
        mock_stage1_response = {"content": "Model response"}
        mock_stage2_response = {"content": "FINAL RANKING:\n1. Response A"}
        mock_stage3_response = {"content": "Final synthesis"}
        
        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel, \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_single:
            
            # First call is Stage 1, second is Stage 2
            mock_parallel.side_effect = [
                {"model1": mock_stage1_response},  # Stage 1
                {"model1": mock_stage2_response},  # Stage 2
            ]
            mock_single.return_value = mock_stage3_response  # Stage 3
            
            result = await run_full_council_typed("test query", ["model1"], "chairman")
            
            assert isinstance(result, CouncilRun)
            assert result.user_query == "test query"
            assert len(result.stage1) == 1
            assert isinstance(result.stage1[0], Stage1Response)
            assert result.stage3 is not None
            assert isinstance(result.stage3, Stage3Synthesis)
            assert result.metadata is not None
            assert isinstance(result.metadata, CouncilMetadata)

    @pytest.mark.asyncio
    async def test_run_full_council_metadata_persists(self):
        """Test that metadata is included in CouncilRun and can be serialized."""
        from backend.council import run_full_council_typed
        
        mock_stage1_response = {"content": "Model response"}
        mock_stage2_response = {"content": "FINAL RANKING:\n1. Response A"}
        mock_stage3_response = {"content": "Final synthesis"}
        
        with patch("backend.council.query_models_parallel", new_callable=AsyncMock) as mock_parallel, \
             patch("backend.council.query_model", new_callable=AsyncMock) as mock_single:
            
            mock_parallel.side_effect = [
                {"openai/gpt-4o": mock_stage1_response},
                {"openai/gpt-4o": mock_stage2_response},
            ]
            mock_single.return_value = mock_stage3_response
            
            result = await run_full_council_typed("test query", ["openai/gpt-4o"], "chairman")
            
            # Verify metadata
            assert "Response A" in result.metadata.label_to_model
            assert result.metadata.label_to_model["Response A"] == "openai/gpt-4o"
            
            # Verify serialization preserves metadata
            serialized = result.model_dump()
            assert serialized["metadata"]["label_to_model"]["Response A"] == "openai/gpt-4o"
