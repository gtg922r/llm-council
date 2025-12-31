"""FastAPI backend for LLM Council."""

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Any, Dict, List
import uuid

from . import config

from .application.council_service import CouncilConfig, CouncilService
from .domain.events import Stage1Complete, Stage2Complete, Stage3Complete
from .domain.models import Conversation, ConversationSummary
from .infrastructure.blob_store import LocalFileBlobStore
from .infrastructure.json_repository import JsonConversationRepository
from .infrastructure.openrouter_adapter import OpenRouterAdapter
from .interface.sse import format_sse_data

app = FastAPI(title="LLM Council API")

# Configure CORS origins based on environment
if config.IS_CODESPACE or config.DEBUG_MODE:
    # Relaxed CORS for Codespaces/Development
    allow_origins = ["*"]
else:
    # Strict CORS for production
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
    pass


class FileContext(BaseModel):
    """Structured file context sent alongside a message."""
    name: str
    content: str
    size: int | None = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    files: List[FileContext] = Field(default_factory=list)
    target_model: str | None = None # e.g., "chairman" for follow-up


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

def get_repo() -> JsonConversationRepository:
    return JsonConversationRepository(config.DATA_DIR)


def get_blob_store() -> LocalFileBlobStore:
    return LocalFileBlobStore(config.BLOB_DIR)


def get_llm() -> OpenRouterAdapter:
    return OpenRouterAdapter()


def get_council_service(
    repo: JsonConversationRepository = Depends(get_repo),
    blob_store: LocalFileBlobStore = Depends(get_blob_store),
    llm: OpenRouterAdapter = Depends(get_llm),
) -> CouncilService:
    return CouncilService(
        repo=repo,
        blob_store=blob_store,
        llm=llm,
        config=CouncilConfig(
            council_models=list(config.COUNCIL_MODELS),
            chairman_model=config.CHAIRMAN_MODEL,
        ),
    )

@app.get("/api/conversations", response_model=List[ConversationSummary], response_model_exclude_none=True)
async def list_conversations(repo: JsonConversationRepository = Depends(get_repo)):
    """List all conversations (metadata only)."""
    return repo.list()


@app.post("/api/conversations", response_model=Conversation, response_model_exclude_none=True)
async def create_conversation(
    request: CreateConversationRequest,
    repo: JsonConversationRepository = Depends(get_repo),
):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    return repo.create(conversation_id)


@app.get("/api/conversations/{conversation_id}", response_model=Conversation, response_model_exclude_none=True)
async def get_conversation(
    conversation_id: str, repo: JsonConversationRepository = Depends(get_repo)
):
    """Get a specific conversation with all its messages."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation, response_model_exclude_none=True)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    repo: JsonConversationRepository = Depends(get_repo),
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
async def delete_conversation(
    conversation_id: str, repo: JsonConversationRepository = Depends(get_repo)
):
    """Permanently delete a conversation."""
    repo.delete(conversation_id)
    return {"status": "success"}


@app.post(
    "/api/conversations/{conversation_id}/duplicate",
    response_model=Conversation,
    response_model_exclude_none=True,
)
async def duplicate_conversation(
    conversation_id: str, repo: JsonConversationRepository = Depends(get_repo)
):
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
    repo: JsonConversationRepository = Depends(get_repo),
    service: CouncilService = Depends(get_council_service),
):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    files_payload = [file.model_dump() for file in request.files] if request.files else None

    stage1 = []
    stage2 = []
    stage3 = None
    metadata = {}

    async for event in service.run_message_events(
        conversation_id=conversation_id,
        content=request.content,
        files=files_payload,
        target_model=request.target_model,
    ):
        if isinstance(event, Stage1Complete):
            stage1 = [r.model_dump(mode="json") for r in event.data]
        elif isinstance(event, Stage2Complete):
            stage2 = [r.model_dump(mode="json") for r in event.data]
            metadata = event.metadata.model_dump(mode="json")
        elif isinstance(event, Stage3Complete):
            stage3 = event.data.model_dump(mode="json")

    if stage3 is None:
        raise HTTPException(status_code=500, detail="Failed to produce a response")

    return {"stage1": stage1, "stage2": stage2, "stage3": stage3, "metadata": metadata}


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    repo: JsonConversationRepository = Depends(get_repo),
    service: CouncilService = Depends(get_council_service),
):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    if repo.get(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    files_payload = [file.model_dump() for file in request.files] if request.files else None

    async def event_generator():
        async for event in service.run_message_events(
            conversation_id=conversation_id,
            content=request.content,
            files=files_payload,
            target_model=request.target_model,
        ):
            yield format_sse_data(event)

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
