"""Council Orchestrator - the single source of truth for council workflow.

This module contains the CouncilOrchestrator which coordinates all stages
of the LLM Council process. It uses dependency injection for all external
interactions (LLM calls, storage) making it fully testable.
"""

import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from pydantic import BaseModel

from ..ports import LLMProvider, ConversationRepository
from ..infrastructure.blob_store import BlobStore
from ..domain.models import (
    Conversation, 
    UserMessage, 
    AssistantMessage, 
    AssistantMetadata,
    Stage1Result,
    Stage2Result,
    Attachment
)
from ..domain.council_logic import parse_ranking_from_text, calculate_aggregate_rankings
from .prompts import (
    build_ranking_prompt,
    build_chairman_synthesis_prompt,
    build_chairman_followup_prompt,
    build_title_generation_prompt,
    create_label_to_model_mapping
)
from .prompt_builder import build_prompt_content
from ..config import COUNCIL_MODELS, CHAIRMAN_MODEL, get_models_for_mode


# Domain Events
class CouncilEvent(BaseModel):
    """Base class for council events."""
    type: str


class StageStarted(CouncilEvent):
    """Emitted when a stage begins."""
    type: str = "stage_start"
    stage: int
    total: Optional[int] = None


class StageProgress(CouncilEvent):
    """Emitted as models complete within a stage."""
    type: str = "stage_progress"
    stage: int
    completed: int
    total: int


class StageCompleted(CouncilEvent):
    """Emitted when a stage completes with its results."""
    type: str = "stage_complete"
    stage: int
    data: Any
    metadata: Optional[Dict[str, Any]] = None


class ModelThinking(CouncilEvent):
    """Emitted when a specific model is processing."""
    type: str = "model_thinking"
    model: str


class TitleGenerated(CouncilEvent):
    """Emitted when conversation title is generated."""
    type: str = "title_complete"
    title: str


class RunCompleted(CouncilEvent):
    """Emitted when the full council run is complete."""
    type: str = "complete"


class CouncilOrchestrator:
    """
    Service to orchestrate the multi-stage LLM Council process.
    
    This is the single source of truth for all council workflow logic.
    All LLM interactions go through the injected LLMProvider.
    All storage interactions go through the injected ConversationRepository.
    """
    
    # Model used for title generation (fast/cheap model)
    TITLE_MODEL = "google/gemini-2.5-flash"
    
    def __init__(
        self, 
        llm_provider: LLMProvider, 
        conversation_repo: ConversationRepository, 
        blob_store: Optional[BlobStore] = None
    ):
        self.llm_provider = llm_provider
        self.repo = conversation_repo
        self.blob_store = blob_store or BlobStore()
        
    async def run_council(
        self, 
        conversation_id: str, 
        user_query: str,
        attachments: Optional[List[Attachment]] = None,
        is_first_message: bool = False,
        model_mode: str = "smart",
        user_id: str = ""
    ) -> AsyncGenerator[Union[StageStarted, StageProgress, StageCompleted, TitleGenerated, RunCompleted], None]:
        """
        Run the full 3-stage council process and yield domain events.
        
        Args:
            conversation_id: ID of the conversation
            user_query: The user's query text
            attachments: Optional list of file attachments
            is_first_message: Whether this is the first message (triggers title generation)
            model_mode: Either 'fast' or 'smart' to select model tier
            user_id: The authenticated user's ID for data isolation
            
        Yields:
            Domain events as each stage progresses and completes
        """
        # Get models based on mode
        council_models, chairman_model = get_models_for_mode(model_mode)
        
        # Build full prompt content (including files)
        prompt_content = build_prompt_content(
            user_query, 
            attachments or [], 
            blob_store=self.blob_store
        )

        # Start title generation in parallel if first message
        title_task = None
        if is_first_message:
            title_task = asyncio.create_task(
                self._generate_title(user_query)
            )
            
        # --- Stage 1: Collect Individual Responses ---
        yield StageStarted(stage=1, total=len(council_models))
        
        # Run stage 1 with progress updates
        messages = [{"role": "user", "content": prompt_content}]
        stage1_responses = {}
        completed = 0
        
        # Create tasks with model tracking
        async def run_model_task(model):
            return model, await self.llm_provider.chat(model, messages)
        
        tasks = [run_model_task(model) for model in council_models]
        
        for coro in asyncio.as_completed(tasks):
            model, response = await coro
            stage1_responses[model] = response
            completed += 1
            yield StageProgress(stage=1, completed=completed, total=len(council_models))
        
        # Format results
        stage1_results = []
        for model in council_models:
            response = stage1_responses.get(model)
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
        
        yield StageCompleted(
            stage=1, 
            data=[r.model_dump() for r in stage1_results]
        )
        self._update_saved_message(conversation_id, user_id, stage1=stage1_results)
        
        # Check if we have any successful responses
        successful_stage1 = [r for r in stage1_results if r.status == "success"]
        if not successful_stage1:
            # All models failed - return error in stage 3
            error_result = {
                "model": "error",
                "response": "All models failed to respond. Please try again."
            }
            yield StageCompleted(stage=2, data=[], metadata={})
            yield StageCompleted(stage=3, data=error_result)
            yield RunCompleted()
            return
        
        # --- Stage 2: Collect Rankings ---
        yield StageStarted(stage=2, total=len(council_models))
        
        # Create label mapping
        label_to_model = create_label_to_model_mapping(stage1_results)
        
        # Build ranking prompt
        ranking_prompt = build_ranking_prompt(prompt_content, stage1_results)
        ranking_messages = [{"role": "user", "content": ranking_prompt}]
        
        # Run stage 2 with progress updates
        stage2_responses = {}
        completed = 0
        
        async def run_ranking_task(model):
            return model, await self.llm_provider.chat(model, ranking_messages)
        
        ranking_tasks = [run_ranking_task(model) for model in council_models]
        
        for coro in asyncio.as_completed(ranking_tasks):
            model, response = await coro
            stage2_responses[model] = response
            completed += 1
            yield StageProgress(stage=2, completed=completed, total=len(council_models))
        
        # Format results
        stage2_results = []
        for model in council_models:
            response = stage2_responses.get(model)
            if response is not None:
                full_text = response.get('content', '')
                stage2_results.append(Stage2Result(
                    model=model,
                    ranking=full_text,
                    parsed_ranking=parse_ranking_from_text(full_text),
                    status="success"
                ))
            else:
                stage2_results.append(Stage2Result(
                    model=model,
                    ranking="Error: Failed to get ranking from this model.",
                    parsed_ranking=[],
                    status="error"
                ))
        
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": [r.model_dump() for r in aggregate_rankings]
        }
        
        yield StageCompleted(
            stage=2, 
            data=[r.model_dump() for r in stage2_results], 
            metadata=metadata
        )
        self._update_saved_message(
            conversation_id, 
            user_id,
            stage2=stage2_results, 
            metadata=AssistantMetadata(
                label_to_model=label_to_model, 
                aggregate_rankings=aggregate_rankings
            )
        )
        
        # --- Stage 3: Chairman Synthesis ---
        yield StageStarted(stage=3)
        stage3_result = await self._run_stage3(
            prompt_content,
            stage1_results,
            stage2_results,
            chairman_model=chairman_model
        )
        
        yield StageCompleted(stage=3, data=stage3_result)
        self._update_saved_message(conversation_id, user_id, stage3=stage3_result)
        
        # Handle title generation result
        if title_task:
            title = await title_task
            conv = self.repo.get(conversation_id, user_id)
            if conv:
                conv.title = title
                self.repo.save(conv, user_id)
            yield TitleGenerated(title=title)
            
        yield RunCompleted()

    async def chairman_followup(
        self,
        conversation_id: str,
        followup_query: str,
        attachments: Optional[List[Attachment]] = None,
        model_mode: str = "smart",
        user_id: str = ""
    ) -> Dict[str, Any]:
        """
        Handle a follow-up question to the Chairman.
        
        Args:
            conversation_id: ID of the conversation
            followup_query: The user's follow-up question
            attachments: Optional list of file attachments
            model_mode: Either 'fast' or 'smart' to select model tier
            
        Returns:
            Dict with 'model' and 'response' keys
        """
        _, chairman_model = get_models_for_mode(model_mode)
        
        conversation = self.repo.get(conversation_id, user_id)
        if not conversation:
            return {
                "model": chairman_model,
                "response": "Error: Conversation not found."
            }
        
        # Find the last assistant message with a stage3 response
        last_assistant_msg = None
        for msg in reversed(conversation.messages):
            if isinstance(msg, AssistantMessage) and msg.stage3:
                last_assistant_msg = msg
                break
        
        if not last_assistant_msg:
            return {
                "model": chairman_model,
                "response": "Error: No previous council response found for follow-up."
            }
        
        # Find the original query
        original_query = "Unknown (Context from previous turn)"
        try:
            idx = conversation.messages.index(last_assistant_msg)
            if idx > 0 and isinstance(conversation.messages[idx - 1], UserMessage):
                original_query = conversation.messages[idx - 1].content or "Unknown"
        except ValueError:
            pass
        
        # Build prompt content with attachments
        prompt_content = build_prompt_content(
            followup_query, 
            attachments or [], 
            blob_store=self.blob_store
        )
        
        # Build the followup prompt
        chairman_prompt = build_chairman_followup_prompt(
            original_query=original_query,
            stage1_results=last_assistant_msg.stage1,
            stage2_results=last_assistant_msg.stage2,
            stage3_response=last_assistant_msg.stage3.get("response", ""),
            followup_query=prompt_content
        )
        
        messages = [{"role": "user", "content": chairman_prompt}]
        response = await self.llm_provider.chat(chairman_model, messages)
        
        if response is None:
            return {
                "model": chairman_model,
                "response": "Error: Unable to generate follow-up response."
            }
        
        return {
            "model": chairman_model,
            "response": response.get('content', '')
        }

    async def _run_stage1(self, prompt_content: str) -> List[Stage1Result]:
        """
        Stage 1: Collect individual responses from all council models.
        """
        messages = [{"role": "user", "content": prompt_content}]
        
        # Query all models in parallel
        tasks = [
            self.llm_provider.chat(model, messages)
            for model in COUNCIL_MODELS
        ]
        results = await asyncio.gather(*tasks)
        responses = dict(zip(COUNCIL_MODELS, results))
        
        # Format results
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
        
        return stage1_results

    async def _run_stage2(
        self, 
        prompt_content: str, 
        stage1_results: List[Stage1Result]
    ) -> tuple[List[Stage2Result], Dict[str, str]]:
        """
        Stage 2: Collect rankings from all council models.
        """
        # Create label mapping
        label_to_model = create_label_to_model_mapping(stage1_results)
        
        # Build ranking prompt
        ranking_prompt = build_ranking_prompt(prompt_content, stage1_results)
        messages = [{"role": "user", "content": ranking_prompt}]
        
        # Query all models in parallel
        tasks = [
            self.llm_provider.chat(model, messages)
            for model in COUNCIL_MODELS
        ]
        results = await asyncio.gather(*tasks)
        responses = dict(zip(COUNCIL_MODELS, results))
        
        # Format results
        stage2_results = []
        for model in COUNCIL_MODELS:
            response = responses.get(model)
            if response is not None:
                full_text = response.get('content', '')
                stage2_results.append(Stage2Result(
                    model=model,
                    ranking=full_text,
                    parsed_ranking=parse_ranking_from_text(full_text),
                    status="success"
                ))
            else:
                stage2_results.append(Stage2Result(
                    model=model,
                    ranking="Error: Failed to get ranking from this model.",
                    parsed_ranking=[],
                    status="error"
                ))
        
        return stage2_results, label_to_model

    async def _run_stage3(
        self,
        prompt_content: str,
        stage1_results: List[Stage1Result],
        stage2_results: List[Stage2Result],
        chairman_model: str = CHAIRMAN_MODEL
    ) -> Dict[str, Any]:
        """
        Stage 3: Chairman synthesizes final response.
        """
        chairman_prompt = build_chairman_synthesis_prompt(
            prompt_content,
            stage1_results,
            stage2_results
        )
        
        messages = [{"role": "user", "content": chairman_prompt}]
        response = await self.llm_provider.chat(chairman_model, messages)
        
        if response is None:
            return {
                "model": chairman_model,
                "response": "Error: Unable to generate final synthesis."
            }
        
        return {
            "model": chairman_model,
            "response": response.get('content', '')
        }

    async def _generate_title(self, user_query: str) -> str:
        """
        Generate a short title for a conversation based on the first user message.
        """
        prompt = build_title_generation_prompt(user_query)
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.llm_provider.chat(
            self.TITLE_MODEL, 
            messages,
            timeout=30.0
        )
        
        if response is None:
            return "New Conversation"
        
        title = response.get('content', 'New Conversation').strip()
        
        # Clean up the title - remove quotes, limit length
        title = title.strip('"\'')
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title

    def _update_saved_message(
        self, 
        conversation_id: str,
        user_id: str,
        stage1: Optional[List[Stage1Result]] = None, 
        stage2: Optional[List[Stage2Result]] = None, 
        stage3: Optional[Dict[str, Any]] = None, 
        metadata: Optional[AssistantMetadata] = None
    ) -> None:
        """Helper to update or create the assistant message in the repository."""
        conv = self.repo.get(conversation_id, user_id)
        if not conv:
            return

        # Find the last assistant message or create one
        assistant_msg = None
        if conv.messages and isinstance(conv.messages[-1], AssistantMessage):
            assistant_msg = conv.messages[-1]
        else:
            assistant_msg = AssistantMessage()
            conv.messages.append(assistant_msg)

        if stage1 is not None:
            assistant_msg.stage1 = stage1
        if stage2 is not None:
            assistant_msg.stage2 = stage2
        if stage3 is not None:
            assistant_msg.stage3 = stage3
        if metadata is not None:
            assistant_msg.metadata = metadata

        conv.has_unread = True
        self.repo.save(conv, user_id)
