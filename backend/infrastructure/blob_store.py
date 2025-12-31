"""Local filesystem blob store for large text payloads (e.g., file attachments)."""

from __future__ import annotations

import uuid
from pathlib import Path

from ..ports import BlobStore


class LocalFileBlobStore(BlobStore):
    """Stores blobs as individual UTF-8 text files.

    This keeps conversation JSON small and enables future migration to DB/object storage.
    """

    def __init__(self, blob_dir: str | Path):
        self._dir = Path(blob_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    def save_text(self, content: str) -> str:
        reference_id = str(uuid.uuid4())
        path = self._dir / f"{reference_id}.txt"
        path.write_text(content, encoding="utf-8")
        return reference_id

    def get_text(self, reference_id: str) -> str:
        path = self._dir / f"{reference_id}.txt"
        return path.read_text(encoding="utf-8")

