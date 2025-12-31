import pytest
from backend.ports import ConversationRepository, LLMProvider

def test_cannot_instantiate_abstract_repository():
    with pytest.raises(TypeError):
        ConversationRepository()

def test_cannot_instantiate_abstract_llm():
    with pytest.raises(TypeError):
        LLMProvider()
