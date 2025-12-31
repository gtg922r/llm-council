"""FastAPI interface layer for LLM Council (hexagonal architecture)."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from . import config
from .application.council_service import CouncilOrchestrator
from .domain.events import StageCompleted
from .domain.models import Conversation, ConversationMetadata
from .infrastructure.blob_store import LocalFileBlobStore
from .infrastructure.json_repository import JsonConversationRepository
from .infrastructure.openrouter_adapter import OpenRouterAdapter
from .ports import ConversationRepository, LLMProvider

app = FastAPI(title="LLM Council API")

# Configure CORS origins based on environment
if config.IS_CODESPACE or config.DEBUG_MODE:
    allow_origins = ["*"]
else:
    allow_origins = ["http://localhost:5173", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""


class FileContext(BaseModel):
    """Structured file context sent alongside a message."""

    name: str
    content: str
    size: int | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""

    content: str
    files: list[FileContext] = Field(default_factory=list)
    target_model: str | None = None  # e.g., "chairman" for follow-up


class UpdateConversationRequest(BaseModel):
    """Request to update conversation flags."""

    title: str | None = None
    is_pinned: bool | None = None
    is_archived: bool | None = None
    has_unread: bool | None = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


def get_repo() -> ConversationRepository:
    return JsonConversationRepository(config.DATA_CONVERSATIONS_DIR)


def get_blob_store() -> LocalFileBlobStore:
    return LocalFileBlobStore(config.DATA_BLOBS_DIR)


def get_llm_provider() -> LLMProvider:
    return OpenRouterAdapter(api_key=config.OPENROUTER_API_KEY, api_url=config.OPENROUTER_API_URL)


def get_council_service(
    repo: ConversationRepository = Depends(get_repo),
    llm: LLMProvider = Depends(get_llm_provider),
    blob_store: LocalFileBlobStore = Depends(get_blob_store),
) -> CouncilOrchestrator:
    return CouncilOrchestrator(
        repo=repo,
        llm=llm,
        blob_store=blob_store,
        council_models=config.COUNCIL_MODELS,
        chairman_model=config.CHAIRMAN_MODEL,
    )


@app.get("/api/conversations", response_model=list[ConversationMetadata])
async def list_conversations(repo: ConversationRepository = Depends(get_repo)):
    """List all conversations (metadata only)."""
    return repo.list()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(
    _request: CreateConversationRequest,
    repo: ConversationRepository = Depends(get_repo),
):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    return repo.create(conversation_id)


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str, repo: ConversationRepository = Depends(get_repo)):
    """Get a specific conversation with all its messages."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    repo: ConversationRepository = Depends(get_repo),
):
    """Update conversation metadata (title, pinned, archived)."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    if request.title is not None:
        conversation.title = request.title
    if request.is_pinned is not None:
        conversation.is_pinned = request.is_pinned
    if request.is_archived is not None:
        conversation.is_archived = request.is_archived
    if request.has_unread is not None:
        conversation.has_unread = request.has_unread

    repo.save(conversation)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str, repo: ConversationRepository = Depends(get_repo)):
    """Permanently delete a conversation."""
    repo.delete(conversation_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/duplicate", response_model=Conversation)
async def duplicate_conversation(conversation_id: str, repo: ConversationRepository = Depends(get_repo)):
    """Duplicate a conversation."""
    new_id = str(uuid.uuid4())
    try:
        return repo.duplicate(conversation_id, new_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    service: CouncilOrchestrator = Depends(get_council_service),
):
    """Send a message and run the 3-stage council process (non-streaming)."""
    stage1: list[Any] = []
    stage2: list[Any] = []
    stage3: Any = None
    metadata: dict[str, Any] = {}

    async for event in service.run(
        conversation_id=conversation_id,
        content=request.content,
        files=[f.model_dump() for f in request.files] if request.files else None,
        target_model=request.target_model,
    ):
        if isinstance(event, StageCompleted):
            if event.stage == "stage1":
                stage1 = event.data or []
            elif event.stage == "stage2":
                stage2 = event.data or []
                metadata = event.metadata or {}
            elif event.stage == "stage3":
                stage3 = event.data

    return {"stage1": stage1, "stage2": stage2, "stage3": stage3, "metadata": metadata}


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    service: CouncilOrchestrator = Depends(get_council_service),
):
    """Send a message and stream Domain Events via SSE."""

    async def event_generator():
        async for event in service.run(
            conversation_id=conversation_id,
            content=request.content,
            files=[f.model_dump() for f in request.files] if request.files else None,
            target_model=request.target_model,
        ):
            yield f"data: {event.model_dump_json()}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)

