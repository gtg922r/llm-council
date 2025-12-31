import os
import hashlib
from pathlib import Path

class BlobStore:
    """Local file persistence for large text blobs."""
    
    def __init__(self, blob_dir: str = "data/blobs"):
        self.blob_dir = Path(blob_dir)
        self.ensure_blob_dir()
        
    def ensure_blob_dir(self):
        """Ensure the blob directory exists."""
        self.blob_dir.mkdir(parents=True, exist_ok=True)
        
    def save_text(self, content: str) -> str:
        """
        Save text content to a blob file.
        Returns a SHA-256 hash as the reference_id.
        """
        # Calculate hash
        ref_id = hashlib.sha256(content.encode('utf-8')).hexdigest()
        
        path = self.blob_dir / f"{ref_id}.txt"
        
        # If file already exists, we can skip writing (deduplication)
        if not path.exists():
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
                
        return ref_id
        
    def get_text(self, reference_id: str) -> str:
        """
        Retrieve text content by reference_id.
        Raises FileNotFoundError if not found.
        """
        path = self.blob_dir / f"{reference_id}.txt"
        
        if not path.exists():
            raise FileNotFoundError(f"Blob with ID {reference_id} not found.")
            
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
