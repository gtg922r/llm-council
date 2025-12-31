"""Blob store for storing large file content separately from conversation JSON.

This module provides a local file-based blob store that stores large text content
(like file attachments) as individual files, keeping the conversation JSON small
and enabling efficient storage and retrieval of large content.
"""

import hashlib
import os
import uuid
from pathlib import Path
from typing import Optional


class LocalBlobStore:
    """Local filesystem-based blob store.
    
    Stores text content as individual files in a specified directory,
    returning unique reference IDs that can be used to retrieve the content later.
    
    Supports optional content-based deduplication using SHA-256 hashes.
    """
    
    def __init__(self, blob_dir: str):
        """Initialize the blob store.
        
        Args:
            blob_dir: Directory path where blobs will be stored.
        """
        self.blob_dir = Path(blob_dir)
        self._ensure_dir()
    
    def _ensure_dir(self):
        """Ensure the blob directory exists."""
        self.blob_dir.mkdir(parents=True, exist_ok=True)
    
    def _get_path(self, reference_id: str) -> Path:
        """Get the file path for a given reference ID."""
        return self.blob_dir / f"{reference_id}.txt"
    
    def _compute_hash(self, content: str) -> str:
        """Compute SHA-256 hash of content for deduplication."""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def save_text(self, content: str, deduplicate: bool = False) -> str:
        """Save text content and return a reference ID.
        
        Args:
            content: The text content to save.
            deduplicate: If True, use content hash as reference ID for deduplication.
                        If False, generate a new UUID for each save.
        
        Returns:
            A unique reference ID that can be used to retrieve the content.
        """
        self._ensure_dir()
        
        if deduplicate:
            # Use content hash for deduplication
            reference_id = self._compute_hash(content)
            blob_path = self._get_path(reference_id)
            
            # Only write if it doesn't exist
            if not blob_path.exists():
                blob_path.write_text(content, encoding='utf-8')
        else:
            # Generate new UUID for each save
            reference_id = str(uuid.uuid4())
            blob_path = self._get_path(reference_id)
            blob_path.write_text(content, encoding='utf-8')
        
        return reference_id
    
    def get_text(self, reference_id: str) -> Optional[str]:
        """Retrieve text content by reference ID.
        
        Args:
            reference_id: The reference ID returned from save_text.
        
        Returns:
            The text content, or None if not found.
        """
        blob_path = self._get_path(reference_id)
        
        if not blob_path.exists():
            return None
        
        return blob_path.read_text(encoding='utf-8')
    
    def exists(self, reference_id: str) -> bool:
        """Check if a blob exists.
        
        Args:
            reference_id: The reference ID to check.
        
        Returns:
            True if the blob exists, False otherwise.
        """
        return self._get_path(reference_id).exists()
    
    def delete(self, reference_id: str) -> bool:
        """Delete a blob.
        
        Args:
            reference_id: The reference ID of the blob to delete.
        
        Returns:
            True if the blob was deleted, False if it didn't exist.
        """
        blob_path = self._get_path(reference_id)
        
        if blob_path.exists():
            blob_path.unlink()
            return True
        
        return False
    
    def get_size(self, reference_id: str) -> Optional[int]:
        """Get the size of a blob in bytes.
        
        Args:
            reference_id: The reference ID of the blob.
        
        Returns:
            Size in bytes, or None if not found.
        """
        blob_path = self._get_path(reference_id)
        
        if not blob_path.exists():
            return None
        
        return blob_path.stat().st_size


# Default blob store instance (can be overridden for testing or configuration)
_default_blob_dir = "data/blobs"


def get_default_blob_store() -> LocalBlobStore:
    """Get the default blob store instance."""
    return LocalBlobStore(_default_blob_dir)
