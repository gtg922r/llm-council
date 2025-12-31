import pytest
from unittest.mock import patch, MagicMock
from backend.council import run_full_council
from backend.domain.models import CouncilRun

@pytest.mark.asyncio
async def test_run_full_council_returns_domain_model():
    # Mock stage 1 responses
    mock_stage1 = {
        "model1": {"content": "Response 1"},
        "model2": {"content": "Response 2"}
    }
    
    # Mock stage 2 rankings
    mock_stage2 = {
        "model1": {"content": "FINAL RANKING:\n1. Response B\n2. Response A"},
        "model2": {"content": "FINAL RANKING:\n1. Response B\n2. Response A"}
    }
    
    # Mock stage 3 synthesis
    mock_stage3 = {"content": "Synthesized response"}
    
    with patch("backend.council.query_models_parallel") as mock_parallel:
        with patch("backend.council.query_model") as mock_single:
            # First call for stage 1, second for stage 2
            mock_parallel.side_effect = [mock_stage1, mock_stage2]
            mock_single.return_value = mock_stage3
            
            result = await run_full_council("What is 1+1?")
            
            assert isinstance(result, CouncilRun)
            assert len(result.stage1_results) == 2
            assert len(result.stage2_results) == 2
            assert result.stage3_result["response"] == "Synthesized response"
            assert "Response A" in result.metadata.label_to_model
            assert len(result.metadata.aggregate_rankings) > 0
