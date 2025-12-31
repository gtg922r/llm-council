"""Prompt builder for constructing LLM prompts with file content.

This module provides utilities for building prompts that include file attachments,
supporting both inline content and blob store references.
"""

from typing import List, Dict, Any, Optional, Union

from backend.domain.models import FileAttachment
from backend.infrastructure.blob_store import LocalBlobStore


def resolve_file_content(
    attachment: FileAttachment,
    blob_store: Optional[LocalBlobStore]
) -> str:
    """Resolve the content of a file attachment.
    
    Args:
        attachment: The FileAttachment to resolve content for.
        blob_store: Optional blob store for resolving blob references.
    
    Returns:
        The file content string.
    """
    if attachment.is_blob_reference:
        if blob_store is None:
            return "[Content unavailable - no blob store provided]"
        
        content = blob_store.get_text(attachment.blob_reference_id)
        if content is None:
            return "[Content unavailable - blob not found]"
        
        return content
    
    # Inline content
    return attachment.content or ""


def build_prompt_content(
    content: str,
    files: Optional[List[Union[FileAttachment, Dict[str, Any]]]],
    blob_store: Optional[LocalBlobStore]
) -> str:
    """Construct the final prompt with user content and file blocks.
    
    Args:
        content: The user's message content.
        files: Optional list of file attachments (FileAttachment or dict).
        blob_store: Optional blob store for resolving blob references.
    
    Returns:
        The complete prompt string with file content included.
    """
    if not files:
        return content

    sections = [content]
    
    for file_context in files:
        # Handle both FileAttachment objects and legacy dicts
        if isinstance(file_context, dict):
            name = file_context.get("name")
            file_content = file_context.get("content", "")
        elif isinstance(file_context, FileAttachment):
            name = file_context.name
            file_content = resolve_file_content(file_context, blob_store)
        else:
            continue
        
        if name is None:
            continue
        
        sections.append(
            f"--- FILE: {name} ---\n"
            f"{file_content}\n"
            f"--- END FILE: {name} ---"
        )

    return "\n\n".join(sections)
