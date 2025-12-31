import os
import uuid
from typing import Optional
from pathlib import Path
from ..config import DATA_DIR

BLOB_DIR = os.path.join(DATA_DIR, "blobs")

def ensure_blob_dir():
    Path(BLOB_DIR).mkdir(parents=True, exist_ok=True)

class BlobStore:
    def store_blob(self, content: str) -> str:
        """Store content as a blob and return its reference ID."""
        ensure_blob_dir()
        blob_id = str(uuid.uuid4())
        path = os.path.join(BLOB_DIR, blob_id)
        with open(path, 'w') as f:
            f.write(content)
        return blob_id

    def get_blob(self, blob_id: str) -> Optional[str]:
        """Retrieve content from a blob reference."""
        path = os.path.join(BLOB_DIR, blob_id)
        if not os.path.exists(path):
            return None
        with open(path, 'r') as f:
            return f.read()

    def delete_blob(self, blob_id: str):
        """Delete a blob."""
        path = os.path.join(BLOB_DIR, blob_id)
        if os.path.exists(path):
            os.remove(path)

# Global instance
blob_store = BlobStore()
