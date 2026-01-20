import pytest
from unittest.mock import MagicMock
from backend import storage, main
from datetime import datetime
from backend.domain.models import Conversation as ConversationModel, UserMessage as UserMessageModel
from backend.main import SendMessageRequest, FileContext
from backend.application.prompt_builder import build_prompt_content
from backend import storage


def test_send_message_request_accepts_files():
    """SendMessageRequest should accept structured file context."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example", size=7)],
    )

    assert request.files[0].name == "notes.txt"
    assert request.files[0].content == "example"
    assert request.files[0].size == 7


def test_file_context_size_optional():
    """FileContext size is optional."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example")],
    )

    assert request.files[0].size is None


def test_add_user_message_stores_files(tmp_path, monkeypatch):
    """Storage should persist files in BlobStore and store references in messages."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    blob_dir = tmp_path / "blobs"
    
    # We need to mock BlobStore to use our tmp path
    from backend.infrastructure.blob_store import BlobStore
    monkeypatch.setattr("backend.storage.BlobStore", lambda: BlobStore(blob_dir=str(blob_dir)))
    
    storage.create_conversation("conv-1")
    files = [{"name": "notes.txt", "content": "example", "size": 7}]

    storage.add_user_message("conv-1", "hello", files=files)
    conversation = storage.get_conversation("conv-1")

    attachments = conversation["messages"][-1]["files"]
    assert len(attachments) == 1
    assert attachments[0]["filename"] == "notes.txt"
    assert "file_reference_id" in attachments[0]
    
    # Verify content in blob store
    store = BlobStore(blob_dir=str(blob_dir))
    assert store.get_text(attachments[0]["file_reference_id"]) == "example"


def test_build_prompt_content_appends_files():
    """Prompt builder should append file blocks after the user message."""
    files = [
        FileContext(name="notes.txt", content="example", size=7),
        FileContext(name="todo.md", content="- item", size=6),
    ]

    prompt = build_prompt_content("hello", files)

    assert prompt == (
        "hello\n\n"
        "--- FILE: notes.txt ---\n"
        "example\n"
        "--- END FILE: notes.txt ---\n\n"
        "--- FILE: todo.md ---\n"
        "- item\n"
        "--- END FILE: todo.md ---"
    )


def test_build_prompt_content_accepts_dict_files():
    """Prompt builder should accept file dicts from storage."""
    files = [{"name": "notes.txt", "content": "example", "size": 7}]

    prompt = build_prompt_content("hello", files)

    assert prompt == (
        "hello\n\n"
        "--- FILE: notes.txt ---\n"
        "example\n"
        "--- END FILE: notes.txt ---"
    )


def test_add_user_message_omits_files_when_none(tmp_path, monkeypatch):
    """Storage should omit files when none are provided."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-1")

    storage.add_user_message("conv-1", "hello")
    conversation = storage.get_conversation("conv-1")

    assert conversation["messages"][-1]["files"] == []


def test_build_prompt_content_skips_invalid_files():
    """Prompt builder should skip incomplete file dicts."""
    # This used to raise ValueError, but now it skips
    prompt = build_prompt_content("hello", [{"not_a_name": "foo"}])
    assert prompt == "hello"


@pytest.mark.asyncio
async def test_send_message_uses_prompt_builder(monkeypatch):
    """send_message should store raw content and send formatted prompt to models."""
    captured = {}

    def fake_get_conversation(_conversation_id):
        return {"messages": [{"role": "user", "content": "prior"}]}

    def fake_add_user_message(_conversation_id, content, files=None):
        captured["content"] = content
        captured["files"] = files

    def fake_add_assistant_message(_conversation_id, _stage1, _stage2, _stage3, metadata=None):
        return None

    from backend.application.council_service import StageCompleted, RunCompleted
    async def fake_run_council(conversation_id, content, attachments=None, is_first_message=False, model_mode="smart"):
        captured["prompt_from_orchestrator"] = build_prompt_content(content, attachments, blob_store=mock_blob)
        yield StageCompleted(stage=3, data={"response": "ok"})
        yield RunCompleted()
    
    mock_repo = MagicMock()
    # Initial conversation has one message
    mock_repo.get.return_value = ConversationModel(id="conv-1", created_at=datetime.now(), messages=[UserMessageModel(content="prior")])
    
    monkeypatch.setattr(main, "conversation_repo", mock_repo)
    mock_blob = MagicMock()
    mock_blob.save_text.return_value = "ref123"
    mock_blob.get_text.return_value = "example"
    monkeypatch.setattr(main, "blob_store", mock_blob)
    # Important: patch the existing instance's attribute
    monkeypatch.setattr(main.orchestrator, "blob_store", mock_blob)
    monkeypatch.setattr(main.orchestrator, "run_council", fake_run_council)
    
    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example", size=7)],
    )

    response = await main.send_message("conv-1", request)

    # Verify repo.save was called with the new messages
    # Note: send_message now appends user message AND orchestrator saves assistant message
    # In our mock, orchestrator doesn't save to repo, but send_message saves user message.
    mock_repo.save.assert_called()
    
    # Check that orchestrator received correct content
    assert captured["prompt_from_orchestrator"] == build_prompt_content("hello", request.files, blob_store=mock_blob)
    assert response["stage3"]["response"] == "ok"
