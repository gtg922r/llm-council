"""Unit tests for the blob store."""

import pytest
import tempfile
from pathlib import Path


class TestBlobStore:
    """Tests for the BlobStore class."""

    @pytest.fixture
    def temp_blob_dir(self, tmp_path):
        """Create a temporary blob directory for tests."""
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir(parents=True)
        return str(blob_dir)

    def test_save_text_returns_uuid(self, temp_blob_dir):
        """Test that save_text returns a UUID reference."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "Hello, World!"
        
        ref_id = store.save_text(content)
        
        assert ref_id is not None
        assert len(ref_id) > 0
        # Should be a valid UUID format
        import uuid
        uuid.UUID(ref_id)  # Raises if invalid

    def test_get_text_retrieves_content(self, temp_blob_dir):
        """Test that get_text retrieves the saved content."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "Hello, World! This is test content."
        
        ref_id = store.save_text(content)
        retrieved = store.get_text(ref_id)
        
        assert retrieved == content

    def test_save_and_get_large_content(self, temp_blob_dir):
        """Test handling of large content."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        # Create a large piece of content (about 100KB)
        content = "x" * 100000
        
        ref_id = store.save_text(content)
        retrieved = store.get_text(ref_id)
        
        assert retrieved == content
        assert len(retrieved) == 100000

    def test_get_text_not_found_returns_none(self, temp_blob_dir):
        """Test that get_text returns None for non-existent reference."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        
        result = store.get_text("non-existent-id")
        
        assert result is None

    def test_save_text_with_special_characters(self, temp_blob_dir):
        """Test saving text with special characters."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "def hello():\n    print('Hello, 世界! 🌍')\n"
        
        ref_id = store.save_text(content)
        retrieved = store.get_text(ref_id)
        
        assert retrieved == content

    def test_delete_removes_blob(self, temp_blob_dir):
        """Test that delete removes the blob file."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "Content to delete"
        
        ref_id = store.save_text(content)
        
        # Verify it exists
        assert store.get_text(ref_id) == content
        
        # Delete
        store.delete(ref_id)
        
        # Verify it's gone
        assert store.get_text(ref_id) is None

    def test_exists_returns_correct_status(self, temp_blob_dir):
        """Test the exists method."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        
        assert store.exists("non-existent") is False
        
        ref_id = store.save_text("Some content")
        assert store.exists(ref_id) is True

    def test_blob_creates_file_on_disk(self, temp_blob_dir):
        """Test that save_text creates an actual file."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "Test content"
        
        ref_id = store.save_text(content)
        
        # Check file exists on disk
        blob_path = Path(temp_blob_dir) / f"{ref_id}.txt"
        assert blob_path.exists()
        assert blob_path.read_text(encoding='utf-8') == content

    def test_content_hash_based_deduplication(self, temp_blob_dir):
        """Test that identical content gets the same reference (deduplication)."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        content = "Duplicate content"
        
        ref_id_1 = store.save_text(content, deduplicate=True)
        ref_id_2 = store.save_text(content, deduplicate=True)
        
        # Same content should produce same reference
        assert ref_id_1 == ref_id_2

    def test_different_content_gets_different_reference(self, temp_blob_dir):
        """Test that different content gets different references."""
        from backend.infrastructure.blob_store import LocalBlobStore
        
        store = LocalBlobStore(temp_blob_dir)
        
        ref_id_1 = store.save_text("Content A")
        ref_id_2 = store.save_text("Content B")
        
        assert ref_id_1 != ref_id_2
