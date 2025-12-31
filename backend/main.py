"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Union
import uuid
import json
import asyncio
from datetime import datetime, timezone

from .infrastructure.blob_store import blob_store
from .infrastructure.json_repository import JsonConversationRepository
from .infrastructure.openrouter_adapter import OpenRouterAdapter
from .application.council_service import CouncilService
from .domain.models import Conversation, UserMessage, AssistantMessage, FileReference
from .domain.events import Stage1Complete, Stage2Complete, Stage3Complete, CouncilError
from . import config
from .council import chairman_followup, generate_conversation_title

app = FastAPI(title="LLM Council API")

# Initialize Infrastructure
repository = JsonConversationRepository()
llm_provider = OpenRouterAdapter()

# Initialize Service
council_service = CouncilService(repository, llm_provider)

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


def build_prompt_content(
    content: str,
    files: List[FileContext] | List[Dict[str, Any]] | None
) -> str:
    """Construct the final prompt with user content and file blocks."""
    if not files:
        return content

    sections = [content]
    for file_context in files:
        if isinstance(file_context, dict):
            name = file_context.get("name")
            file_content = file_context.get("content")
        else:
            name = file_context.name
            file_content = file_context.content
        if name is None or file_content is None:
            raise ValueError("File context must include name and content.")
        sections.append(
            f"--- FILE: {name} ---\n"
            f"{file_content}\n"
            f"--- END FILE: {name} ---"
        )

    return "\n\n".join(sections)


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    has_unread: bool = False
    message_count: int


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
    return repository.list_metadata()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = repository.create(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """Update conversation metadata (title, pinned, archived)."""
    conversation = repository.get(conversation_id)
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
        
    repository.save(conversation)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Permanently delete a conversation."""
    repository.delete(conversation_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/duplicate", response_model=Conversation)
async def duplicate_conversation(conversation_id: str):
    """Duplicate a conversation."""
    original = repository.get(conversation_id)
    if original is None:
        raise HTTPException(status_code=404, detail="Original conversation not found")

    new_id = str(uuid.uuid4())
    
    new_conversation = Conversation(
        id=new_id,
        created_at=datetime.now(timezone.utc).isoformat(),
        title=f"{original.title} (Copy)",
        is_pinned=False,
        is_archived=False,
        has_unread=False,
        messages=original.messages
    )
    
    repository.save(new_conversation)
    return new_conversation


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    prompt_content = build_prompt_content(request.content, request.files)
    
    # Process files
    files_payload = []
    if request.files:
        for file in request.files:
            blob_id = blob_store.store_blob(file.content)
            files_payload.append(FileReference(
                name=file.name,
                file_reference_id=blob_id,
                size=file.size or len(file.content)
            ))

    # Check for Follow-up (Target: Chairman)
    if request.target_model == "chairman":
        # Add user message first
        user_msg = UserMessage(content=request.content, files=files_payload)
        conversation.messages.append(user_msg)
        repository.save(conversation)
        
        # Find context
        last_assistant_msg = None
        for msg in reversed(conversation.messages):
            if isinstance(msg, AssistantMessage) and msg.stage3:
                last_assistant_msg = msg
                break
        
        if last_assistant_msg:
            # We found context
            original_query = "Unknown (Context from previous turn)"
            try:
                idx = conversation.messages.index(last_assistant_msg)
                # Look before the assistant message
                # Note: This index lookup on list of objects might fail if objects are recreated or equality check issues.
                # Since conversation.messages is loaded from persistence, objects should be stable in this request scope.
                if idx > 0 and isinstance(conversation.messages[idx-1], UserMessage):
                    original_query = conversation.messages[idx-1].content
            except ValueError:
                pass
            
            stage3_result = await chairman_followup(
                original_query=original_query,
                stage1_results=[s.model_dump() for s in last_assistant_msg.stage1],
                stage2_results=[s.model_dump() for s in last_assistant_msg.stage2],
                stage3_response=last_assistant_msg.stage3.response,
                followup_query=prompt_content
            )

            # Store result
            assistant_msg = AssistantMessage(
                stage1=[],
                stage2=[],
                stage3=stage3_result,
                metadata={}
            )
            conversation.messages.append(assistant_msg)
            conversation.has_unread = True
            repository.save(conversation)

            return {
                "stage1": [],
                "stage2": [],
                "stage3": stage3_result,
                "metadata": {}
            }

    # Run the 3-stage council process via Service
    final_stage1 = []
    final_stage2 = []
    final_stage3 = None
    final_metadata = {}
    
    async for event in council_service.run_council(
        conversation_id, 
        prompt_content, 
        request.content, 
        files_payload, 
        is_first_message
    ):
        if event.type == "stage1_complete":
            final_stage1 = event.data
        elif event.type == "stage2_complete":
            final_stage2 = event.data
            final_metadata = event.metadata
        elif event.type == "stage3_complete":
            final_stage3 = event.data
        elif event.type == "error":
             raise HTTPException(status_code=500, detail=event.message)

    # Return the complete response with metadata
    return {
        "stage1": final_stage1,
        "stage2": final_stage2,
        "stage3": final_stage3,
        "metadata": final_metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = repository.get(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation.messages) == 0

    prompt_content = build_prompt_content(request.content, request.files)
    
    # Process files
    files_payload = []
    if request.files:
        for file in request.files:
            blob_id = blob_store.store_blob(file.content)
            files_payload.append(FileReference(
                name=file.name,
                file_reference_id=blob_id,
                size=file.size or len(file.content)
            ))

    async def event_generator():
        async for event in council_service.run_council(
            conversation_id, 
            prompt_content, 
            request.content,
            files_payload,
            is_first_message
        ):
            yield f"data: {event.model_dump_json()}\n\n"

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
