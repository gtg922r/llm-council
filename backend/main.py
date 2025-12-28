"""FastAPI backend for LLM Council."""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Dict, Any
import uuid
import json
import asyncio

from . import storage
from . import config
from .council import (
    run_full_council,
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    calculate_aggregate_rankings,
    chairman_followup
)

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


class SendMessageRequest(BaseModel):
    """Request to send a message in a conversation."""
    content: str
    target_model: str | None = None # e.g., "chairman" for follow-up


class ConversationMetadata(BaseModel):
    """Conversation metadata for list view."""
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    message_count: int


class Conversation(BaseModel):
    """Full conversation with all messages."""
    id: str
    created_at: str
    title: str
    is_pinned: bool = False
    is_archived: bool = False
    messages: List[Dict[str, Any]]


class UpdateConversationRequest(BaseModel):
    """Request to update conversation flags."""
    title: str | None = None
    is_pinned: bool | None = None
    is_archived: bool | None = None


@app.get("/")
async def root():
    """Health check endpoint."""
    return {"status": "ok", "service": "LLM Council API"}


@app.get("/api/conversations", response_model=List[ConversationMetadata])
async def list_conversations():
    """List all conversations (metadata only)."""
    return storage.list_conversations()


@app.post("/api/conversations", response_model=Conversation)
async def create_conversation(request: CreateConversationRequest):
    """Create a new conversation."""
    conversation_id = str(uuid.uuid4())
    conversation = storage.create_conversation(conversation_id)
    return conversation


@app.get("/api/conversations/{conversation_id}", response_model=Conversation)
async def get_conversation(conversation_id: str):
    """Get a specific conversation with all its messages."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return conversation


@app.patch("/api/conversations/{conversation_id}", response_model=Conversation)
async def update_conversation(conversation_id: str, request: UpdateConversationRequest):
    """Update conversation metadata (title, pinned, archived)."""
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    if request.title is not None:
        conversation["title"] = request.title
    if request.is_pinned is not None:
        conversation["is_pinned"] = request.is_pinned
    if request.is_archived is not None:
        conversation["is_archived"] = request.is_archived
        
    storage.save_conversation(conversation)
    return conversation


@app.delete("/api/conversations/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """Permanently delete a conversation."""
    storage.delete_conversation(conversation_id)
    return {"status": "success"}


@app.post("/api/conversations/{conversation_id}/duplicate", response_model=Conversation)
async def duplicate_conversation(conversation_id: str):
    """Duplicate a conversation."""
    new_id = str(uuid.uuid4())
    try:
        new_conv = storage.duplicate_conversation(conversation_id, new_id)
        return new_conv
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@app.post("/api/conversations/{conversation_id}/message")
async def send_message(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and run the 3-stage council process.
    Returns the complete response with all stages.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    # Add user message
    storage.add_user_message(conversation_id, request.content)

    # If this is the first message, generate a title
    if is_first_message:
        title = await generate_conversation_title(request.content)
        storage.update_conversation_title(conversation_id, title)

    # Check for Follow-up (Target: Chairman)
    if request.target_model == "chairman":
        # We need to find the previous context.
        # Logic: Look for the last assistant message that has Stage 1/2/3 results.
        # Iterate backwards through messages
        last_assistant_msg = None
        for msg in reversed(conversation["messages"]):
            if msg["role"] == "assistant" and "stage3" in msg:
                last_assistant_msg = msg
                break
        
        if last_assistant_msg:
            # We found context
            # Call chairman_followup
            # Note: We need the original query too. Ideally, it's the user message immediately preceding the assistant message.
            # But finding that might be tricky if there are multiple user messages.
            # Let's assume the user message *before* the last assistant message is the original query.
            # Or we can just pass "Previous Context" as the query if strictly following the function signature?
            # The function expects 'original_query'.
            # Let's try to find it.
            
            # Simplified approach: Use the "stage3" response as the base.
            # The 'original_query' is less critical if we have the full stage1/2 text which includes the query usually?
            # Actually, `chairman_followup` uses `original_query` in the prompt.
            # We can try to extract it from the message history if we really want to be precise, 
            # but for now, let's look for the user message before the last_assistant_msg.
            
            # This is a bit complex to find efficiently in a simple list without IDs/links.
            # We'll use a placeholder or try to find it.
            original_query = "Unknown (Context from previous turn)"
            # A better way might be to look at `last_assistant_msg` index - 1
            try:
                idx = conversation["messages"].index(last_assistant_msg)
                if idx > 0 and conversation["messages"][idx-1]["role"] == "user":
                    original_query = conversation["messages"][idx-1]["content"]
            except ValueError:
                pass

            stage3_result = await chairman_followup(
                original_query=original_query,
                stage1_results=last_assistant_msg.get("stage1", []),
                stage2_results=last_assistant_msg.get("stage2", []),
                stage3_response=last_assistant_msg.get("stage3", {}).get("response", ""),
                followup_query=request.content
            )

            # Store result
            # For a follow-up, Stage 1 and Stage 2 are empty/skipped.
            storage.add_assistant_message(
                conversation_id,
                stage1=[],
                stage2=[],
                stage3=stage3_result
            )

            return {
                "stage1": [],
                "stage2": [],
                "stage3": stage3_result,
                "metadata": {}
            }
        else:
            # Fallback if no context found? Just run full council?
            # Or raise error?
            # Let's run full council as fallback but maybe log it?
            pass

    # Run the 3-stage council process (Default)
    stage1_results, stage2_results, stage3_result, metadata = await run_full_council(
        request.content
    )

    # Add assistant message with all stages
    storage.add_assistant_message(
        conversation_id,
        stage1_results,
        stage2_results,
        stage3_result
    )

    # Return the complete response with metadata
    return {
        "stage1": stage1_results,
        "stage2": stage2_results,
        "stage3": stage3_result,
        "metadata": metadata
    }


@app.post("/api/conversations/{conversation_id}/message/stream")
async def send_message_stream(conversation_id: str, request: SendMessageRequest):
    """
    Send a message and stream the 3-stage council process.
    Returns Server-Sent Events as each stage completes.
    """
    # Check if conversation exists
    conversation = storage.get_conversation(conversation_id)
    if conversation is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Check if this is the first message
    is_first_message = len(conversation["messages"]) == 0

    async def event_generator():
        try:
            # Add user message
            storage.add_user_message(conversation_id, request.content)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                title_task = asyncio.create_task(generate_conversation_title(request.content))

            # Stage 1: Collect responses
            yield f"data: {json.dumps({'type': 'stage1_start'})}\n\n"
            stage1_results = await stage1_collect_responses(request.content)
            yield f"data: {json.dumps({'type': 'stage1_complete', 'data': stage1_results})}\n\n"

            # Stage 2: Collect rankings
            yield f"data: {json.dumps({'type': 'stage2_start'})}\n\n"
            stage2_results, label_to_model = await stage2_collect_rankings(request.content, stage1_results)
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            yield f"data: {json.dumps({'type': 'stage2_complete', 'data': stage2_results, 'metadata': {'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}})}\n\n"

            # Stage 3: Synthesize final answer
            yield f"data: {json.dumps({'type': 'stage3_start'})}\n\n"
            stage3_result = await stage3_synthesize_final(request.content, stage1_results, stage2_results)
            yield f"data: {json.dumps({'type': 'stage3_complete', 'data': stage3_result})}\n\n"

            # Wait for title generation if it was started
            if title_task:
                title = await title_task
                storage.update_conversation_title(conversation_id, title)
                yield f"data: {json.dumps({'type': 'title_complete', 'data': {'title': title}})}\n\n"

            # Save complete assistant message
            storage.add_assistant_message(
                conversation_id,
                stage1_results,
                stage2_results,
                stage3_result
            )

            # Send completion event
            yield f"data: {json.dumps({'type': 'complete'})}\n\n"

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
