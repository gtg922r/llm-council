import pytest
import os
from backend.infrastructure.blob_store import BlobStore

def test_save_get_blob(tmp_path):
    # Setup blob store with tmp path
    store = BlobStore(blob_dir=str(tmp_path))
    
    content = "This is a large file content"
    ref_id = store.save_text(content)
    
    assert ref_id is not None
    assert len(ref_id) > 0
    
    # Get it back
    loaded = store.get_text(ref_id)
    assert loaded == content

def test_get_nonexistent_blob(tmp_path):
    store = BlobStore(blob_dir=str(tmp_path))
    with pytest.raises(FileNotFoundError):
        store.get_text("nonexistent")
