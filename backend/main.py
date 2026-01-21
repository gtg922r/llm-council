"""FastAPI backend for LLM Council.

This is the Interface Layer - responsible only for HTTP requests/responses
and calling the Application layer (CouncilOrchestrator).
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
import uuid
import json

from . import config
from .infrastructure.blob_store import BlobStore
from .infrastructure.json_repository import JsonConversationRepository
from .infrastructure.openrouter_adapter import OpenRouterAdapter
from .application.council_service import CouncilOrchestrator
from .domain.models import (
    Attachment, 
    Conversation as ConversationModel, 
    UserMessage as UserMessageModel, 
    AssistantMessage as AssistantMessageModel,
)

app = FastAPI(title="LLM Council API")

# Infrastructure Adapters (Dependency Injection)
conversation_repo = JsonConversationRepository(data_dir=config.DATA_DIR)
llm_provider = OpenRouterAdapter(api_key=config.OPENROUTER_API_KEY)
blob_store = BlobStore()

# Application Services
orchestrator = CouncilOrchestrator(
    llm_provider=llm_provider, 
    conversation_repo=conversation_repo,
    blob_store=blob_store
)

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


# Request/Response Models
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
    target_model: str | None = None  # e.g., "chairman" for follow-up
    model_mode: str = "smart"  # "fast" or "smart"


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: datetime
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: datetime
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: List[Dict[str, Any]]


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


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return conversation_repo.list()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = ConversationModel(
        id=conversation_id,
        created_at=datetime.now(),
        title="New Conversation"
    )
    conversation_repo.save(conversation)
    return conversation.model_dump()


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = conversation_repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation.model_dump()


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """Update conversation metadata (title, pinned, archived)."""
    conversation = conversation_repo.get(conversation_id)
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
        
    conversation_repo.save(conversation)
    return conversation.model_dump()


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Permanently delete a conversation."""
    conversation_repo.delete(conversation_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/duplicate", response_model=Conversation)
async def duplicate_conversation(conversation_id: str):
    """Duplicate a conversation."""
    original = conversation_repo.get(conversation_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    new_id = str(uuid.uuid4())
    new_conv = ConversationModel(
        id=new_id,
        created_at=datetime.now(),
        title=f"{original.title} (Copy)",
        messages=original.messages.copy()
    )
    conversation_repo.save(new_conv)
    return new_conv.model_dump()


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = conversation_repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    # Process file attachments
    attachments = []
    if request.files:
        for f in request.files:
            ref_id = blob_store.save_text(f.content)
            attachments.append(Attachment(
                filename=f.name,
                content_type="text/plain",
                file_reference_id=ref_id,
                size=f.size
            ))
            
    # Add user message to conversation
    user_msg = UserMessageModel(
        content=request.content,
        files=attachments
    )
    conversation.messages.append(user_msg)
    conversation_repo.save(conversation)
    
    # Handle Chairman Follow-up
    if request.target_model == "chairman":
        stage3_result = await orchestrator.chairman_followup(
            conversation_id=conversation_id,
            followup_query=request.content,
            attachments=attachments,
            model_mode=request.model_mode
        )
        
        # Save the assistant message
        assistant_msg = AssistantMessageModel(
            stage1=[],
            stage2=[],
            stage3=stage3_result
        )
        conversation.messages.append(assistant_msg)
        conversation.has_unread = True
        conversation_repo.save(conversation)

        return {
            "stage1": [],
            "stage2": [],
            "stage3": stage3_result,
            "metadata": {}
        }

    # Run the full 3-stage council process
    final_result = {
        "stage1": [],
        "stage2": [],
        "stage3": {},
        "metadata": {}
    }
    
    async for event in orchestrator.run_council(
        conversation_id, 
        request.content,
        attachments=attachments,
        is_first_message=is_first_message,
        model_mode=request.model_mode
    ):
        if event.type == "stage_complete":
            if event.stage == 1:
                final_result["stage1"] = event.data
            elif event.stage == 2:
                final_result["stage2"] = event.data
                final_result["metadata"] = event.metadata
            elif event.stage == 3:
                final_result["stage3"] = event.data
                
    return final_result


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = conversation_repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    async def event_generator():
        try:
            # Send initial ping to establish connection
            yield ": ping\n\n"
            
            # Process file attachments
            attachments = []
            if request.files:
                for f in request.files:
                    ref_id = blob_store.save_text(f.content)
                    attachments.append(Attachment(
                        filename=f.name,
                        content_type="text/plain",
                        file_reference_id=ref_id,
                        size=f.size
                    ))
            
            # Add user message
            user_msg = UserMessageModel(
                content=request.content,
                files=attachments
            )
            conversation.messages.append(user_msg)
            conversation_repo.save(conversation)
            
            # Stream events from orchestrator
            async for event in orchestrator.run_council(
                conversation_id, 
                request.content,
                attachments=attachments,
                is_first_message=is_first_message,
                model_mode=request.model_mode
            ):
                yield f"data: {event.model_dump_json()}\n\n"

        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx/proxy buffering
            "Transfer-Encoding": "chunked",
        }
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
