"""Local file-based blob storage for large file content.

This keeps conversation JSON files small by storing file attachments
separately in data/blobs/.
"""

import hashlib
import os
from pathlib import Path
from typing import Optional

from ..ports import BlobStorePort
from ..config import BLOB_DIR


class BlobStore(BlobStorePort):
    """Local filesystem implementation of blob storage."""
    
    def __init__(self, blob_dir: str = BLOB_DIR):
        self.blob_dir = Path(blob_dir)
        self._ensure_dir()
    
    def _ensure_dir(self) -> None:
        """Ensure the blob directory exists."""
        self.blob_dir.mkdir(parents=True, exist_ok=True)
    
    def _generate_id(self, content: str) -> str:
        """Generate a content-addressable ID using SHA-256 hash."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def _get_path(self, reference_id: str) -> Path:
        """Get the file path for a blob ID."""
        return self.blob_dir / f"{reference_id}.txt"
    
    def save_text(self, content: str) -> str:
        """Save text content and return a reference ID.
        
        Uses content-addressable storage (hash-based IDs) for deduplication.
        """
        self._ensure_dir()
        
        reference_id = self._generate_id(content)
        path = self._get_path(reference_id)
        
        # Only write if not already exists (content-addressable deduplication)
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
        
        return reference_id
    
    def get_text(self, reference_id: str) -> Optional[str]:
        """Retrieve text content by reference ID."""
        path = self._get_path(reference_id)
        
        if not path.exists():
            return None
        
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def delete(self, reference_id: str) -> None:
        """Delete a blob by reference ID."""
        path = self._get_path(reference_id)
        
        if path.exists():
            os.remove(path)
