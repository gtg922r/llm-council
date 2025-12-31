"""Tests for file transmission functionality.

Updated to work with the new hexagonal architecture.
"""

import pytest
from backend.main import SendMessageRequest, FileContextRequest
from backend.domain.models import FileContext, FileReference
from backend.application.council_service import build_prompt_content
from backend.infrastructure.blob_store import BlobStore


def test_send_message_request_accepts_files():
    """SendMessageRequest should accept structured file context."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContextRequest(name="notes.txt", content="example", size=7)],
    )

    assert request.files[0].name == "notes.txt"
    assert request.files[0].content == "example"
    assert request.files[0].size == 7


def test_file_context_size_optional():
    """FileContext size is optional."""
    request = SendMessageRequest(
        content="hello",
        files=[FileContextRequest(name="notes.txt", content="example")],
    )

    assert request.files[0].size is None


def test_build_prompt_content_with_blob_store(tmp_path):
    """Prompt builder should append file content from blob store."""
    blob_store = BlobStore(blob_dir=str(tmp_path))
    
    # Store files in blob store
    blob_id1 = blob_store.save_text("example")
    blob_id2 = blob_store.save_text("- item")
    
    files = [
        FileReference(name="notes.txt", blob_id=blob_id1, size=7),
        FileReference(name="todo.md", blob_id=blob_id2, size=6),
    ]

    prompt = build_prompt_content("hello", files, blob_store)

    assert prompt == (
        "hello\n\n"
        "--- FILE: notes.txt ---\n"
        "example\n"
        "--- END FILE: notes.txt ---\n\n"
        "--- FILE: todo.md ---\n"
        "- item\n"
        "--- END FILE: todo.md ---"
    )


def test_build_prompt_content_no_files():
    """Prompt builder should return original content if no files."""
    prompt = build_prompt_content("hello", [], None)
    assert prompt == "hello"


def test_build_prompt_content_no_blob_store():
    """Prompt builder should return original content if no blob store."""
    files = [FileReference(name="notes.txt", blob_id="abc", size=7)]
    prompt = build_prompt_content("hello", files, None)
    assert prompt == "hello"


def test_blob_store_integration(tmp_path):
    """Test the blob store saves and retrieves content correctly."""
    blob_store = BlobStore(blob_dir=str(tmp_path))
    
    content = "Test file content"
    blob_id = blob_store.save_text(content)
    
    retrieved = blob_store.get_text(blob_id)
    assert retrieved == content
