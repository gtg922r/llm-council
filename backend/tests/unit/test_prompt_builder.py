"""Unit tests for prompt builder with blob store integration."""

import pytest
from unittest.mock import MagicMock

from backend.domain.models import FileAttachment


class TestBuildPromptContent:
    """Tests for the build_prompt_content function with blob store support."""

    def test_build_prompt_without_files(self):
        """Test building prompt with just content."""
        from backend.application.prompt_builder import build_prompt_content
        
        result = build_prompt_content("What is 2+2?", None, None)
        
        assert result == "What is 2+2?"

    def test_build_prompt_with_inline_files(self):
        """Test building prompt with inline file attachments."""
        from backend.application.prompt_builder import build_prompt_content
        
        files = [
            FileAttachment(name="main.py", content="print('hello')", size=16)
        ]
        
        result = build_prompt_content("Analyze this code", files, None)
        
        assert "Analyze this code" in result
        assert "--- FILE: main.py ---" in result
        assert "print('hello')" in result
        assert "--- END FILE: main.py ---" in result

    def test_build_prompt_with_blob_reference(self):
        """Test building prompt with blob reference files."""
        from backend.application.prompt_builder import build_prompt_content
        from backend.infrastructure.blob_store import LocalBlobStore
        
        # Create a mock blob store
        mock_store = MagicMock(spec=LocalBlobStore)
        mock_store.get_text.return_value = "def hello():\n    print('world')"
        
        files = [
            FileAttachment(name="hello.py", size=100, blob_reference_id="blob-123")
        ]
        
        result = build_prompt_content("Analyze this code", files, mock_store)
        
        # Verify blob store was called
        mock_store.get_text.assert_called_once_with("blob-123")
        
        # Verify content was included
        assert "--- FILE: hello.py ---" in result
        assert "def hello():" in result
        assert "print('world')" in result

    def test_build_prompt_with_mixed_files(self):
        """Test building prompt with both inline and blob reference files."""
        from backend.application.prompt_builder import build_prompt_content
        from backend.infrastructure.blob_store import LocalBlobStore
        
        mock_store = MagicMock(spec=LocalBlobStore)
        mock_store.get_text.return_value = "blob content here"
        
        files = [
            FileAttachment(name="inline.py", content="inline content", size=14),
            FileAttachment(name="blob.py", size=100, blob_reference_id="blob-456"),
        ]
        
        result = build_prompt_content("Analyze these files", files, mock_store)
        
        assert "--- FILE: inline.py ---" in result
        assert "inline content" in result
        assert "--- FILE: blob.py ---" in result
        assert "blob content here" in result

    def test_build_prompt_handles_missing_blob(self):
        """Test that missing blob content is handled gracefully."""
        from backend.application.prompt_builder import build_prompt_content
        from backend.infrastructure.blob_store import LocalBlobStore
        
        mock_store = MagicMock(spec=LocalBlobStore)
        mock_store.get_text.return_value = None  # Blob not found
        
        files = [
            FileAttachment(name="missing.py", size=100, blob_reference_id="non-existent")
        ]
        
        result = build_prompt_content("Analyze this", files, mock_store)
        
        assert "--- FILE: missing.py ---" in result
        assert "[Content unavailable - blob not found]" in result

    def test_build_prompt_with_dict_files(self):
        """Test backward compatibility with dict-based file attachments."""
        from backend.application.prompt_builder import build_prompt_content
        
        files = [
            {"name": "test.py", "content": "test content", "size": 12}
        ]
        
        result = build_prompt_content("Analyze this", files, None)
        
        assert "--- FILE: test.py ---" in result
        assert "test content" in result


class TestResolveFileContent:
    """Tests for resolving file content from various sources."""

    def test_resolve_inline_content(self):
        """Test resolving content from inline FileAttachment."""
        from backend.application.prompt_builder import resolve_file_content
        
        attachment = FileAttachment(name="test.py", content="inline data", size=11)
        
        result = resolve_file_content(attachment, None)
        
        assert result == "inline data"

    def test_resolve_blob_content(self):
        """Test resolving content from blob store."""
        from backend.application.prompt_builder import resolve_file_content
        from backend.infrastructure.blob_store import LocalBlobStore
        
        mock_store = MagicMock(spec=LocalBlobStore)
        mock_store.get_text.return_value = "blob data"
        
        attachment = FileAttachment(name="test.py", size=9, blob_reference_id="ref-123")
        
        result = resolve_file_content(attachment, mock_store)
        
        assert result == "blob data"
        mock_store.get_text.assert_called_once_with("ref-123")

    def test_resolve_blob_without_store_raises(self):
        """Test that resolving blob without store returns error message."""
        from backend.application.prompt_builder import resolve_file_content
        
        attachment = FileAttachment(name="test.py", size=9, blob_reference_id="ref-123")
        
        result = resolve_file_content(attachment, None)
        
        assert result == "[Content unavailable - no blob store provided]"
