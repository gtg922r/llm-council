"""3-stage LLM Council orchestration."""

from typing import List, Dict, Any, Tuple
from .openrouter import query_models_parallel, query_model
from .config import COUNCIL_MODELS, CHAIRMAN_MODEL
from typing import List, Dict, Any, Tuple, Optional
from .ports import LLMProvider, ConversationRepository
from .domain.models import (
    Stage1Result, 
    Stage2Result, 
    AggregateRanking, 
    AssistantMetadata, 
    CouncilRun
)


async def stage1_collect_responses(
    user_query: str, 
    llm_provider: Optional[LLMProvider] = None
) -> List[Stage1Result]:
    """
    Stage 1: Collect individual responses from all council models.

    Args:
        user_query: The user's question
        llm_provider: LLM provider instance

    Returns:
        List of Stage1Result objects
    """
    from .openrouter import query_models_parallel
    
    messages = [{"role": "user", "content": user_query}]

    # Query all models in parallel
    if llm_provider:
        # Assuming the implementation has chat_parallel or we use gather
        # Let's check if we should add it to LLMProvider port or just use chat
        if hasattr(llm_provider, 'chat_parallel'):
            responses = await llm_provider.chat_parallel(COUNCIL_MODELS, messages)
        else:
            tasks = [llm_provider.chat(model, messages) for model in COUNCIL_MODELS]
            results = await asyncio.gather(*tasks)
            responses = dict(zip(COUNCIL_MODELS, results))
    else:
        responses = await query_models_parallel(COUNCIL_MODELS, messages)

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


async def stage2_collect_rankings(
    user_query: str,
    stage1_results: List[Stage1Result],
    llm_provider: Optional[LLMProvider] = None
) -> Tuple[List[Stage2Result], Dict[str, str]]:
    """
    Stage 2: Each model ranks the anonymized responses.

    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        llm_provider: LLM provider instance

    Returns:
        Tuple of (rankings list, label_to_model mapping)
    """
    from .openrouter import query_models_parallel

    # Create anonymized labels for successful responses (Response A, Response B, etc.)
    successful_results = [r for r in stage1_results if r.status == "success"]
    
    labels = [chr(65 + i) for i in range(len(successful_results))]  # A, B, C, ...

    # Create mapping from label to model name
    label_to_model = {
        f"Response {label}": result.model
        for label, result in zip(labels, successful_results)
    }

    # Build the ranking prompt
    responses_text = "\n\n".join([
        f"Response {label}:\n{result.response}"
        for label, result in zip(labels, successful_results)
    ])

    ranking_prompt = f"""You are evaluating different responses to the following question:

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

    messages = [{"role": "user", "content": ranking_prompt}]

    # Get rankings from all council models in parallel
    if llm_provider:
        if hasattr(llm_provider, 'chat_parallel'):
            responses = await llm_provider.chat_parallel(COUNCIL_MODELS, messages)
        else:
            tasks = [llm_provider.chat(model, messages) for model in COUNCIL_MODELS]
            results = await asyncio.gather(*tasks)
            responses = dict(zip(COUNCIL_MODELS, results))
    else:
        responses = await query_models_parallel(COUNCIL_MODELS, messages)

    # Format results
    stage2_results = []
    for model in COUNCIL_MODELS:
        response = responses.get(model)
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

    return stage2_results, label_to_model



async def stage3_synthesize_final(
    user_query: str,
    stage1_results: List[Stage1Result],
    stage2_results: List[Stage2Result],
    llm_provider: Optional[LLMProvider] = None
) -> Dict[str, Any]:
    """
    Stage 3: Chairman synthesizes final response.

    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        llm_provider: LLM provider instance

    Returns:
        Dict with 'model' and 'response' keys
    """
    from .openrouter import query_model

    # Build comprehensive context for chairman
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

    # Query the chairman model
    if llm_provider:
        response = await llm_provider.chat(CHAIRMAN_MODEL, messages)
    else:
        response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        # Fallback if chairman fails
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate final synthesis."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }


def parse_ranking_from_text(ranking_text: str) -> List[str]:
    """
    Parse the FINAL RANKING section from the model's response.

    Args:
        ranking_text: The full text response from the model

    Returns:
        List of response labels in ranked order
    """
    import re

    # Look for "FINAL RANKING:" section
    if "FINAL RANKING:" in ranking_text:
        # Extract everything after "FINAL RANKING:"
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            # Try to extract numbered list format (e.g., "1. Response A")
            # This pattern looks for: number, period, optional space, "Response X"
            numbered_matches = re.findall(r'\d+\.\s*Response [A-Z]', ranking_section)
            if numbered_matches:
                # Extract just the "Response X" part
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
    """
    Calculate aggregate rankings across all models.

    Args:
        stage2_results: Rankings from each model
        label_to_model: Mapping from anonymous labels to model names

    Returns:
        List of AggregateRanking objects, sorted best to worst
    """
    from collections import defaultdict

    # Track positions for each model
    model_positions = defaultdict(list)

    for ranking in stage2_results:
        # parsed_ranking is already available in Stage2Result
        parsed_ranking = ranking.parsed_ranking

        for position, label in enumerate(parsed_ranking, start=1):
            if label in label_to_model:
                model_name = label_to_model[label]
                model_positions[model_name].append(position)

    # Calculate average position for each model
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


async def generate_conversation_title(user_query: str) -> str:
    """
    Generate a short title for a conversation based on the first user message.

    Args:
        user_query: The first user message

    Returns:
        A short title (3-5 words)
    """
    title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""

    messages = [{"role": "user", "content": title_prompt}]

    # Use gemini-2.5-flash for title generation (fast and cheap)
    response = await query_model("google/gemini-2.5-flash", messages, timeout=30.0)

    if response is None:
        # Fallback to a generic title
        return "New Conversation"

    title = response.get('content', 'New Conversation').strip()

    # Clean up the title - remove quotes, limit length
    title = title.strip('"\'')

    # Truncate if too long
    if len(title) > 50:
        title = title[:47] + "..."

    return title


async def run_full_council(
    user_query: str,
    llm_provider: Optional[LLMProvider] = None
) -> CouncilRun:
    """
    Run the complete 3-stage council process.

    Args:
        user_query: The user's question
        llm_provider: LLM provider instance

    Returns:
        CouncilRun domain model
    """
    # Stage 1: Collect individual responses
    stage1_results = await stage1_collect_responses(user_query, llm_provider=llm_provider)

    # If no models responded successfully, return error
    successful_stage1 = [r for r in stage1_results if r.status == "success"]
    if not successful_stage1:
        return CouncilRun(
            stage1_results=stage1_results,
            stage2_results=[],
            stage3_result={
                "model": "error",
                "response": "All models failed to respond. Please try again."
            },
            metadata=AssistantMetadata()
        )

    # Stage 2: Collect rankings
    stage2_results, label_to_model = await stage2_collect_rankings(
        user_query, 
        stage1_results, 
        llm_provider=llm_provider
    )

    # Calculate aggregate rankings
    aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)

    # Stage 3: Synthesize final answer
    stage3_result = await stage3_synthesize_final(
        user_query,
        stage1_results,
        stage2_results,
        llm_provider=llm_provider
    )

    # Prepare metadata
    metadata = AssistantMetadata(
        label_to_model=label_to_model,
        aggregate_rankings=aggregate_rankings
    )

    return CouncilRun(
        stage1_results=stage1_results,
        stage2_results=stage2_results,
        stage3_result=stage3_result,
        metadata=metadata
    )


async def chairman_followup(
    original_query: str,
    stage1_results: List[Stage1Result],
    stage2_results: List[Stage2Result],
    stage3_response: str,
    followup_query: str,
    llm_provider: Optional[LLMProvider] = None
) -> Dict[str, Any]:
    """
    Handle a follow-up question to the Chairman.

    Args:
        original_query: The initial user question
        stage1_results: Results from Stage 1
        stage2_results: Rankings from Stage 2
        stage3_response: The Chairman's initial response
        followup_query: The user's follow-up question
        llm_provider: LLM provider instance

    Returns:
        Dict with 'model' and 'response' keys
    """
    from .openrouter import query_model

    # Build comprehensive context for chairman
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

    # Query the chairman model
    if llm_provider:
        response = await llm_provider.chat(CHAIRMAN_MODEL, messages)
    else:
        response = await query_model(CHAIRMAN_MODEL, messages)

    if response is None:
        return {
            "model": CHAIRMAN_MODEL,
            "response": "Error: Unable to generate follow-up response."
        }

    return {
        "model": CHAIRMAN_MODEL,
        "response": response.get('content', '')
    }
