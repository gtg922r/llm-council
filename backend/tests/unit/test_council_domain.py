"""Tests for council domain logic (pure functions)."""

import pytest
from backend.domain.council_logic import parse_ranking_from_text, calculate_aggregate_rankings
from backend.domain.models import Stage2Result, AggregateRanking


class TestParseRankingFromText:
    """Tests for the parse_ranking_from_text function."""
    
    def test_parse_standard_format(self):
        """Test parsing standard FINAL RANKING format."""
        text = """Response A provides good detail...
Response B is accurate but lacks depth...

FINAL RANKING:
1. Response B
2. Response A
3. Response C"""
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]
    
    def test_parse_without_numbers(self):
        """Test parsing when ranking section lacks numbers."""
        text = """Evaluation...

FINAL RANKING:
Response C
Response A
Response B"""
        result = parse_ranking_from_text(text)
        assert result == ["Response C", "Response A", "Response B"]
    
    def test_parse_fallback_no_header(self):
        """Test fallback when FINAL RANKING header is missing."""
        text = """I think Response B is best, followed by Response A, then Response C."""
        result = parse_ranking_from_text(text)
        assert result == ["Response B", "Response A", "Response C"]
    
    def test_parse_empty_text(self):
        """Test parsing empty text."""
        result = parse_ranking_from_text("")
        assert result == []
    
    def test_parse_no_responses(self):
        """Test parsing text with no Response labels."""
        result = parse_ranking_from_text("No responses mentioned here.")
        assert result == []


class TestCalculateAggregateRankings:
    """Tests for the calculate_aggregate_rankings function."""
    
    def test_calculate_simple_case(self):
        """Test simple case with two models and two voters."""
        stage2_results = [
            Stage2Result(
                model="voter1",
                ranking="...",
                parsed_ranking=["Response A", "Response B"],
                status="success"
            ),
            Stage2Result(
                model="voter2",
                ranking="...",
                parsed_ranking=["Response B", "Response A"],
                status="success"
            ),
        ]
        label_to_model = {
            "Response A": "model_a",
            "Response B": "model_b"
        }
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        assert len(result) == 2
        # Both should have average rank 1.5 (1+2)/2
        for r in result:
            assert r.average_rank == 1.5
            assert r.rankings_count == 2
    
    def test_calculate_clear_winner(self):
        """Test case with a clear winner."""
        stage2_results = [
            Stage2Result(
                model="voter1",
                ranking="...",
                parsed_ranking=["Response A", "Response B"],
                status="success"
            ),
            Stage2Result(
                model="voter2",
                ranking="...",
                parsed_ranking=["Response A", "Response B"],
                status="success"
            ),
        ]
        label_to_model = {
            "Response A": "winner_model",
            "Response B": "loser_model"
        }
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        assert len(result) == 2
        assert result[0].model == "winner_model"
        assert result[0].average_rank == 1.0
        assert result[1].model == "loser_model"
        assert result[1].average_rank == 2.0
    
    def test_calculate_with_error_voter(self):
        """Test that error voters are handled gracefully."""
        stage2_results = [
            Stage2Result(
                model="voter1",
                ranking="...",
                parsed_ranking=["Response A", "Response B"],
                status="success"
            ),
            Stage2Result(
                model="voter2",
                ranking="Error",
                parsed_ranking=[],  # No rankings due to error
                status="error"
            ),
        ]
        label_to_model = {
            "Response A": "model_a",
            "Response B": "model_b"
        }
        
        result = calculate_aggregate_rankings(stage2_results, label_to_model)
        
        assert len(result) == 2
        # Only voter1's rankings counted
        assert result[0].rankings_count == 1
    
    def test_calculate_empty_results(self):
        """Test with no results."""
        result = calculate_aggregate_rankings([], {})
        assert result == []
