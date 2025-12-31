"""Council orchestration service (unified streaming + non-streaming)."""

from __future__ import annotations

import asyncio
import re
from collections import defaultdict
from typing import Any, AsyncIterator

from ..domain.events import (
    CouncilEvent,
    ErrorEvent,
    RunCompleted,
    StageCompleted,
    StageProgress,
    StageStarted,
    TitleUpdated,
)
from ..domain.models import (
    AssistantMessage,
    FileAttachment,
    Stage1Result,
    Stage2Result,
    Stage3Result,
    UserMessage,
)
from ..infrastructure.blob_store import LocalFileBlobStore
from ..ports import ConversationRepository, LLMProvider
from .prompt_builder import build_prompt_content


def parse_ranking_from_text(ranking_text: str) -> list[str]:
    """Parse the FINAL RANKING section from a model's evaluation."""
    if "FINAL RANKING:" in ranking_text:
        parts = ranking_text.split("FINAL RANKING:")
        if len(parts) >= 2:
            ranking_section = parts[1]
            numbered_matches = re.findall(r"\d+\.\s*Response [A-Z]", ranking_section)
            if numbered_matches:
                return [re.search(r"Response [A-Z]", m).group() for m in numbered_matches]  # type: ignore[union-attr]
            return re.findall(r"Response [A-Z]", ranking_section)
    return re.findall(r"Response [A-Z]", ranking_text)


def calculate_aggregate_rankings(
    stage2_results: list[Stage2Result],
    label_to_model: dict[str, str],
) -> list[dict[str, Any]]:
    """Compute average rank position across peer evaluations."""
    model_positions: dict[str, list[int]] = defaultdict(list)
    for ranking in stage2_results:
        for position, label in enumerate(ranking.parsed_ranking, start=1):
            model_name = label_to_model.get(label)
            if model_name:
                model_positions[model_name].append(position)

    aggregate: list[dict[str, Any]] = []
    for model, positions in model_positions.items():
        if positions:
            avg_rank = sum(positions) / len(positions)
            aggregate.append(
                {
                    "model": model,
                    "average_rank": round(avg_rank, 2),
                    "rankings_count": len(positions),
                }
            )
    aggregate.sort(key=lambda x: x["average_rank"])
    return aggregate


class CouncilOrchestrator:
    """Application service coordinating the 3-stage workflow."""

    def __init__(
        self,
        *,
        repo: ConversationRepository,
        llm: LLMProvider,
        blob_store: LocalFileBlobStore,
        council_models: list[str],
        chairman_model: str,
        title_model: str = "google/gemini-2.5-flash",
    ):
        self._repo = repo
        self._llm = llm
        self._blob_store = blob_store
        self._council_models = council_models
        self._chairman_model = chairman_model
        self._title_model = title_model

    async def _generate_title(self, user_query: str) -> str:
        title_prompt = (
            "Generate a very short title (3-5 words maximum) that summarizes the following question.\n"
            "The title should be concise and descriptive. Do not use quotes or punctuation in the title.\n\n"
            f"Question: {user_query}\n\n"
            "Title:"
        )
        response = await self._llm.chat(
            model=self._title_model,
            messages=[{"role": "user", "content": title_prompt}],
            timeout=30.0,
        )
        if response is None:
            return "New Conversation"
        title = (response.get("content") or "New Conversation").strip().strip("\"'")
        return title[:47] + "..." if len(title) > 50 else title

    async def _query_model(self, model: str, prompt: str) -> tuple[str, dict[str, Any] | None]:
        try:
            return model, await self._llm.chat(model=model, messages=[{"role": "user", "content": prompt}])
        except Exception as e:
            print(f"Exception raised while querying model {model}: {e}")
            return model, None

    async def run(
        self,
        *,
        conversation_id: str,
        content: str,
        files: list[dict[str, Any]] | None = None,
        target_model: str | None = None,
    ) -> AsyncIterator[CouncilEvent]:
        conversation = self._repo.get(conversation_id)
        if conversation is None:
            yield ErrorEvent(message="Conversation not found")
            return

        is_first_message = len(conversation.messages) == 0
        title_task: asyncio.Task[str] | None = None
        if is_first_message:
            title_task = asyncio.create_task(self._generate_title(content))

        # Persist user message (store attachments as blobs + references)
        attachments: list[FileAttachment] = []
        for f in files or []:
            reference_id = self._blob_store.save_text(str(f.get("content", "")))
            attachments.append(
                FileAttachment(
                    name=str(f.get("name")),
                    file_reference_id=reference_id,
                    size=f.get("size"),
                )
            )

        conversation.messages.append(UserMessage(content=content, files=attachments))
        self._repo.save(conversation)

        prompt_content = build_prompt_content(
            content=content,
            files=attachments,
            blob_store=self._blob_store,
        )

        if target_model == "chairman":
            async for event in self._run_chairman_followup(
                conversation_id=conversation_id,
                followup_prompt=prompt_content,
            ):
                yield event
            if title_task:
                title = await title_task
                conversation = self._repo.get(conversation_id)
                if conversation:
                    conversation.title = title
                    self._repo.save(conversation)
                yield TitleUpdated(title=title)
            yield RunCompleted()
            return

        # --- Stage 1 ---
        yield StageStarted(stage="stage1", total=len(self._council_models))
        stage1_tasks = [
            asyncio.create_task(self._query_model(model, prompt_content))
            for model in self._council_models
        ]
        stage1_responses: dict[str, dict[str, Any] | None] = {}
        completed = 0
        for task in asyncio.as_completed(stage1_tasks):
            model, response = await task
            stage1_responses[model] = response
            completed += 1
            yield StageProgress(stage="stage1", completed=completed, total=len(self._council_models))

        stage1_results: list[Stage1Result] = []
        for model in self._council_models:
            response = stage1_responses.get(model)
            if response is not None:
                stage1_results.append(
                    Stage1Result(model=model, response=response.get("content", "") or "", status="success")
                )
            else:
                stage1_results.append(
                    Stage1Result(
                        model=model,
                        response="Error: Failed to get response from this model.",
                        status="error",
                    )
                )
        yield StageCompleted(stage="stage1", data=[r.model_dump() for r in stage1_results])

        successful_stage1 = [r for r in stage1_results if r.status == "success"]
        if not successful_stage1:
            stage3 = Stage3Result(
                model="error",
                response="All models failed to respond. Please try again.",
            )
            assistant = AssistantMessage(
                stage1=stage1_results,
                stage2=[],
                stage3=stage3,
                metadata={},
            )
            conversation = self._repo.get(conversation_id)
            if conversation:
                conversation.messages.append(assistant)
                conversation.has_unread = True
                self._repo.save(conversation)
            yield StageStarted(stage="stage3")
            yield StageCompleted(stage="stage3", data=stage3.model_dump())
            if title_task:
                title = await title_task
                conversation = self._repo.get(conversation_id)
                if conversation:
                    conversation.title = title
                    self._repo.save(conversation)
                yield TitleUpdated(title=title)
            yield RunCompleted()
            return

        # --- Stage 2 ---
        yield StageStarted(stage="stage2", total=len(self._council_models))
        labels = [chr(65 + i) for i in range(len(successful_stage1))]
        label_to_model = {
            f"Response {label}": result.model for label, result in zip(labels, successful_stage1)
        }
        responses_text = "\n\n".join(
            [f"Response {label}:\n{result.response}" for label, result in zip(labels, successful_stage1)]
        )
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

        stage2_tasks = [
            asyncio.create_task(self._query_model(model, ranking_prompt))
            for model in self._council_models
        ]
        stage2_responses: dict[str, dict[str, Any] | None] = {}
        completed = 0
        for task in asyncio.as_completed(stage2_tasks):
            model, response = await task
            stage2_responses[model] = response
            completed += 1
            yield StageProgress(stage="stage2", completed=completed, total=len(self._council_models))

        stage2_results: list[Stage2Result] = []
        for model in self._council_models:
            response = stage2_responses.get(model)
            if response is not None:
                full_text = response.get("content", "") or ""
                stage2_results.append(
                    Stage2Result(
                        model=model,
                        ranking=full_text,
                        parsed_ranking=parse_ranking_from_text(full_text),
                        status="success",
                    )
                )
            else:
                stage2_results.append(
                    Stage2Result(
                        model=model,
                        ranking="Error: Failed to get ranking from this model.",
                        parsed_ranking=[],
                        status="error",
                    )
                )

        aggregate_rankings = calculate_aggregate_rankings(stage2_results, label_to_model)
        run_metadata = {"label_to_model": label_to_model, "aggregate_rankings": aggregate_rankings}
        yield StageCompleted(
            stage="stage2",
            data=[r.model_dump() for r in stage2_results],
            metadata=run_metadata,
        )

        # --- Stage 3 ---
        yield StageStarted(stage="stage3")
        stage1_text = "\n\n".join(
            [
                f"Model: {r.model}{'' if r.status == 'success' else f' [STATUS: {r.status.upper()}]'}\n"
                f"Response: {r.response}"
                for r in stage1_results
            ]
        )
        stage2_text = "\n\n".join(
            [
                f"Model: {r.model}{'' if r.status == 'success' else f' [STATUS: {r.status.upper()}]'}\n"
                f"Ranking: {r.ranking}"
                for r in stage2_results
            ]
        )
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

        response = await self._llm.chat(
            model=self._chairman_model,
            messages=[{"role": "user", "content": chairman_prompt}],
        )
        if response is None:
            stage3 = Stage3Result(model=self._chairman_model, response="Error: Unable to generate final synthesis.")
        else:
            stage3 = Stage3Result(model=self._chairman_model, response=response.get("content", "") or "")
        yield StageCompleted(stage="stage3", data=stage3.model_dump())

        # Persist assistant message with metadata (fixes reload amnesia).
        assistant = AssistantMessage(
            stage1=stage1_results,
            stage2=stage2_results,
            stage3=stage3,
            metadata=run_metadata,
        )
        conversation = self._repo.get(conversation_id)
        if conversation:
            conversation.messages.append(assistant)
            conversation.has_unread = True
            self._repo.save(conversation)

        if title_task:
            title = await title_task
            conversation = self._repo.get(conversation_id)
            if conversation:
                conversation.title = title
                self._repo.save(conversation)
            yield TitleUpdated(title=title)

        yield RunCompleted()

    async def _run_chairman_followup(
        self,
        *,
        conversation_id: str,
        followup_prompt: str,
    ) -> AsyncIterator[CouncilEvent]:
        conversation = self._repo.get(conversation_id)
        if conversation is None:
            yield ErrorEvent(message="Conversation not found")
            return

        last_assistant: AssistantMessage | None = None
        last_assistant_index: int | None = None
        for idx in range(len(conversation.messages) - 1, -1, -1):
            msg = conversation.messages[idx]
            if isinstance(msg, AssistantMessage) and msg.stage3 is not None:
                last_assistant = msg
                last_assistant_index = idx
                break

        original_query = "Unknown (Context from previous turn)"
        if last_assistant_index is not None and last_assistant_index > 0:
            prev_msg = conversation.messages[last_assistant_index - 1]
            if isinstance(prev_msg, UserMessage):
                original_query = prev_msg.content

        stage1_text = ""
        for result in (last_assistant.stage1 if last_assistant else []):
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage1_text += f"Model: {result.model}{status_info}\nResponse: {result.response}\n\n"

        stage2_text = ""
        for result in (last_assistant.stage2 if last_assistant else []):
            status_info = "" if result.status == "success" else f" [STATUS: {result.status.upper()}]"
            stage2_text += f"Model: {result.model}{status_info}\nRanking: {result.ranking}\n\n"

        stage3_response = ""
        if last_assistant and isinstance(last_assistant.stage3, Stage3Result):
            stage3_response = last_assistant.stage3.response
        elif last_assistant and isinstance(last_assistant.stage3, dict):
            stage3_response = str(last_assistant.stage3.get("response") or "")

        chairman_prompt = f"""You are the Chairman of an LLM Council. You have previously synthesized a response based on the council's input. The user now has a follow-up question.

Original Question: {original_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Chairman's Initial Response:
{stage3_response}

User Follow-up Question: {followup_prompt}

Your task is to answer the follow-up question. You should:
- Maintain the persona of the Chairman (wise, synthesizing, authoritative but balanced).
- Refer back to the council's findings if relevant to the follow-up.
- If the follow-up challenges your previous conclusion, re-evaluate based on the evidence.
- Provide a direct and helpful answer.

Answer:"""

        yield StageStarted(stage="stage3")
        response = await self._llm.chat(
            model=self._chairman_model,
            messages=[{"role": "user", "content": chairman_prompt}],
        )
        if response is None:
            stage3 = Stage3Result(
                model=self._chairman_model,
                response="Error: Unable to generate follow-up response.",
            )
        else:
            stage3 = Stage3Result(model=self._chairman_model, response=response.get("content", "") or "")
        yield StageCompleted(stage="stage3", data=stage3.model_dump())

        assistant = AssistantMessage(stage1=[], stage2=[], stage3=stage3, metadata={})
        conversation = self._repo.get(conversation_id)
        if conversation:
            conversation.messages.append(assistant)
            conversation.has_unread = True
            self._repo.save(conversation)

