import pytest
import backend.main as main
from backend.main import SendMessageRequest, FileContext, build_prompt_content
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
    """Storage should persist files alongside user messages."""
    monkeypatch.setattr(storage, "DATA_DIR", str(tmp_path))
    storage.create_conversation("conv-1")
    files = [{"name": "notes.txt", "content": "example", "size": 7}]

    storage.add_user_message("conv-1", "hello", files=files)
    conversation = storage.get_conversation("conv-1")

    assert conversation["messages"][-1]["files"] == files


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

    assert "files" not in conversation["messages"][-1]


def test_build_prompt_content_requires_name_and_content():
    """Prompt builder should reject incomplete file dicts."""
    with pytest.raises(ValueError):
        build_prompt_content("hello", [{"name": "notes.txt"}])


@pytest.mark.asyncio
async def test_send_message_uses_prompt_builder(monkeypatch):
    """send_message should store raw content and send formatted prompt to models."""
    captured = {}

    def fake_get_conversation(_conversation_id):
        return {"messages": [{"role": "user", "content": "prior"}]}

    def fake_add_user_message(_conversation_id, content, files=None):
        captured["content"] = content
        captured["files"] = files

    def fake_add_assistant_message(_conversation_id, _stage1, _stage2, _stage3):
        return None

    async def fake_run_full_council(prompt_content):
        captured["prompt"] = prompt_content
        from backend.domain.models import CouncilRun, AssistantMetadata
        return CouncilRun(
            stage1_results=[],
            stage2_results=[],
            stage3_result={"response": "ok"},
            metadata=AssistantMetadata()
        )

    monkeypatch.setattr(main.storage, "get_conversation", fake_get_conversation)
    monkeypatch.setattr(main.storage, "add_user_message", fake_add_user_message)
    monkeypatch.setattr(main.storage, "add_assistant_message", fake_add_assistant_message)
    monkeypatch.setattr(main, "run_full_council", fake_run_full_council)

    request = SendMessageRequest(
        content="hello",
        files=[FileContext(name="notes.txt", content="example", size=7)],
    )

    response = await main.send_message("conv-1", request)

    assert captured["content"] == "hello"
    assert captured["files"] == [{"name": "notes.txt", "content": "example", "size": 7}]
    assert captured["prompt"] == build_prompt_content("hello", request.files)
    assert response["stage3"]["response"] == "ok"
