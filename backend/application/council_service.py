"""Application-layer service orchestrating the council workflow.

This is the single source of truth for both streaming (SSE) and non-stream responses.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any, AsyncIterator, Iterable

from ..domain.events import (
    Complete,
    CouncilEvent,
    Error,
    Stage1Complete,
    Stage1Progress,
    Stage1Start,
    Stage2Complete,
    Stage2Progress,
    Stage2Start,
    Stage3Complete,
    Stage3Start,
    TitleComplete,
)
from ..domain.models import (
    AggregateRanking,
    AssistantMessage,
    AssistantMessageMetadata,
    Conversation,
    FileAttachment,
    Stage1Result,
    Stage2Result,
    Stage3Result,
    UserMessage,
)
from ..domain.ranking import calculate_aggregate_rankings, parse_ranking_from_text
from ..ports import BlobStore, ConversationRepository, LLMProvider
from .prompt_builder import build_prompt_content


@dataclass(frozen=True)
class CouncilConfig:
    council_models: list[str]
    chairman_model: str
    title_model: str = "google/gemini-2.5-flash"


class CouncilService:
    def __init__(
        self,
        *,
        repo: ConversationRepository,
        blob_store: BlobStore,
        llm: LLMProvider,
        config: CouncilConfig,
    ):
        self._repo = repo
        self._blob_store = blob_store
        self._llm = llm
        self._config = config

    def _build_prompt_content(self, content: str, files: Iterable[FileAttachment]) -> str:
        return build_prompt_content(content, files, self._blob_store)

    async def _generate_title(self, first_user_message: str) -> str:
        title_prompt = (
            "Generate a very short title (3-5 words maximum) that summarizes the following question.\n"
            "The title should be concise and descriptive. Do not use quotes or punctuation in the title.\n\n"
            f"Question: {first_user_message}\n\n"
            "Title:"
        )
        response = await self._llm.chat(
            self._config.title_model, [{"role": "user", "content": title_prompt}], timeout=30.0
        )
        if response is None:
            return "New Conversation"
        title = (response.get("content") or "New Conversation").strip().strip('"\'')
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    def _persist_user_message(
        self, conversation: Conversation, content: str, files: list[dict[str, Any]] | None
    ) -> UserMessage:
        attachments: list[FileAttachment] = []
        for f in files or []:
            name = f.get("name")
            raw_content = f.get("content")
            if not name or raw_content is None:
                continue
            reference_id = self._blob_store.save_text(str(raw_content))
            attachments.append(
                FileAttachment(name=str(name), reference_id=reference_id, size=f.get("size"))
            )

        msg = UserMessage(content=content, files=attachments)
        conversation.messages.append(msg)
        self._repo.save(conversation)
        return msg

    def _persist_assistant_message(
        self,
        conversation: Conversation,
        *,
        stage1: list[Stage1Result],
        stage2: list[Stage2Result],
        stage3: Stage3Result,
        metadata: AssistantMessageMetadata,
    ) -> AssistantMessage:
        conversation.messages.append(
            AssistantMessage(stage1=stage1, stage2=stage2, stage3=stage3, metadata=metadata)
        )
        conversation.has_unread = True
        self._repo.save(conversation)
        return conversation.messages[-1]  # type: ignore[return-value]

    async def run_message_events(
        self,
        *,
        conversation_id: str,
        content: str,
        files: list[dict[str, Any]] | None,
        target_model: str | None = None,
    ) -> AsyncIterator[CouncilEvent]:
        conversation = self._repo.get(conversation_id)
        if conversation is None:
            yield Error(message="Conversation not found")
            return

        is_first_message = len(conversation.messages) == 0
        user_msg = self._persist_user_message(conversation, content, files)
        prompt_content = self._build_prompt_content(user_msg.content, user_msg.files)

        title_task: asyncio.Task[str] | None = None
        if is_first_message:
            title_task = asyncio.create_task(self._generate_title(user_msg.content))

        try:
            # Follow-up path (Chairman only)
            if target_model == "chairman":
                stage3 = await self._run_chairman_followup(conversation, prompt_content)
                yield Stage3Start()
                yield Stage3Complete(data=stage3)
                self._persist_assistant_message(
                    conversation,
                    stage1=[],
                    stage2=[],
                    stage3=stage3,
                    metadata=AssistantMessageMetadata(),
                )
                if title_task:
                    title = await title_task
                    conversation.title = title
                    self._repo.save(conversation)
                    yield TitleComplete(data={"title": title})
                yield Complete()
                return

            stage1_results: list[Stage1Result] = []
            stage2_results: list[Stage2Result] = []
            stage3_result: Stage3Result | None = None
            metadata = AssistantMessageMetadata()

            async for event in self._run_council_events(prompt_content):
                if isinstance(event, Stage1Complete):
                    stage1_results = event.data
                elif isinstance(event, Stage2Complete):
                    stage2_results = event.data
                    metadata = event.metadata
                elif isinstance(event, Stage3Complete):
                    stage3_result = event.data
                yield event

            if stage3_result is None:
                yield Error(message="Internal error: missing stage3 result")
                return

            self._persist_assistant_message(
                conversation,
                stage1=stage1_results,
                stage2=stage2_results,
                stage3=stage3_result,
                metadata=metadata,
            )

            # If title generation was started, apply it after the council run.
            if title_task:
                title = await title_task
                conversation.title = title
                self._repo.save(conversation)
                yield TitleComplete(data={"title": title})

            yield Complete()

        except Exception as e:  # pragma: no cover (defensive)
            yield Error(message=str(e))

    async def _run_chairman_followup(
        self, conversation: Conversation, followup_query: str
    ) -> Stage3Result:
        # Find the most recent assistant message with stage3
        last_assistant: AssistantMessage | None = None
        last_user_query: str = "Unknown (Context from previous turn)"

        for idx in range(len(conversation.messages) - 1, -1, -1):
            msg = conversation.messages[idx]
            if isinstance(msg, AssistantMessage) and msg.stage3:
                last_assistant = msg
                if idx > 0 and isinstance(conversation.messages[idx - 1], UserMessage):
                    last_user_query = conversation.messages[idx - 1].content
                break

        if last_assistant is None:
            # No context found: fall back to a normal run-like answer.
            response = await self._llm.chat(
                self._config.chairman_model,
                [{"role": "user", "content": followup_query}],
            )
            return Stage3Result(
                model=self._config.chairman_model,
                response=(response or {}).get("content") or "Error: Unable to generate follow-up response.",
            )

        stage1_text = ""
        for r in last_assistant.stage1:
            status_info = "" if r.status == "success" else f" [STATUS: {r.status.upper()}]"
            stage1_text += f"Model: {r.model}{status_info}\nResponse: {r.response}\n\n"

        stage2_text = ""
        for r in last_assistant.stage2:
            status_info = "" if r.status == "success" else f" [STATUS: {r.status.upper()}]"
            stage2_text += f"Model: {r.model}{status_info}\nRanking: {r.ranking}\n\n"

        chairman_prompt = f"""You are the Chairman of an LLM Council. You have previously synthesized a response based on the council's input. The user now has a follow-up question.

Original Question: {last_user_query}

STAGE 1 - Individual Responses:
{stage1_text}

STAGE 2 - Peer Rankings:
{stage2_text}

Chairman's Initial Response:
{last_assistant.stage3.response}

User Follow-up Question: {followup_query}

Your task is to answer the follow-up question. You should:
- Maintain the persona of the Chairman (wise, synthesizing, authoritative but balanced).
- Refer back to the council's findings if relevant to the follow-up.
- If the follow-up challenges your previous conclusion, re-evaluate based on the evidence.
- Provide a direct and helpful answer.

Answer:"""

        response = await self._llm.chat(
            self._config.chairman_model, [{"role": "user", "content": chairman_prompt}]
        )
        if response is None:
            return Stage3Result(
                model=self._config.chairman_model,
                response="Error: Unable to generate follow-up response.",
            )
        return Stage3Result(model=self._config.chairman_model, response=response.get("content", ""))

    async def _run_council_events(self, user_query: str) -> AsyncIterator[CouncilEvent]:
        council_models = list(self._config.council_models)

        async def query_with_model(model: str, messages: list[dict[str, str]]):
            try:
                return model, await self._llm.chat(model, messages)
            except Exception:
                return model, None

        # Stage 1
        yield Stage1Start(total=len(council_models))
        stage1_messages = [{"role": "user", "content": user_query}]
        stage1_tasks = [
            asyncio.create_task(query_with_model(model, stage1_messages))
            for model in council_models
        ]
        stage1_responses: dict[str, dict[str, Any] | None] = {}
        completed = 0
        for task in asyncio.as_completed(stage1_tasks):
            model, response = await task
            stage1_responses[model] = response
            completed += 1
            yield Stage1Progress(completed=completed, total=len(council_models))

        stage1_results: list[Stage1Result] = []
        for model in council_models:
            resp = stage1_responses.get(model)
            if resp is not None:
                stage1_results.append(
                    Stage1Result(
                        model=model, response=resp.get("content", "") or "", status="success"
                    )
                )
            else:
                stage1_results.append(
                    Stage1Result(
                        model=model,
                        response="Error: Failed to get response from this model.",
                        status="error",
                    )
                )
        yield Stage1Complete(data=stage1_results)

        successful_stage1 = [r for r in stage1_results if r.status == "success"]
        if not successful_stage1:
            # No Stage 2 possible; return error Stage 3
            yield Stage3Start()
            yield Stage3Complete(
                data=Stage3Result(
                    model="error",
                    response="All models failed to respond. Please try again.",
                )
            )
            # Persist the assistant message via metadata-less Stage2Complete-equivalent state.
            # (Persistence happens in the interface layer after events are consumed.)
            return

        # Stage 2
        yield Stage2Start(total=len(council_models))
        labels = [chr(65 + i) for i in range(len(successful_stage1))]
        label_to_model = {
            f"Response {label}": result.model for label, result in zip(labels, successful_stage1)
        }
        responses_text = "\n\n".join(
            [
                f"Response {label}:\n{result.response}"
                for label, result in zip(labels, successful_stage1)
            ]
        )
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
        stage2_messages = [{"role": "user", "content": ranking_prompt}]
        stage2_tasks = [
            asyncio.create_task(query_with_model(model, stage2_messages))
            for model in council_models
        ]
        stage2_responses: dict[str, dict[str, Any] | None] = {}
        completed = 0
        for task in asyncio.as_completed(stage2_tasks):
            model, response = await task
            stage2_responses[model] = response
            completed += 1
            yield Stage2Progress(completed=completed, total=len(council_models))

        stage2_results: list[Stage2Result] = []
        stage2_results_for_aggregate: list[dict[str, Any]] = []
        for model in council_models:
            resp = stage2_responses.get(model)
            if resp is not None:
                full_text = resp.get("content", "") or ""
                parsed = parse_ranking_from_text(full_text)
                stage2_results.append(
                    Stage2Result(
                        model=model,
                        ranking=full_text,
                        parsed_ranking=parsed,
                        status="success",
                    )
                )
                stage2_results_for_aggregate.append(
                    {"model": model, "ranking": full_text, "parsed_ranking": parsed, "status": "success"}
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
                stage2_results_for_aggregate.append(
                    {"model": model, "ranking": "", "parsed_ranking": [], "status": "error"}
                )

        aggregate = calculate_aggregate_rankings(stage2_results_for_aggregate, label_to_model)
        metadata = AssistantMessageMetadata(
            label_to_model=label_to_model,
            aggregate_rankings=[AggregateRanking.model_validate(a) for a in aggregate],
        )
        yield Stage2Complete(data=stage2_results, metadata=metadata)

        # Stage 3
        yield Stage3Start()
        stage1_text = ""
        for r in stage1_results:
            status_info = "" if r.status == "success" else f" [STATUS: {r.status.upper()}]"
            stage1_text += f"Model: {r.model}{status_info}\nResponse: {r.response}\n\n"

        stage2_text = ""
        for r in stage2_results:
            status_info = "" if r.status == "success" else f" [STATUS: {r.status.upper()}]"
            stage2_text += f"Model: {r.model}{status_info}\nRanking: {r.ranking}\n\n"

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

        response = await self._llm.chat(
            self._config.chairman_model, [{"role": "user", "content": chairman_prompt}]
        )
        if response is None:
            yield Stage3Complete(
                data=Stage3Result(
                    model=self._config.chairman_model,
                    response="Error: Unable to generate final synthesis.",
                )
            )
        else:
            yield Stage3Complete(
                data=Stage3Result(
                    model=self._config.chairman_model,
                    response=response.get("content", "") or "",
                )
            )

