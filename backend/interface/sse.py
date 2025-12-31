"""SSE formatting helpers for FastAPI routes.

Kept separate so `backend/main.py` stays free of low-level JSON concerns.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel


def format_sse_data(event: BaseModel | dict[str, Any]) -> str:
    """Format a single SSE `data:` block."""
    payload = event.model_dump(mode="json") if isinstance(event, BaseModel) else event
    return f"data: {json.dumps(payload)}\n\n"

