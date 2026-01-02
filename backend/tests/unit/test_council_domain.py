import pytest
from unittest.mock import patch, MagicMock
from backend.council import run_full_council
from backend.domain.models import CouncilRun

@pytest.mark.asyncio
async def test_run_full_council_returns_domain_model(monkeypatch):
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
    
    from backend.ports import LLMProvider
    class MockLLM(LLMProvider):
        def __init__(self):
            self.call_count = 0
        async def chat(self, model, messages, **kwargs):
            return mock_stage3
        async def stream_chat(self, model, messages, **kwargs):
            yield mock_stage3
        async def chat_parallel(self, models, messages, **kwargs):
            self.call_count += 1
            if self.call_count == 1:
                return mock_stage1
            return mock_stage2

    # Override COUNCIL_MODELS for this test
    monkeypatch.setattr("backend.council.COUNCIL_MODELS", ["model1", "model2"])
    
    llm = MockLLM()
    result = await run_full_council("What is 1+1?", llm_provider=llm)
    
    assert isinstance(result, CouncilRun)
    assert len(result.stage1_results) == 2
    assert len(result.stage2_results) == 2
    assert result.stage3_result["response"] == "Synthesized response"
    assert "Response A" in result.metadata.label_to_model
    assert len(result.metadata.aggregate_rankings) > 0
