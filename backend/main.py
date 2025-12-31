"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import List, Dict, Any
from datetime import datetime
import uuid
import json
import asyncio

from . import config
from .config import COUNCIL_MODELS
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    chairman_followup,
    parse_ranking_from_text,
    Stage1Result,
    Stage2Result
)
from .infrastructure.blob_store import BlobStore
from .infrastructure.json_repository import JsonConversationRepository
from .infrastructure.openrouter_adapter import OpenRouterAdapter
from .domain.models import (
    Attachment, 
    Conversation as ConversationModel, 
    UserMessage as UserMessageModel, 
    AssistantMessage as AssistantMessageModel,
    AssistantMetadata
)
from .openrouter import query_model

app = FastAPI(title="LLM Council API")

# Infrastructure Adapters
conversation_repo = JsonConversationRepository(data_dir=config.DATA_DIR)
llm_provider = OpenRouterAdapter(api_key=config.OPENROUTER_API_KEY)
blob_store = BlobStore()

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
    files: List[FileContext] | List[Dict[str, Any]] | List[Attachment] | None
) -> str:
    """Construct the final prompt with user content and file blocks."""
    if not files:
        return content

    blob_store = BlobStore()
    sections = [content]
    for f in files:
        if isinstance(f, dict):
            name = f.get("name") or f.get("filename")
            file_content = f.get("content")
        elif isinstance(f, Attachment):
            name = f.filename
            if f.file_reference_id:
                try:
                    file_content = blob_store.get_text(f.file_reference_id)
                except FileNotFoundError:
                    file_content = f.content or "[Error: Content not found in blob store]"
            else:
                file_content = f.content
        else:
            name = f.name
            file_content = f.content
            
        if name is None or file_content is None:
            # Skip invalid files or handle error
            continue
            
        sections.append(
            f"--- FILE: {name} ---\n"
            f"{file_content}\n"
            f"--- END FILE: {name} ---"
        )

    return "\n\n".join(sections)


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

    # Add user message
    attachments = []
    if request.files:
        for f in request.files:
            ref_id = blob_store.save_text(f.content)
            attachments.append(Attachment(
                filename=f.name,
                content_type="text/plain", # Default
                file_reference_id=ref_id,
                size=f.size
            ))
            
    user_msg = UserMessageModel(
        content=request.content,
        files=attachments
    )
    conversation.messages.append(user_msg)
    
    prompt_content = build_prompt_content(request.content, attachments)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        conversation.title = title

    # Check for Follow-up (Target: Chairman)
    if request.target_model == "chairman":
        last_assistant_msg = None
        for msg in reversed(conversation.messages):
            if isinstance(msg, AssistantMessageModel) and msg.stage3:
                last_assistant_msg = msg
                break
        
        if last_assistant_msg:
            original_query = "Unknown (Context from previous turn)"
            try:
                idx = conversation.messages.index(last_assistant_msg)
                if idx > 0 and isinstance(conversation.messages[idx-1], UserMessageModel):
                    original_query = conversation.messages[idx-1].content or "Unknown"
            except ValueError:
                pass

            stage3_result = await chairman_followup(
                original_query=original_query,
                stage1_results=last_assistant_msg.stage1,
                stage2_results=last_assistant_msg.stage2,
                stage3_response=last_assistant_msg.stage3.get("response", ""),
                followup_query=prompt_content,
                llm_provider=llm_provider
            )

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

    # Run the 3-stage council process (Default)
    run_result = await run_full_council(
        prompt_content,
        llm_provider=llm_provider
    )

    # Add assistant message with all stages
    assistant_msg = AssistantMessageModel(
        stage1=run_result.stage1_results,
        stage2=run_result.stage2_results,
        stage3=run_result.stage3_result,
        metadata=run_result.metadata
    )
    conversation.messages.append(assistant_msg)
    conversation.has_unread = True
    conversation_repo.save(conversation)

    # Return the complete response with metadata
    return {
        "stage1": run_result.stage1_results,
        "stage2": run_result.stage2_results,
        "stage3": run_result.stage3_result,
        "metadata": run_result.metadata.model_dump()
    }


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
            # Add user message
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
            
            user_msg = UserMessageModel(
                content=request.content,
                files=attachments
            )
            conversation.messages.append(user_msg)
            prompt_content = build_prompt_content(request.content, attachments)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start', 'total': len(COUNCIL_MODELS)})}\n\n"
            
            # Using llm_provider for parallel calls
            responses = await llm_provider.chat_parallel(COUNCIL_MODELS, [{"role": "user", "content": prompt_content}])
            # For progress simulation, we could iterate but chat_parallel gathers them.
            # In Phase 4 we'll have better events.
            
            stage1_results = []
            for model in COUNCIL_MODELS:
                response = responses.get(model)
                if response is not None:
                    stage1_results.append(Stage1Result(
                        model=model,
                        response=response.get('content', ''),
                        status="success"
                    ))
                else:
                    stage1_results.append(Stage1Result(
                        model=model,
                        response="Error: Failed to get response from this model.",
                        status="error"
                    ))
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': [r.model_dump() for r in stage1_results]})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start', 'total': len(COUNCIL_MODELS)})}\n\n"
            
            stage2_results, label_to_model = await stage2_collect_rankings(
                prompt_content, 
                stage1_results, 
                llm_provider=llm_provider
            )
            
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': [r.model_dump() for r in stage2_results], 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': [r.model_dump() for r in aggregate_rankings]}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(
                prompt_content, 
                stage1_results, 
                stage2_results, 
                llm_provider=llm_provider
            )
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                conversation.title = title
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            assistant_msg = AssistantMessageModel(
                stage1=stage1_results,
                stage2=stage2_results,
                stage3=stage3_result,
                metadata=AssistantMetadata(
                    label_to_model=label_to_model,
                    aggregate_rankings=aggregate_rankings
                )
            )
            conversation.messages.append(assistant_msg)
            conversation.has_unread = True
            conversation_repo.save(conversation)

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

        except Exception as e:
            # Send error event
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"

        except Exception as e:
            # Send error event
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
