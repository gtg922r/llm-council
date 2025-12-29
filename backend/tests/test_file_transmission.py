from backend.main import SendMessageRequest, FileContext


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
