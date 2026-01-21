"""Pure prompt templates for Symposia.

This module contains only string building functions - no async, no network calls.
Follows the principle of keeping prompt logic separate from orchestration.
"""

from typing import List
from ..domain.models import Stage1Result, Stage2Result


def build_ranking_prompt(user_query: str, stage1_results: List[Stage1Result]) -> str:
    """
    Build the Stage 2 ranking prompt from Stage 1 results.
    
    Args:
        user_query: The original user query
        stage1_results: Results from Stage 1
        
    Returns:
        The complete ranking prompt string
    """
    # Create anonymized labels for successful responses
    successful_results = [r for r in stage1_results if r.status == "success"]
    labels = [chr(65 + i) for i in range(len(successful_results))]  # A, B, C, ...
    
    responses_text = "\n\n".join([
        f"Response {label}:\n{result.response}"
        for label, result in zip(labels, successful_results)
    ])
    
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


def build_chairman_synthesis_prompt(
    user_query: str,
    stage1_results: List[Stage1Result],
    stage2_results: List[Stage2Result]
) -> str:
    """
    Build the Stage 3 chairman synthesis prompt.
    
    Args:
        user_query: The original user query
        stage1_results: Individual model responses from Stage 1
        stage2_results: Rankings from Stage 2
        
    Returns:
        The complete chairman synthesis prompt string
    """
    stage1_text = ""
    for result in stage1_results:
        status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
        stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"

    stage2_text = ""
    for result in stage2_results:
        status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
        stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"

    return f"""You are the Chairman of Symposia, an AI Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

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


def build_chairman_followup_prompt(
    original_query: str,
    stage1_results: List[Stage1Result],
    stage2_results: List[Stage2Result],
    stage3_response: str,
    followup_query: str
) -> str:
    """
    Build the chairman follow-up prompt.
    
    Args:
        original_query: The initial user question
        stage1_results: Results from Stage 1
        stage2_results: Rankings from Stage 2
        stage3_response: The Chairman's initial response
        followup_query: The user's follow-up question
        
    Returns:
        The complete chairman follow-up prompt string
    """
    stage1_text = ""
    for result in stage1_results:
        status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
        stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"

    stage2_text = ""
    for result in stage2_results:
        status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
        stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"

    return f"""You are the Chairman of Symposia, an AI Council. You have previously synthesized a response based on the council's input. The user now has a follow-up question.

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


def build_title_generation_prompt(user_query: str) -> str:
    """
    Build the prompt for generating a conversation title.
    
    Args:
        user_query: The first user message
        
    Returns:
        The prompt string for title generation
    """
    return f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_query}

Title:"""


def create_label_to_model_mapping(stage1_results: List[Stage1Result]) -> dict:
    """
    Create the mapping from anonymous labels to model names.
    
    Args:
        stage1_results: Results from Stage 1
        
    Returns:
        Dict mapping "Response A" -> "model/name"
    """
    successful_results = [r for r in stage1_results if r.status == "success"]
    labels = [chr(65 + i) for i in range(len(successful_results))]  # A, B, C, ...
    
    return {
        f"Response {label}": result.model
        for label, result in zip(labels, successful_results)
    }
