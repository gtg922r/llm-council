from backend.main import SendMessageRequest, FileContext
from pydantic import ValidationError
import pytest

def test_file_context_model():
    """Test that FileContext model correctly validates data."""
    file = FileContext(name="test.txt", content="hello world", size=11)
    assert file.name == "test.txt"
    assert file.content == "hello world"
    assert file.size == 11

def test_file_context_optional_size():
    """Test that size is optional in FileContext."""
    file = FileContext(name="test.txt", content="hello world")
    assert file.name == "test.txt"
    assert file.size is None

def test_send_message_request_with_files():
    """Test that SendMessageRequest accepts a list of FileContext objects."""
    files = [
        FileContext(name="f1.txt", content="c1"),
        FileContext(name="f2.py", content="c2", size=100)
    ]
    request = SendMessageRequest(content="my prompt", files=files)
    assert request.content == "my prompt"
    assert len(request.files) == 2
    assert request.files[0].name == "f1.txt"

def test_send_message_request_optional_files():
    """Test that files is optional in SendMessageRequest."""
    request = SendMessageRequest(content="my prompt")
    assert request.content == "my prompt"
    assert request.files is None or request.files == []
