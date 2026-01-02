import pytest
import os
from datetime import datetime, timezone
from backend.domain.models import Conversation
from backend.infrastructure.json_repository import JsonConversationRepository

def test_json_repo_save_get(tmp_path):
    repo = JsonConversationRepository(data_dir=str(tmp_path))
    
    conv = Conversation(
        id="test-1",
        created_at=datetime.now(timezone.utc),
        title="Test"
    )
    
    repo.save(conv)
    
    loaded = repo.get("test-1")
    assert loaded is not None
    assert loaded.id == "test-1"
    assert loaded.title == "Test"

def test_json_repo_list(tmp_path):
    repo = JsonConversationRepository(data_dir=str(tmp_path))
    
    conv1 = Conversation(id="1", created_at=datetime.now(timezone.utc), title="A")
    conv2 = Conversation(id="2", created_at=datetime.now(timezone.utc), title="B")
    
    repo.save(conv1)
    repo.save(conv2)
    
    listing = repo.list()
    assert len(listing) == 2
    titles = [c["title"] for c in listing]
    assert "A" in titles
    assert "B" in titles

def test_json_repo_delete(tmp_path):
    repo = JsonConversationRepository(data_dir=str(tmp_path))
    conv = Conversation(id="1", created_at=datetime.now(timezone.utc))
    repo.save(conv)
    
    assert repo.get("1") is not None
    repo.delete("1")
    assert repo.get("1") is None
