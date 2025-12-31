"""Prompt construction utilities."""

from __future__ import annotations

from typing import Iterable

from ..domain.models import FileAttachment
from ..infrastructure.blob_store import LocalFileBlobStore


def build_prompt_content(
    *,
    content: str,
    files: Iterable[FileAttachment] | None,
    blob_store: LocalFileBlobStore,
) -> str:
    """Construct the final prompt with user content and file blocks."""
    files = list(files or [])
    if not files:
        return content

    sections: list[str] = [content]
    for attachment in files:
        file_content = blob_store.get_text(attachment.file_reference_id)
        sections.append(
            f"--- FILE: {attachment.name} ---\n"
            f"{file_content}\n"
            f"--- END FILE: {attachment.name} ---"
        )
    return "\n\n".join(sections)

