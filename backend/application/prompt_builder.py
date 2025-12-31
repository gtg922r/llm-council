"""Prompt construction helpers (application-layer).

This is the glue between domain messages (which may reference blobs) and the
final prompt string sent to the LLM provider.
"""

from __future__ import annotations

from collections.abc import Iterable

from ..domain.models import FileAttachment
from ..ports import BlobStore


def build_prompt_content(content: str, files: Iterable[FileAttachment], blob_store: BlobStore) -> str:
    """Construct the final prompt with user content and resolved file blocks."""
    sections: list[str] = [content]
    for f in files:
        file_content: str | None = None
        if f.reference_id:
            file_content = blob_store.get_text(f.reference_id)
        elif f.content is not None:  # legacy
            file_content = f.content

        if file_content is None:
            continue

        sections.append(
            f"--- FILE: {f.name} ---\n{file_content}\n--- END FILE: {f.name} ---"
        )
    return "\n\n".join(sections)

