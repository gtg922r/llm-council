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
