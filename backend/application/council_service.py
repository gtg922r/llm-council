import asyncio
import json
from typing import AsyncGenerator, List, Dict, Any, Optional
from ..domain.models import (
    Conversation, UserMessage, AssistantMessage, FileReference, 
    Stage1Result, Stage2Result, Stage3Result
)
from ..domain.events import (
    DomainEvent, Stage1Start, Stage1Progress, Stage1Complete,
    Stage2Start, Stage2Progress, Stage2Complete,
    Stage3Start, Stage3Complete, TitleComplete, CouncilComplete, CouncilError
)
from ..ports import ConversationRepository, LLMProvider
from ..config import COUNCIL_MODELS
from ..council import (
    parse_ranking_from_text, calculate_aggregate_rankings, 
    stage3_synthesize_final, generate_conversation_title
)

class CouncilService:
    def __init__(self, repository: ConversationRepository, llm_provider: LLMProvider):
        self.repository = repository
        self.llm_provider = llm_provider

    async def run_council(
        self, 
        conversation_id: str, 
        prompt_content: str,
        user_message_content: str, # For title generation and persistence
        files: List[FileReference],
        is_first_message: bool
    ) -> AsyncGenerator[DomainEvent, None]:
        
        conversation = self.repository.get(conversation_id)
        if not conversation:
             yield CouncilError(message="Conversation not found")
             return

        try:
            async def query_with_model(model, messages):
                try:
                    # Use llm_provider
                    return model, await self.llm_provider.query(model, messages)
                except Exception as e:
                    print(f"Exception raised while querying model {model}: {e}")
                    return model, None
            
            # Add user message
            user_msg = UserMessage(content=user_message_content, files=files)
            conversation.messages.append(user_msg)
            self.repository.save(conversation)

            # Start title generation in parallel (don't await yet)
            title_task = None
            if is_first_message:
                # generate_conversation_title currently calls query_model directly
                # We should refactor it or just let it be for now (it's a utility).
                # But strictly, we should use llm_provider.
                # For this refactor, I'll rely on the existing import in council.py for title, 
                # OR reimplement title gen here using provider.
                # Reimplementing is cleaner.
                
                async def generate_title_internal():
                     title_prompt = f"""Generate a very short title (3-5 words maximum) that summarizes the following question.
The title should be concise and descriptive. Do not use quotes or punctuation in the title.

Question: {user_message_content}

Title:"""
                     messages = [{"role": "user", "content": title_prompt}]
                     # Use a fast model
                     response = await self.llm_provider.query("google/gemini-2.5-flash", messages, timeout=30.0)
                     if response:
                         title = response.get('content', 'New Conversation').strip().strip('"\'')
                         if len(title) > 50:
                             title = title[:47] + "..."
                         return title
                     return "New Conversation"

                title_task = asyncio.create_task(generate_title_internal())

            # Stage 1: Collect responses
            yield Stage1Start(total=len(COUNCIL_MODELS))
            stage1_messages = [{"role": "user", "content": prompt_content}]
            stage1_tasks = [
                asyncio.create_task(query_with_model(model, stage1_messages))
                for model in COUNCIL_MODELS
            ]
            stage1_responses = {}
            stage1_completed = 0
            for task in asyncio.as_completed(stage1_tasks):
                model, response = await task
                stage1_responses[model] = response
                stage1_completed += 1
                yield Stage1Progress(completed=stage1_completed, total=len(COUNCIL_MODELS))

            stage1_results = []
            for model in COUNCIL_MODELS:
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

            # Stage 2: Collect rankings
            yield Stage2Start(total=len(COUNCIL_MODELS))
            successful_results = [r for r in stage1_results if r.status == "success"]
            labels = [chr(65 + i) for i in range(len(successful_results))]
            label_to_model = {
                f"Response {label}": result.model
                for label, result in zip(labels, successful_results)
            }
            responses_text = "\n\n".join([
                f"Response {label}:\n{result.response}"
                for label, result in zip(labels, successful_results)
            ])
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

Example of the correct format for your ENTIRE response:

Response A provides good detail on X but misses Y...
Response B is accurate but lacks depth on Z...
Response C offers the most comprehensive answer...

FINAL RANKING:
1. Response C
2. Response A
3. Response B

Now provide your evaluation and ranking:"""
            stage2_messages = [{"role": "user", "content": ranking_prompt}]
            stage2_tasks = [
                asyncio.create_task(query_with_model(model, stage2_messages))
                for model in COUNCIL_MODELS
            ]
            stage2_responses = {}
            stage2_completed = 0
            for task in asyncio.as_completed(stage2_tasks):
                model, response = await task
                stage2_responses[model] = response
                stage2_completed += 1
                yield Stage2Progress(completed=stage2_completed, total=len(COUNCIL_MODELS))

            stage2_results = []
            for model in COUNCIL_MODELS:
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
            
            # Convert stage2_results to dicts for calculate_aggregate_rankings if it expects dicts
            # But calculate_aggregate_rankings expects list of dicts.
            # I should update calculate_aggregate_rankings to handle objects or convert here.
            # Converting here for safety.
            stage2_dicts = [s.model_dump() for s in stage2_results]
            aggregate_rankings = calculate_aggregate_rankings(stage2_dicts, label_to_model)
            
            yield Stage2Complete(
                data=stage2_results, 
                metadata={'label_to_model': label_to_model, 'aggregate_rankings': aggregate_rankings}
            )

            # Stage 3: Synthesize final answer
            yield Stage3Start()
            
            # stage3_synthesize_final expects dicts.
            stage1_dicts = [s.model_dump() for s in stage1_results]
            
            # Reimplement stage3_synthesize_final call using llm_provider?
            # Or use the existing function but convert args?
            # existing function uses query_model internally. 
            # Ideally I should pass the provider or duplicate logic.
            # I'll duplicate logic to use self.llm_provider
            
            stage1_text = ""
            for result in stage1_results:
                status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
                stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"

            stage2_text = ""
            for result in stage2_results:
                status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
                stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"

            chairman_prompt = f"""You are the Chairman of an LLM Council. Multiple AI models have provided responses to a user's question, and then ranked each other's responses.

Original Question: {prompt_content}

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

            # CHAIRMAN_MODEL import?
            from ..config import CHAIRMAN_MODEL
            messages = [{"role": "user", "content": chairman_prompt}]
            response = await self.llm_provider.query(CHAIRMAN_MODEL, messages)
            
            if response:
                stage3_result = Stage3Result(model=CHAIRMAN_MODEL, response=response.get('content', ''))
            else:
                stage3_result = Stage3Result(model=CHAIRMAN_MODEL, response="Error: Unable to generate final synthesis.")

            yield Stage3Complete(data=stage3_result)

            # Wait for title generation
            if title_task:
                title = await title_task
                conversation.title = title
                self.repository.save(conversation)
                yield TitleComplete(data={'title': title})

            # Save complete assistant message
            assistant_msg = AssistantMessage(
                stage1=stage1_results,
                stage2=stage2_results,
                stage3=stage3_result,
                metadata={"label_to_model": label_to_model, "aggregate_rankings": aggregate_rankings}
            )
            conversation.messages.append(assistant_msg)
            conversation.has_unread = True
            self.repository.save(conversation)

            yield CouncilComplete()

        except Exception as e:
            yield CouncilError(message=str(e))
