from typing import List, Dict, Any, Optional, Union
from ..domain.models import Attachment
from ..infrastructure.blob_store import BlobStore

def build_prompt_content(
    content: str,
    files: List[Any] | None,
    blob_store: Optional[BlobStore] = None
) -> str:
    """Construct the final prompt with user content and file blocks."""
    if not files:
        return content

    if blob_store is None:
        blob_store = BlobStore()
        
    sections = [content]
    for f in files:
        # Handle dicts (legacy or from API requests)
        if isinstance(f, dict):
            name = f.get("name") or f.get("filename")
            file_content = f.get("content")
        # Handle Attachment domain models
        elif isinstance(f, Attachment):
            name = f.filename
            if f.file_reference_id:
                try:
                    file_content = blob_store.get_text(f.file_reference_id)
                except FileNotFoundError:
                    file_content = f.content or "[Error: Content not found in blob store]"
            else:
                file_content = f.content
        # Handle FileContext objects (from main.py Pydantic models)
        else:
            name = getattr(f, "name", None) or getattr(f, "filename", None)
            file_content = getattr(f, "content", None)
            
        if name is None or file_content is None:
            # Skip invalid files or handle error
            continue
            
        sections.append(
            f"--- FILE: {name} ---\n"
            f"{file_content}\n"
            f"--- END FILE: {name} ---"
        )

    return "\n\n".join(sections)
