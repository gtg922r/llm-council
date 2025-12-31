"""Local filesystem blob store for large text attachments."""

from __future__ import annotations

import uuid
from pathlib import Path


class LocalFileBlobStore:
    """
    Stores large text payloads out-of-line from conversation JSON.

    This keeps `data/conversations/*.json` small and makes it easier to migrate
    to a database later.
    """

    def __init__(self, base_dir: str):
        self._base_dir = Path(base_dir)

    def _ensure_dir(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)

    def save_text(self, content: str) -> str:
        self._ensure_dir()
        reference_id = str(uuid.uuid4())
        path = self._base_dir / f"{reference_id}.txt"
        path.write_text(content, encoding="utf-8")
        return reference_id

    def get_text(self, reference_id: str) -> str:
        path = self._base_dir / f"{reference_id}.txt"
        return path.read_text(encoding="utf-8")

