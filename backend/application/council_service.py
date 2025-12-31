"""Council Service - orchestrates the multi-stage council workflow.

This service encapsulates all business logic for running the LLM Council,
providing an event-driven interface that can be consumed by both streaming
and non-streaming API endpoints.
"""

import asyncio
import re
from collections import defaultdict
from typing import List, Dict, Any, AsyncIterator, Optional

from ..ports import LLMProvider, BlobStorePort
from ..domain.models import (
    Stage1Result,
    Stage2Result,
    Stage3Result,
    CouncilMetadata,
    AggregateRanking,
    CouncilEvent,
    Stage1Started,
    Stage1Progress,
    Stage1Complete,
    Stage2Started,
    Stage2Progress,
    Stage2Complete,
    Stage3Started,
    Stage3Complete,
    TitleGenerated,
    CouncilComplete,
    CouncilError,
    FileReference,
)
from ..config import COUNCIL_MODELS, CHAIRMAN_MODEL


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """Parse the FINAL RANKING section from the model's response.
    
    Args:
        ranking_text: The full text response from the model
        
    Returns:
        List of response labels in ranked order (e.g., ["Response A", "Response C", "Response B"])
    """
    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                return [re.search(r'Response [A-Z]', m).group() for m in numbered_matches]
            
            # Fallback: Extract all "Response X" patterns in order
            matches = re.findall(r'Response [A-Z]', ranking_section)
            return matches
    
    # Fallback: try to find any "Response X" patterns in order
    matches = re.findall(r'Response [A-Z]', ranking_text)
    return matches


def calculate_aggregate_rankings(
    stage2_results: List[Stage2Result],
    label_to_model: Dict[str, str]
) -> List[AggregateRanking]:
    """Calculate aggregate rankings across all models.
    
    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names
        
    Returns:
        List of AggregateRanking sorted best to worst
    """
    model_positions = defaultdict(list)
    
    for ranking in stage2_results:
        parsed_ranking = parse_ranking_from_text(ranking.ranking)
        
        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)
    
    aggregate = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append(AggregateRanking(
                model=model,
                average_rank=round(avg_rank, 2),
                rankings_count=len(positions)
            ))
    
    # Sort by average rank (lower is better)
    aggregate.sort(key=lambda x: x.average_rank)
    
    return aggregate


def build_prompt_content(
    content: str,
    files: List[FileReference],
    blob_store: Optional[BlobStorePort]
) -> str:
    """Build the full prompt including file content.
    
    Args:
        content: User message content
        files: List of file references
        blob_store: Blob store for retrieving file content
        
    Returns:
        Complete prompt string with embedded file content
    """
    if not files or not blob_store:
        return content
    
    sections = [content]
    for file_ref in files:
        file_content = blob_store.get_text(file_ref.blob_id)
        if file_content:
            sections.append(
                f"--- FILE: {file_ref.name} ---\n"
                f"{file_content}\n"
                f"--- END FILE: {file_ref.name} ---"
            )
    
    return "\n\n".join(sections)


class CouncilService:
    """Service that orchestrates the multi-stage LLM Council workflow."""
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        blob_store: Optional[BlobStorePort] = None,
        council_models: List[str] = None,
        chairman_model: str = None
    ):
        self.llm = llm_provider
        self.blob_store = blob_store
        self.council_models = council_models or COUNCIL_MODELS
        self.chairman_model = chairman_model or CHAIRMAN_MODEL
    
    async def _query_with_model(
        self,
        model: str,
        messages: List[Dict[str, str]]
    ) -> tuple[str, Optional[Dict[str, Any]]]:
        """Query a model and return (model, response) tuple."""
        try:
            response = await self.llm.chat(model, messages)
            return model, response
        except Exception as e:
            print(f"Exception raised while querying model {model}: {e}")
            return model, None
    
    async def run_council(
        self,
        prompt: str,
        generate_title: bool = False,
        files: Optional[List[FileReference]] = None
    ) -> AsyncIterator[CouncilEvent]:
        """Run the full council workflow, yielding events for each step.
        
        This is an async generator that yields domain events as the council
        progresses through stages. Consumers can handle these events for
        streaming UI updates or wait for completion.
        
        Args:
            prompt: The user's query
            generate_title: Whether to generate a title for this conversation
            files: Optional file references attached to the message
            
        Yields:
            Domain events for each stage of the council process
        """
        try:
            # Build full prompt with file content if present
            full_prompt = prompt
            if files and self.blob_store:
                full_prompt = build_prompt_content(prompt, files, self.blob_store)
            
            # Start title generation in background if requested
            title_task = None
            if generate_title:
                title_task = asyncio.create_task(self._generate_title(prompt))
            
            # Stage 1: Collect individual responses
            yield Stage1Started(total=len(self.council_models))
            
            stage1_messages = [{"role": "user", "content": full_prompt}]
            stage1_tasks = [
                asyncio.create_task(self._query_with_model(model, stage1_messages))
                for model in self.council_models
            ]
            
            stage1_responses = {}
            completed = 0
            for task in asyncio.as_completed(stage1_tasks):
                model, response = await task
                stage1_responses[model] = response
                completed += 1
                yield Stage1Progress(completed=completed, total=len(self.council_models))
            
            # Build Stage 1 results
            stage1_results = []
            for model in self.council_models:
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
            
            yield Stage1Complete(data=stage1_results)
            
            # Check for total failure
            successful_results = [r for r in stage1_results if r.status == "success"]
            if not successful_results:
                yield CouncilError(message="All models failed to respond.")
                return
            
            # Stage 2: Collect rankings
            yield Stage2Started(total=len(self.council_models))
            
            # Build anonymized responses
            labels = [chr(65 + i) for i in range(len(successful_results))]
            label_to_model = {
                f"Response {label}": result.model
                for label, result in zip(labels, successful_results)
            }
            
            responses_text = "\n\n".join([
                f"Response {label}:\n{result.response}"
                for label, result in zip(labels, successful_results)
            ])
            
            ranking_prompt = self._build_ranking_prompt(full_prompt, responses_text)
            stage2_messages = [{"role": "user", "content": ranking_prompt}]
            
            stage2_tasks = [
                asyncio.create_task(self._query_with_model(model, stage2_messages))
                for model in self.council_models
            ]
            
            stage2_responses = {}
            completed = 0
            for task in asyncio.as_completed(stage2_tasks):
                model, response = await task
                stage2_responses[model] = response
                completed += 1
                yield Stage2Progress(completed=completed, total=len(self.council_models))
            
            # Build Stage 2 results
            stage2_results = []
            for model in self.council_models:
                response = stage2_responses.get(model)
                if response is not None:
                    full_text = response.get('content', '')
                    parsed = parse_ranking_from_text(full_text)
                    stage2_results.append(Stage2Result(
                        model=model,
                        ranking=full_text,
                        parsed_ranking=parsed,
                        status="success"
                    ))
                else:
                    stage2_results.append(Stage2Result(
                        model=model,
                        ranking="Error: Failed to get ranking from this model.",
                        parsed_ranking=[],
                        status="error"
                    ))
            
            # Calculate aggregate rankings
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            
            metadata = CouncilMetadata(
                label_to_model=label_to_model,
                aggregate_rankings=aggregate_rankings
            )
            
            yield Stage2Complete(data=stage2_results, metadata=metadata)
            
            # Stage 3: Chairman synthesis
            yield Stage3Started()
            
            stage3_result = await self._stage3_synthesize(full_prompt, stage1_results, stage2_results)
            
            yield Stage3Complete(data=stage3_result)
            
            # Handle title generation
            if title_task:
                title = await title_task
                yield TitleGenerated(title=title)
            
            yield CouncilComplete()
            
        except Exception as e:
            yield CouncilError(message=str(e))
    
    async def run_followup(
        self,
        original_query: str,
        stage1_results: List[Stage1Result],
        stage2_results: List[Stage2Result],
        stage3_response: str,
        followup_query: str
    ) -> Stage3Result:
        """Handle a follow-up question to the Chairman.
        
        Args:
            original_query: The initial user question
            stage1_results: Results from Stage 1
            stage2_results: Rankings from Stage 2
            stage3_response: The Chairman's initial response
            followup_query: The user's follow-up question
            
        Returns:
            Stage3Result with the Chairman's follow-up response
        """
        # Build context text
        stage1_text = ""
        for result in stage1_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"
        
        stage2_text = ""
        for result in stage2_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"
        
        chairman_prompt = f"""You are the Chairman of an LLM Council. You have previously synthesized a response based on the council's input. The user now has a follow-up question.

Original Question: {original_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Chairman's Initial Response:
{stage3_response}

User Follow-up Question: {followup_query}

Your task is to answer the follow-up question. You should:
- Maintain the persona of the Chairman (wise, synthesizing, authoritative but balanced).
- Refer back to the council's findings if relevant to the follow-up.
- If the follow-up challenges your previous conclusion, re-evaluate based on the evidence.
- Provide a direct and helpful answer.

Answer:"""
        
        messages = [{"role": "user", "content": chairman_prompt}]
        response = await self.llm.chat(self.chairman_model, messages)
        
        if response is None:
            return Stage3Result(
                model=self.chairman_model,
                response="Error: Unable to generate follow-up response."
            )
        
        return Stage3Result(
            model=self.chairman_model,
            response=response.get('content', '')
        )
    
    async def _generate_title(self, user_query: str) -> str:
        """Generate a short title for a conversation."""
        title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""
        
        messages = [{"role": "user", "content": title_prompt}]
        response = await self.llm.chat("google/gemini-2.5-flash", messages, timeout=30.0)
        
        if response is None:
            return "New Conversation"
        
        title = response.get('content', 'New Conversation').strip()
        title = title.strip('"\'')
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title
    
    async def _stage3_synthesize(
        self,
        user_query: str,
        stage1_results: List[Stage1Result],
        stage2_results: List[Stage2Result]
    ) -> Stage3Result:
        """Synthesize the final response from the Chairman."""
        stage1_text = ""
        for result in stage1_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"
        
        stage2_text = ""
        for result in stage2_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"
        
        chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Your task as Chairman is to synthesize all of this information into a single, comprehensive, accurate answer to the user's original question. Consider:
- The individual responses and their insights
- The peer rankings and what they reveal about response quality
- Any patterns of agreement or disagreement
- Note: Some models may have failed to respond (indicated by STATUS: ERROR).

Provide a clear, well-reasoned final answer that represents the council's collective wisdom:"""
        
        messages = [{"role": "user", "content": chairman_prompt}]
        response = await self.llm.chat(self.chairman_model, messages)
        
        if response is None:
            return Stage3Result(
                model=self.chairman_model,
                response="Error: Unable to generate final synthesis."
            )
        
        return Stage3Result(
            model=self.chairman_model,
            response=response.get('content', '')
        )
    
    def _build_ranking_prompt(self, user_query: str, responses_text: str) -> str:
        """Build the Stage 2 ranking prompt."""
        return f"""You are evaluating different responses to the following question:

Question: {user_query}

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

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""
