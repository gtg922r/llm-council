"""Council Service - Orchestrates the multi-stage LLM Council workflow.

This service implements the core business logic for running a council deliberation.
It yields Domain Events that can be consumed for streaming or batch responses.

The service is infrastructure-agnostic - it uses LLMProvider interface for
model queries, enabling testing without real API calls.
"""

import asyncio
import re
from typing import List, Dict, Any, Optional, AsyncGenerator, Tuple

from backend.ports import LLMProvider
from backend.domain.models import (
    Stage1Response, Stage2Ranking, Stage3Synthesis,
    CouncilMetadata, AggregateRanking, CouncilRun,
    AssistantMessage
)
from backend.domain.events import (
    Event, Stage1Started, Stage1Progress, Stage1Complete,
    Stage2Started, Stage2Progress, Stage2Complete,
    Stage3Started, Stage3Complete, TitleGenerated, CouncilComplete, CouncilError
)


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """Parse the FINAL RANKING section from the model's response.
    
    Args:
        ranking_text: The full text response from the model.
    
    Returns:
        List of response labels in ranked order.
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
    stage2_results: List[Stage2Ranking],
    label_to_model: Dict[str, str]
) -> List[AggregateRanking]:
    """Calculate aggregate rankings across all models.
    
    Args:
        stage2_results: Rankings from each model.
        label_to_model: Mapping from anonymous labels to model names.
    
    Returns:
        List of AggregateRanking models, sorted best to worst.
    """
    from collections import defaultdict

    model_positions = defaultdict(list)

    for ranking in stage2_results:
        for position, label in enumerate(ranking.parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    aggregate: List[AggregateRanking] = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append(AggregateRanking(
                model=model,
                average_rank=round(avg_rank, 2),
                rankings_count=len(positions)
            ))

    aggregate.sort(key=lambda x: x.average_rank)
    return aggregate


class CouncilService:
    """Orchestrates the multi-stage LLM Council workflow.
    
    This service yields Domain Events as it progresses through the workflow,
    enabling both streaming and batch consumption patterns.
    """
    
    def __init__(
        self,
        llm_provider: LLMProvider,
        council_models: List[str],
        chairman_model: str
    ):
        """Initialize the service.
        
        Args:
            llm_provider: The LLM provider for making queries.
            council_models: List of model identifiers for the council.
            chairman_model: The model to use for final synthesis.
        """
        self.llm_provider = llm_provider
        self.council_models = council_models
        self.chairman_model = chairman_model
    
    async def _query_with_tracking(
        self, model: str, messages: List[Dict[str, str]]
    ) -> Tuple[str, Optional[Dict[str, Any]]]:
        """Query a model and return (model, response) for tracking."""
        try:
            response = await self.llm_provider.query(model, messages)
            return model, response
        except Exception as e:
            print(f"Exception querying model {model}: {e}")
            return model, None
    
    async def run_council(
        self, user_query: str
    ) -> AsyncGenerator[Event, None]:
        """Run the complete council workflow, yielding events.
        
        Args:
            user_query: The user's question.
        
        Yields:
            Domain events as the workflow progresses.
        """
        try:
            # Stage 1: Collect individual responses
            yield Stage1Started(total=len(self.council_models))
            
            stage1_messages = [{"role": "user", "content": user_query}]
            stage1_tasks = [
                asyncio.create_task(self._query_with_tracking(model, stage1_messages))
                for model in self.council_models
            ]
            
            stage1_responses: Dict[str, Optional[Dict[str, Any]]] = {}
            completed = 0
            
            for task in asyncio.as_completed(stage1_tasks):
                model, response = await task
                stage1_responses[model] = response
                completed += 1
                yield Stage1Progress(completed=completed, total=len(self.council_models))
            
            # Build Stage 1 results
            stage1_results: List[Stage1Response] = []
            for model in self.council_models:
                response = stage1_responses.get(model)
                if response is not None:
                    stage1_results.append(Stage1Response(
                        model=model,
                        response=response.get('content', ''),
                        status="success"
                    ))
                else:
                    stage1_results.append(Stage1Response(
                        model=model,
                        response="Error: Failed to get response from this model.",
                        status="error"
                    ))
            
            yield Stage1Complete(data=stage1_results)
            
            # Check if we have any successful responses
            successful_stage1 = [r for r in stage1_results if r.status == "success"]
            if not successful_stage1:
                yield CouncilError(message="All models failed to respond. Please try again.")
                return
            
            # Stage 2: Collect rankings
            yield Stage2Started(total=len(self.council_models))
            
            labels = [chr(65 + i) for i in range(len(successful_stage1))]
            label_to_model = {
                f"Response {label}": result.model
                for label, result in zip(labels, successful_stage1)
            }
            
            responses_text = "\n\n".join([
                f"Response {label}:\n{result.response}"
                for label, result in zip(labels, successful_stage1)
            ])
            
            ranking_prompt = self._build_ranking_prompt(user_query, responses_text)
            stage2_messages = [{"role": "user", "content": ranking_prompt}]
            
            stage2_tasks = [
                asyncio.create_task(self._query_with_tracking(model, stage2_messages))
                for model in self.council_models
            ]
            
            stage2_responses: Dict[str, Optional[Dict[str, Any]]] = {}
            completed = 0
            
            for task in asyncio.as_completed(stage2_tasks):
                model, response = await task
                stage2_responses[model] = response
                completed += 1
                yield Stage2Progress(completed=completed, total=len(self.council_models))
            
            # Build Stage 2 results
            stage2_results: List[Stage2Ranking] = []
            for model in self.council_models:
                response = stage2_responses.get(model)
                if response is not None:
                    full_text = response.get('content', '')
                    parsed = parse_ranking_from_text(full_text)
                    stage2_results.append(Stage2Ranking(
                        model=model,
                        ranking=full_text,
                        parsed_ranking=parsed,
                        status="success"
                    ))
                else:
                    stage2_results.append(Stage2Ranking(
                        model=model,
                        ranking="Error: Failed to get ranking from this model.",
                        parsed_ranking=[],
                        status="error"
                    ))
            
            aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
            metadata = CouncilMetadata(
                label_to_model=label_to_model,
                aggregate_rankings=aggregate_rankings
            )
            
            yield Stage2Complete(data=stage2_results, metadata=metadata)
            
            # Stage 3: Synthesize final answer
            yield Stage3Started()
            
            chairman_prompt = self._build_chairman_prompt(user_query, stage1_results, stage2_results)
            stage3_messages = [{"role": "user", "content": chairman_prompt}]
            
            response = await self.llm_provider.query(self.chairman_model, stage3_messages)
            
            if response is None:
                stage3_result = Stage3Synthesis(
                    model=self.chairman_model,
                    response="Error: Unable to generate final synthesis."
                )
            else:
                stage3_result = Stage3Synthesis(
                    model=self.chairman_model,
                    response=response.get('content', '')
                )
            
            yield Stage3Complete(data=stage3_result)
            yield CouncilComplete()
        
        except Exception as e:
            yield CouncilError(message=str(e))
    
    async def run_council_batch(self, user_query: str) -> CouncilRun:
        """Run the council and collect all results into a CouncilRun.
        
        This is a convenience method for non-streaming use cases.
        
        Args:
            user_query: The user's question.
        
        Returns:
            A CouncilRun with all results.
        """
        stage1_results: List[Stage1Response] = []
        stage2_results: List[Stage2Ranking] = []
        stage3_result: Optional[Stage3Synthesis] = None
        metadata: Optional[CouncilMetadata] = None
        
        async for event in self.run_council(user_query):
            if isinstance(event, Stage1Complete):
                stage1_results = event.data
            elif isinstance(event, Stage2Complete):
                stage2_results = event.data
                metadata = event.metadata
            elif isinstance(event, Stage3Complete):
                stage3_result = event.data
        
        return CouncilRun(
            user_query=user_query,
            stage1=stage1_results,
            stage2=stage2_results,
            stage3=stage3_result,
            metadata=metadata or CouncilMetadata()
        )
    
    async def generate_title(self, user_query: str) -> str:
        """Generate a short title for a conversation.
        
        Args:
            user_query: The first user message.
        
        Returns:
            A short title (3-5 words).
        """
        title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""
        
        messages = [{"role": "user", "content": title_prompt}]
        
        # Use a fast model for title generation
        response = await self.llm_provider.query("google/gemini-2.5-flash", messages, timeout=30.0)
        
        if response is None:
            return "New Conversation"
        
        title = response.get('content', 'New Conversation').strip()
        title = title.strip('"\'')
        
        if len(title) > 50:
            title = title[:47] + "..."
        
        return title
    
    async def chairman_followup(
        self,
        original_query: str,
        stage1_results: List[Stage1Response],
        stage2_results: List[Stage2Ranking],
        stage3_response: str,
        followup_query: str
    ) -> Stage3Synthesis:
        """Handle a follow-up question to the Chairman.
        
        Args:
            original_query: The initial user question.
            stage1_results: Results from Stage 1.
            stage2_results: Rankings from Stage 2.
            stage3_response: The Chairman's initial response.
            followup_query: The user's follow-up question.
        
        Returns:
            The Chairman's follow-up response.
        """
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
        response = await self.llm_provider.query(self.chairman_model, messages)
        
        if response is None:
            return Stage3Synthesis(
                model=self.chairman_model,
                response="Error: Unable to generate follow-up response."
            )
        
        return Stage3Synthesis(
            model=self.chairman_model,
            response=response.get('content', '')
        )
    
    def _build_ranking_prompt(self, user_query: str, responses_text: str) -> str:
        """Build the prompt for ranking responses."""
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
    
    def _build_chairman_prompt(
        self,
        user_query: str,
        stage1_results: List[Stage1Response],
        stage2_results: List[Stage2Ranking]
    ) -> str:
        """Build the prompt for the chairman synthesis."""
        stage1_text = ""
        for result in stage1_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"
        
        stage2_text = ""
        for result in stage2_results:
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"
        
        return f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

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


def create_assistant_message_from_council_run(run: CouncilRun) -> AssistantMessage:
    """Create an AssistantMessage from a CouncilRun.
    
    This is a helper for persisting council results to storage.
    
    Args:
        run: The completed CouncilRun.
    
    Returns:
        An AssistantMessage ready for storage.
    """
    return AssistantMessage(
        stage1=run.stage1,
        stage2=run.stage2,
        stage3=run.stage3,
        metadata=run.metadata
    )
