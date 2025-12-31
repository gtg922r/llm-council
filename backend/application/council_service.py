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
    CouncilRun,
    Attachment
)
from ..council import (
    calculate_aggregate_rankings, 
    generate_conversation_title,
    stage1_collect_responses,
    stage2_collect_rankings,
    stage3_synthesize_final,
    COUNCIL_MODELS
)

# We import build_prompt_content from local sibling
from ..application.prompt_builder import build_prompt_content

class CouncilEvent(BaseModel):
    type: str

class StageStarted(CouncilEvent):
    type: str = "stage_start"
    stage: int
    total: Optional[int] = None

class StageProgress(CouncilEvent):
    type: str = "stage_progress"
    stage: int
    completed: int
    total: int

class StageCompleted(CouncilEvent):
    type: str = "stage_complete"
    stage: int
    data: Any
    metadata: Optional[Dict[str, Any]] = None

class ModelThinking(CouncilEvent):
    type: str = "model_thinking"
    model: str

class TitleGenerated(CouncilEvent):
    type: str = "title_complete"
    title: str

class RunCompleted(CouncilEvent):
    type: str = "complete"

class CouncilOrchestrator:
    """Service to orchestrate the multi-stage LLM Council process."""
    
    def __init__(self, llm_provider: LLMProvider, conversation_repo: ConversationRepository, blob_store: Optional[BlobStore] = None):
        self.llm_provider = llm_provider
        self.repo = conversation_repo
        self.blob_store = blob_store or BlobStore()
        
    async def run_council(
        self, 
        conversation_id: str, 
        user_query: str,
        attachments: List[Attachment] = None,
        is_first_message: bool = False
    ) -> AsyncGenerator[Union[StageStarted, StageProgress, StageCompleted, TitleGenerated, RunCompleted], None]:
        """
        Run the full 3-stage council process and yield domain events.
        """
        # Build full prompt content (including files)
        prompt_content = build_prompt_content(user_query, attachments or [], blob_store=self.blob_store)

        # 1. Title Generation (in parallel if first message)
        title_task = None
        if is_first_message:
            title_task = asyncio.create_task(generate_conversation_title(user_query))
            
        # Stage 1
        yield StageStarted(stage=1, total=len(COUNCIL_MODELS))
        stage1_results = await stage1_collect_responses(prompt_content, llm_provider=self.llm_provider)
        yield StageCompleted(stage=1, data=[r.model_dump() for r in stage1_results])
        
        # Stage 2
        yield StageStarted(stage=2, total=len(COUNCIL_MODELS))
        stage2_results, label_to_model = await stage2_collect_rankings(
            prompt_content, 
            stage1_results, 
            llm_provider=self.llm_provider
        )
        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": [r.model_dump() for r in aggregate_rankings]
        }
        yield StageCompleted(stage=2, data=[r.model_dump() for r in stage2_results], metadata=metadata)
        
        # Stage 3
        yield StageStarted(stage=3)
        stage3_result = await stage3_synthesize_final(
            prompt_content,
            stage1_results,
            stage2_results,
            llm_provider=self.llm_provider
        )
        yield StageCompleted(stage=3, data=stage3_result)
        
        # Title handling
        if title_task:
            title = await title_task
            conv = self.repo.get(conversation_id)
            if conv:
                conv.title = title
                self.repo.save(conv)
            yield TitleGenerated(title=title)
            
        # Save final assistant message
        conv = self.repo.get(conversation_id)
        if conv:
            assistant_msg = AssistantMessage(
                stage1=stage1_results,
                stage2=stage2_results,
                stage3=stage3_result,
                metadata=AssistantMetadata(
                    label_to_model=label_to_model,
                    aggregate_rankings=aggregate_rankings
                )
            )
            conv.messages.append(assistant_msg)
            conv.has_unread = True
            self.repo.save(conv)
            
        yield RunCompleted()
