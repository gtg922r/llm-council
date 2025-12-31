"""FastAPI backend for LLM Council.

This module serves as the interface layer, handling HTTP requests/responses
and delegating to the application layer for business logic.
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import json

from . import config
from .ports import ConversationRepository, BlobStorePort, LLMProvider
from .infrastructure import (
    JsonConversationRepository,
    BlobStore,
    OpenRouterAdapter,
)
from .application import CouncilService
from .domain.models import (
    Conversation,
    ConversationMetadata,
    UserMessage,
    AssistantMessage,
    Stage1Result,
    Stage2Result,
    Stage3Result,
    CouncilMetadata,
    AggregateRanking,
    FileReference,
    Stage1Complete,
    Stage2Complete,
    Stage3Complete,
    TitleGenerated,
    CouncilComplete,
    CouncilError,
)

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


# Dependency Injection - Infrastructure instances
def get_repository() -> ConversationRepository:
    """Provide the conversation repository."""
    return JsonConversationRepository()


def get_blob_store() -> BlobStorePort:
    """Provide the blob store."""
    return BlobStore()


def get_llm_provider() -> LLMProvider:
    """Provide the LLM provider."""
    return OpenRouterAdapter()


def get_council_service(
    llm: LLMProvider = Depends(get_llm_provider),
    blob_store: BlobStorePort = Depends(get_blob_store)
) -> CouncilService:
    """Provide the council service."""
    return CouncilService(llm_provider=llm, blob_store=blob_store)


# Request/Response Models
class CreateConversationRequest(BaseModel):
    """Request to create a new conversation."""
    pass


class FileContextRequest(BaseModel):
    """File context sent alongside a message (before blob storage)."""
    name: str
    content: str
    size: Optional[int] = None


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    files: List[FileContextRequest] = Field(default_factory=list)
    target_model: Optional[str] = None  # e.g., "chairman" for follow-up


class ConversationMetadataResponse(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int


class ConversationResponse(BaseModel):
    """Full conversation response."""
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    messages: List[Dict[str, Any]]


class UpdateConversationRequest(BaseModel):
    """Request to update conversation flags."""
    title: Optional[str] = None
    is_pinned: Optional[bool] = None
    is_archived: Optional[bool] = None
    has_unread: Optional[bool] = None


def _conversation_to_response(conv: Conversation) -> ConversationResponse:
    """Convert a domain Conversation to API response format."""
    messages = []
    for msg in conv.messages:
        if isinstance(msg, UserMessage):
            msg_dict = {
                "role": "user",
                "content": msg.content,
            }
            if msg.files:
                msg_dict["files"] = [
                    {"name": f.name, "size": f.size}
                    for f in msg.files
                ]
            messages.append(msg_dict)
        elif isinstance(msg, AssistantMessage):
            messages.append({
                "role": "assistant",
                "stage1": [r.model_dump() for r in msg.stage1],
                "stage2": [r.model_dump() for r in msg.stage2],
                "stage3": msg.stage3.model_dump() if msg.stage3 else None,
                "metadata": {
                    "label_to_model": msg.metadata.label_to_model,
                    "aggregate_rankings": [
                        r.model_dump() for r in msg.metadata.aggregate_rankings
                    ]
                }
            })
    
    return ConversationResponse(
        id=conv.id,
        created_at=conv.created_at.isoformat(),
        title=conv.title,
        is_pinned=conv.is_pinned,
        is_archived=conv.is_archived,
        has_unread=conv.has_unread,
        messages=messages
    )


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadataResponse])
async def list_conversations(repo: ConversationRepository = Depends(get_repository)):
    """List all conversations (metadata only)."""
    metadata_list = repo.list()
    return [
        ConversationMetadataResponse(
            id=m.id,
            created_at=m.created_at.isoformat(),
            title=m.title,
            is_pinned=m.is_pinned,
            is_archived=m.is_archived,
            has_unread=m.has_unread,
            message_count=m.message_count
        )
        for m in metadata_list
    ]


@app.post("/api/conversations", response_model=ConversationResponse)
async def create_conversation(
    request: CreateConversationRequest,
    repo: ConversationRepository = Depends(get_repository)
):
    """Create a new conversation."""
    conversation = Conversation(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        title="New Conversation",
        messages=[]
    )
    repo.save(conversation)
    return _conversation_to_response(conversation)


@app.get("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def get_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_repository)
):
    """Get a specific conversation with all its messages."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return _conversation_to_response(conversation)


@app.patch("/api/conversations/{conversation_id}", response_model=ConversationResponse)
async def update_conversation(
    conversation_id: str,
    request: UpdateConversationRequest,
    repo: ConversationRepository = Depends(get_repository)
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
    return _conversation_to_response(conversation)


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_repository)
):
    """Permanently delete a conversation."""
    repo.delete(conversation_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/duplicate", response_model=ConversationResponse)
async def duplicate_conversation(
    conversation_id: str,
    repo: ConversationRepository = Depends(get_repository)
):
    """Duplicate a conversation."""
    original = repo.get(conversation_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    new_conversation = Conversation(
        id=str(uuid.uuid4()),
        created_at=datetime.now(timezone.utc),
        title=f"{original.title} (Copy)",
        is_pinned=False,
        is_archived=False,
        has_unread=False,
        messages=original.messages.copy()
    )
    repo.save(new_conversation)
    return _conversation_to_response(new_conversation)


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(
    conversation_id: str,
    request: SendMessageRequest,
    repo: ConversationRepository = Depends(get_repository),
    blob_store: BlobStorePort = Depends(get_blob_store),
    council_service: CouncilService = Depends(get_council_service)
):
    """Send a message and run the 3-stage council process."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    is_first_message = len(conversation.messages) == 0
    
    # Store files in blob store and create references
    file_refs = []
    for file_ctx in request.files:
        blob_id = blob_store.save_text(file_ctx.content)
        file_refs.append(FileReference(
            name=file_ctx.name,
            blob_id=blob_id,
            size=file_ctx.size
        ))
    
    # Add user message
    user_msg = UserMessage(content=request.content, files=file_refs)
    conversation.messages.append(user_msg)
    
    # Handle Follow-up (Target: Chairman)
    if request.target_model == "chairman":
        last_assistant_msg = None
        for msg in reversed(conversation.messages):
            if isinstance(msg, AssistantMessage) and msg.stage3:
                last_assistant_msg = msg
                break
        
        if last_assistant_msg:
            # Find original query
            original_query = "Unknown"
            try:
                idx = conversation.messages.index(last_assistant_msg)
                if idx > 0:
                    prev_msg = conversation.messages[idx - 1]
                    if isinstance(prev_msg, UserMessage):
                        original_query = prev_msg.content
            except ValueError:
                pass
            
            stage3_result = await council_service.run_followup(
                original_query=original_query,
                stage1_results=last_assistant_msg.stage1,
                stage2_results=last_assistant_msg.stage2,
                stage3_response=last_assistant_msg.stage3.response if last_assistant_msg.stage3 else "",
                followup_query=request.content
            )
            
            # Create assistant message for follow-up
            assistant_msg = AssistantMessage(
                stage1=[],
                stage2=[],
                stage3=stage3_result,
                metadata=CouncilMetadata()
            )
            conversation.messages.append(assistant_msg)
            conversation.has_unread = True
            repo.save(conversation)
            
            return {
                "stage1": [],
                "stage2": [],
                "stage3": stage3_result.model_dump(),
                "metadata": {"label_to_model": {}, "aggregate_rankings": []}
            }
    
    # Run full council process (non-streaming)
    stage1_results = []
    stage2_results = []
    stage3_result = None
    metadata = CouncilMetadata()
    title = None
    
    async for event in council_service.run_council(
        prompt=request.content,
        generate_title=is_first_message,
        files=file_refs
    ):
        if isinstance(event, Stage1Complete):
            stage1_results = event.data
        elif isinstance(event, Stage2Complete):
            stage2_results = event.data
            metadata = event.metadata
        elif isinstance(event, Stage3Complete):
            stage3_result = event.data
        elif isinstance(event, TitleGenerated):
            title = event.title
        elif isinstance(event, CouncilError):
            raise HTTPException(status_code=500, detail=event.message)
    
    # Update title if generated
    if title:
        conversation.title = title
    
    # Add assistant message
    assistant_msg = AssistantMessage(
        stage1=stage1_results,
        stage2=stage2_results,
        stage3=stage3_result,
        metadata=metadata
    )
    conversation.messages.append(assistant_msg)
    conversation.has_unread = True
    repo.save(conversation)
    
    return {
        "stage1": [r.model_dump() for r in stage1_results],
        "stage2": [r.model_dump() for r in stage2_results],
        "stage3": stage3_result.model_dump() if stage3_result else None,
        "metadata": {
            "label_to_model": metadata.label_to_model,
            "aggregate_rankings": [r.model_dump() for r in metadata.aggregate_rankings]
        }
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(
    conversation_id: str,
    request: SendMessageRequest,
    repo: ConversationRepository = Depends(get_repository),
    blob_store: BlobStorePort = Depends(get_blob_store),
    council_service: CouncilService = Depends(get_council_service)
):
    """Send a message and stream the 3-stage council process via SSE."""
    conversation = repo.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    is_first_message = len(conversation.messages) == 0
    
    async def event_generator():
        try:
            # Store files in blob store
            file_refs = []
            for file_ctx in request.files:
                blob_id = blob_store.save_text(file_ctx.content)
                file_refs.append(FileReference(
                    name=file_ctx.name,
                    blob_id=blob_id,
                    size=file_ctx.size
                ))
            
            # Add user message
            user_msg = UserMessage(content=request.content, files=file_refs)
            conversation.messages.append(user_msg)
            
            # Track results for saving
            stage1_results = []
            stage2_results = []
            stage3_result = None
            metadata = CouncilMetadata()
            title = None
            
            # Stream events from council service
            async for event in council_service.run_council(
                prompt=request.content,
                generate_title=is_first_message,
                files=file_refs
            ):
                # Convert domain event to SSE format
                event_dict = event.model_dump()
                
                # Track completed stages for persistence
                if isinstance(event, Stage1Complete):
                    stage1_results = event.data
                elif isinstance(event, Stage2Complete):
                    stage2_results = event.data
                    metadata = event.metadata
                    # Include metadata in the event
                    event_dict["metadata"] = {
                        "label_to_model": metadata.label_to_model,
                        "aggregate_rankings": [r.model_dump() for r in metadata.aggregate_rankings]
                    }
                elif isinstance(event, Stage3Complete):
                    stage3_result = event.data
                elif isinstance(event, TitleGenerated):
                    title = event.title
                    event_dict = {"type": "title_complete", "data": {"title": title}}
                elif isinstance(event, CouncilComplete):
                    # Save conversation before signaling completion
                    if title:
                        conversation.title = title
                    
                    assistant_msg = AssistantMessage(
                        stage1=stage1_results,
                        stage2=stage2_results,
                        stage3=stage3_result,
                        metadata=metadata
                    )
                    conversation.messages.append(assistant_msg)
                    conversation.has_unread = True
                    repo.save(conversation)
                
                yield f"data: {json.dumps(event_dict)}\n\n"
            
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
    
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
