"""Unit tests for the BlobStore."""

import os
import tempfile
import pytest

from backend.infrastructure.blob_store import BlobStore


class TestBlobStore:
    """Tests for the BlobStore class."""
    
    @pytest.fixture
    def temp_blob_dir(self, tmp_path):
        """Create a temporary blob directory."""
        blob_dir = tmp_path / "blobs"
        blob_dir.mkdir()
        return str(blob_dir)
    
    @pytest.fixture
    def blob_store(self, temp_blob_dir):
        """Create a BlobStore with temp directory."""
        return BlobStore(blob_dir=temp_blob_dir)
    
    def test_save_and_get_text(self, blob_store):
        """Test saving and retrieving text content."""
        content = "Hello, World!"
        
        blob_id = blob_store.save_text(content)
        
        assert blob_id is not None
        assert len(blob_id) == 64  # SHA-256 hex digest
        
        retrieved = blob_store.get_text(blob_id)
        assert retrieved == content
    
    def test_content_addressable_deduplication(self, blob_store, temp_blob_dir):
        """Test that identical content produces same blob ID."""
        content = "Duplicate content"
        
        id1 = blob_store.save_text(content)
        id2 = blob_store.save_text(content)
        
        assert id1 == id2
        
        # Only one file should exist
        files = os.listdir(temp_blob_dir)
        assert len(files) == 1
    
    def test_different_content_different_ids(self, blob_store):
        """Test that different content produces different blob IDs."""
        id1 = blob_store.save_text("Content A")
        id2 = blob_store.save_text("Content B")
        
        assert id1 != id2
    
    def test_get_nonexistent_blob(self, blob_store):
        """Test retrieving a non-existent blob returns None."""
        result = blob_store.get_text("nonexistent_id")
        assert result is None
    
    def test_delete_blob(self, blob_store, temp_blob_dir):
        """Test deleting a blob."""
        content = "To be deleted"
        blob_id = blob_store.save_text(content)
        
        # Verify it exists
        assert blob_store.get_text(blob_id) == content
        
        # Delete it
        blob_store.delete(blob_id)
        
        # Verify it's gone
        assert blob_store.get_text(blob_id) is None
    
    def test_delete_nonexistent_blob(self, blob_store):
        """Test deleting a non-existent blob doesn't raise."""
        # Should not raise
        blob_store.delete("nonexistent_id")
    
    def test_unicode_content(self, blob_store):
        """Test storing Unicode content."""
        content = "こんにちは世界 🌍 Привет мир"
        
        blob_id = blob_store.save_text(content)
        retrieved = blob_store.get_text(blob_id)
        
        assert retrieved == content
    
    def test_large_content(self, blob_store):
        """Test storing large content."""
        content = "x" * (1024 * 1024)  # 1MB of 'x'
        
        blob_id = blob_store.save_text(content)
        retrieved = blob_store.get_text(blob_id)
        
        assert retrieved == content
