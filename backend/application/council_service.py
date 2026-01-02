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
            
        # --- Stage 1 ---
        yield StageStarted(stage=1, total=len(COUNCIL_MODELS))
        
        stage1_messages = [{"role": "user", "content": prompt_content}]
        stage1_responses = {}
        completed_count = 0

        async def wrap_task(model, task):
            return model, await task

        stage1_wrapped = [
            wrap_task(model, self.llm_provider.chat(model, stage1_messages))
            for model in COUNCIL_MODELS
        ]
        
        for task in asyncio.as_completed(stage1_wrapped):
            model, response = await task
            stage1_responses[model] = response
            completed_count += 1
            yield StageProgress(stage=1, completed=completed_count, total=len(COUNCIL_MODELS))

        stage1_results = []
        for model in COUNCIL_MODELS:
            response = stage1_responses.get(model)
            if response:
                stage1_results.append(Stage1Result(model=model, response=response.get('content', ''), status="success"))
            else:
                stage1_results.append(Stage1Result(model=model, response="Error", status="error"))
        
        yield StageCompleted(stage=1, data=[r.model_dump() for r in stage1_results])
        self._update_saved_message(conversation_id, stage1=stage1_results)
        
        # --- Stage 2 ---
        yield StageStarted(stage=2, total=len(COUNCIL_MODELS))
        
        # We need the logic from stage2_collect_rankings but with progress
        # For simplicity and to avoid duplicating too much logic, 
        # we'll keep the prompt building in council.py but do the loop here.
        # But wait, stage2_collect_rankings builds the prompt based on stage1_results.
        
        # Create anonymized labels
        successful_results = [r for r in stage1_results if r.status == "success"]
        labels = [chr(65 + i) for i in range(len(successful_results))]
        label_to_model = {f"Response {label}": result.model for label, result in zip(labels, successful_results)}
        responses_text = "\n\n".join([f"Response {label}:\n{result.response}" for label, result in zip(labels, successful_results)])
        
        ranking_prompt = f"Original Question: {prompt_content}\n\n{responses_text}\n\nProvide rankings..." # Simplified for brevity, usually we'd use the real prompt
        # Actually, let's use the real prompt builder logic if possible or just import it.
        # To be safe, I'll just call the parallel provider directly.
        
        # Since I want to use the exact same prompt from council.py:
        from ..council import stage2_collect_rankings
        # We'll mock the provider to just give us the prompt? No, that's complex.
        # I'll just copy the prompt string or use a helper.
        
        # Actually, let's just use the real implementation but wrap it.
        # But stage2_collect_rankings currently does the whole parallel call.
        
        # REFACTORED APPROACH: Update CouncilOrchestrator to handle the loop.
        # I'll copy the ranking prompt from council.py
        
        ranking_prompt = f"""You are evaluating different responses to the following question:

Question: {prompt_content}

Here are the responses from different models (anonymized):

{responses_text}

Your task:
1. First, evaluate each response individually. For each response, explain what it does well and what it does poorly.
2. Then, at the very end of your response, provide a final ranking.

IMPORTANT: Your final ranking MUST be formatted EXACTLY as follows:
- Start with the line "FINAL RANKING:" (all caps, with colon)
- Then list the responses from best to worst as a numbered list
- Each line should be: number, period, space, then ONLY the response label (e.g., "1. Response A")
- Do not add any other text or explanations in the ranking section

Now provide your evaluation and ranking:"""

        stage2_messages = [{"role": "user", "content": ranking_prompt}]
        stage2_wrapped = [
            wrap_task(model, self.llm_provider.chat(model, stage2_messages))
            for model in COUNCIL_MODELS
        ]
        
        stage2_responses = {}
        completed_count = 0
        for task in asyncio.as_completed(stage2_wrapped):
            model, response = await task
            stage2_responses[model] = response
            completed_count += 1
            yield StageProgress(stage=2, completed=completed_count, total=len(COUNCIL_MODELS))

        stage2_results = []
        from ..council import parse_ranking_from_text
        for model in COUNCIL_MODELS:
            response = stage2_responses.get(model)
            if response:
                full_text = response.get('content', '')
                stage2_results.append(Stage2Result(
                    model=model, 
                    ranking=full_text, 
                    parsed_ranking=parse_ranking_from_text(full_text), 
                    status="success"
                ))
            else:
                stage2_results.append(Stage2Result(model=model, ranking="Error", parsed_ranking=[], status="error"))

        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        metadata = {
            "label_to_model": label_to_model,
            "aggregate_rankings": [r.model_dump() for r in aggregate_rankings]
        }
        yield StageCompleted(stage=2, data=[r.model_dump() for r in stage2_results], metadata=metadata)
        self._update_saved_message(
            conversation_id, 
            stage2=stage2_results, 
            metadata=AssistantMetadata(label_to_model=label_to_model, aggregate_rankings=aggregate_rankings)
        )
        
        # --- Stage 3 ---
        yield StageStarted(stage=3)
        stage3_result = await stage3_synthesize_final(
            prompt_content,
            stage1_results,
            stage2_results,
            llm_provider=self.llm_provider
        )
        yield StageCompleted(stage=3, data=stage3_result)
        self._update_saved_message(conversation_id, stage3=stage3_result)
        
        # Title handling
        if title_task:
            title = await title_task
            conv = self.repo.get(conversation_id)
            if conv:
                conv.title = title
                self.repo.save(conv)
            yield TitleGenerated(title=title)
            
        yield RunCompleted()

    def _update_saved_message(
        self, 
        conversation_id: str, 
        stage1=None, 
        stage2=None, 
        stage3=None, 
        metadata=None
    ):
        """Helper to update or create the assistant message in the repository."""
        conv = self.repo.get(conversation_id)
        if not conv:
            return

        # Find the last assistant message or create one
        assistant_msg = None
        if conv.messages and isinstance(conv.messages[-1], AssistantMessage):
            assistant_msg = conv.messages[-1]
        else:
            assistant_msg = AssistantMessage()
            conv.messages.append(assistant_msg)

        if stage1 is not None: assistant_msg.stage1 = stage1
        if stage2 is not None: assistant_msg.stage2 = stage2
        if stage3 is not None: assistant_msg.stage3 = stage3
        if metadata is not None: assistant_msg.metadata = metadata

        conv.has_unread = True
        self.repo.save(conv)
