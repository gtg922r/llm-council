## Architecture Review (LLM Council)

This review focuses on:
- **Data flow**: how a new user message is processed end-to-end (frontend → backend → OpenRouter → response → storage → UI).
- **Data storage**: what is stored where (browser vs backend), what is ephemeral, and what is lost across reloads.

## 1. Current architecture (concise)

### 1A. Data flow (new request/message)

- **Conversation lifecycle**
  - **Create**: `POST /api/conversations` creates a conversation ID and persists a JSON file in `data/conversations/{id}.json`.
  - **List**: `GET /api/conversations` returns metadata (id, title, flags, message_count).
  - **Load**: `GET /api/conversations/{id}` returns the full conversation JSON (messages included).

- **Default “Council” message send (streaming path)**
  - **Frontend** (`frontend/src/App.jsx`):
    - Optimistically appends a **user message** to UI state.
    - Appends a placeholder **assistant message** with per-stage loading/progress fields.
    - If files are attached, reads them in-browser and **concatenates file contents into the prompt string** sent to the backend (while showing only filename “chips” in the UI).
    - Calls `POST /api/conversations/{id}/message/stream` and consumes Server-Sent Events (SSE).
    - Uses SSE events to incrementally fill `stage1`, `stage2`, `stage3`, and `metadata` into the last assistant message.
  - **Backend** (`backend/main.py`, streaming handler):
    - Immediately persists the **user message** to storage (`storage.add_user_message`).
    - Runs:
      - **Stage 1**: parallel OpenRouter calls for each model, emitting progress events.
      - **Stage 2**: builds an anonymized “Response A/B/…” prompt, parallel OpenRouter calls for each model, parses rankings, computes aggregate rankings, emits results + metadata.
      - **Stage 3**: chairman synthesizes final answer, emits final result.
    - Generates a conversation title (first message only) concurrently, persists it, emits a `title_complete` event.
    - Persists the **assistant message** (stage1/stage2/stage3) at the end of the stream.

- **Non-streaming message send (batch path)**
  - `POST /api/conversations/{id}/message`:
    - Persists user message, generates title for first message, runs `run_full_council()` (stage1 → stage2 → aggregate → stage3), persists assistant message, returns `{stage1, stage2, stage3, metadata}`.

- **Chairman follow-up path**
  - Frontend uses the **non-streaming** endpoint with `target_model: "chairman"`.
  - Backend:
    - Persists the follow-up user message.
    - Locates the most recent assistant message that includes `stage3` and uses it as context.
    - Runs `chairman_followup()` and persists an assistant message where `stage1=[]` and `stage2=[]` (stage3 only).

### 1B. Data storage (where data lives today)

- **Backend (source of persistence)**
  - Storage is **JSON files** in `data/conversations/` (one file per conversation).
  - Each conversation stores:
    - Metadata: `id`, `created_at`, `title`, `is_pinned`, `is_archived`
    - Messages array with:
      - User: `{ role: "user", content: string }`
      - Assistant: `{ role: "assistant", stage1: [...], stage2: [...], stage3: {...} }`
  - **Notably not persisted**:
    - The API-level `metadata` object (`label_to_model`, `aggregate_rankings`) is returned for batch and streamed in SSE for the default flow, but it is **not saved** in the conversation JSON.

- **Browser / frontend**
  - Conversation state is held in **React state only** (in-memory). There is no local persistence (no LocalStorage/IndexedDB).
  - The UI stores additional transient fields on assistant messages (loading/progress and metadata) that are **not part of the persisted backend schema**.
  - **File attachments are not stored as structured data**:
    - The UI shows file chips and stores only filename/size in the optimistic UI message.
    - The backend receives a single `content` string (often containing the concatenated file contents) and stores it as plain message text.
    - On reload, the conversation is rehydrated from backend JSON, so file “chips” disappear and the user message text may now include the full file contents inline.

## 2. Proposed refactor (toward idiomatic, elegant architecture)

This is intentionally staged: you can adopt the “minimal refactor” first (high leverage, low risk), then evolve storage and streaming as needed.

### 2A. Data flow refactor

- **Unify “batch” and “streaming” as one orchestration pipeline**
  - Today, the streaming endpoint re-implements stage logic that also exists in `backend/council.py`.
  - Recommended structure:
    - A single domain/service method (e.g., `CouncilOrchestrator.run(query, options)`) that yields **typed stage events** (start/progress/complete) and a final result.
    - The batch endpoint consumes the generator to completion and returns the final aggregated response.
    - The streaming endpoint maps the same events to SSE messages.
  - Benefit: one source of truth for stage execution, consistent behavior and easier feature additions.

- **Introduce stable identifiers for messages and processing**
  - Add `message_id`, `created_at`, and `type` (user/assistant) to each message.
  - For streaming:
    - Persist an **assistant placeholder message** immediately (e.g., `{status: "running"}`) and stream updates keyed by `message_id`.
    - Update the stored assistant message incrementally or at least mark completion deterministically.
  - Benefit: idempotency, simpler UI reconciliation, and easier “resume after refresh” behavior.

- **Make follow-ups first-class and consistent**
  - Avoid “search backward for last assistant with stage3” logic as the main linkage mechanism.
  - Store `in_reply_to_message_id` on each message so follow-ups are explicitly connected to the prior assistant response they reference.
  - Optional: support a “stage3-only streaming follow-up” endpoint so the UI doesn’t switch to a different transport model for follow-ups.

- **Clarify the boundary between “user text” and “LLM prompt”**
  - Right now, the UI mutates the “content” sent to the backend by appending file contents. This blurs meaning and causes confusing persistence.
  - Recommended: send a structured payload:
    - `user_text`: what the user typed
    - `attachments`: metadata + (optionally) extracted text content
    - `prompt_strategy`: how attachments should be incorporated
  - The backend is responsible for prompt assembly and stores both:
    - the original user text
    - the attachment references / extracted content (as appropriate)
    - (optionally) the final prompt for debugging in a gated, safe manner

### 2B. Data storage refactor

- **Persist everything needed to faithfully render a conversation**
  - Persist assistant-side `metadata` that the UI currently relies on but loses after reload:
    - `label_to_model`
    - `aggregate_rankings`
    - (optionally) `parsed_ranking` if you want it treated as a derived-but-stored field
  - Principle: if the UI renders it and it matters for user understanding, it should be in backend storage (unless explicitly “ephemeral by design”).

- **Replace JSON-file storage with a small, robust database when ready**
  - JSON files are fine for a hack/prototype, but they are brittle for concurrency, partial writes, indexing, and evolution.
  - A very idiomatic next step is **SQLite** with a lightweight ORM (or even raw SQL):
    - Tables: `conversations`, `messages`, `attachments`
    - Index by `conversation_id`, `created_at`
    - Store stage payloads as JSON columns (or normalized tables later if needed)
  - If you keep JSON for now, introduce a “storage adapter” interface so the rest of the app doesn’t care which backend is used.

- **Model versioning / migrations**
  - Add a `schema_version` to persisted conversation/message records.
  - Provide a tiny migration path (even a one-time upgrade script) so future structural changes don’t break old conversations.

- **Attachment storage**
  - Store attachments as structured objects:
    - `id`, `name`, `size`, `mime`, `text_extracted` (optional), `hash` (optional), `created_at`
  - Decide policy:
    - For local-only usage, storing extracted text in SQLite is fine.
    - For larger files, store extracted text separately (filesystem/object store) and keep only references in DB.
  - This avoids polluting user messages with “inline file dumps” and preserves UX fidelity across reload.

## 3. Architecture guidelines & principles for future development

These guidelines are intentionally biased toward “small app done well”: clear boundaries, simple data models, and low-friction iteration.

### 3A. Data flow principles

- **Single source of truth**
  - The backend is the system of record for conversations and messages.
  - The frontend may be optimistic, but it must reconcile to server IDs and server state.

- **One orchestration engine, multiple transports**
  - Batch and streaming must be different *presentations* of the same underlying workflow (no duplicated business logic).
  - Streaming should emit domain events; the UI is a projection of those events.

- **Explicit contracts**
  - Use typed request/response models (Pydantic) for all endpoints.
  - Avoid “stringly-typed” flags that create hidden branches (e.g., prefer `mode: "council" | "chairman_followup"` to ad-hoc `target_model` semantics).

- **Idempotency + correlation**
  - Add `request_id` / `message_id` and carry it through logs and events.
  - Make “retry” safe where possible (especially for streaming reconnects).

- **Separation of concerns**
  - Domain logic (`council` orchestration) should not know about HTTP/SSE details.
  - Storage code should be behind a repository/adapter boundary.

### 3B. Data storage principles

- **Persist what you render**
  - If the UI displays derived metadata (rank mappings, aggregates), persist it with the assistant message.
  - If something is ephemeral, mark it explicitly as such and ensure the UI degrades gracefully.

- **Preserve meaning**
  - Store user-authored text separately from system-generated prompt expansions (like file contents).
  - Store attachments as structured data; don’t embed large blobs in message text by default.

- **Schema evolution is a feature**
  - Always version persisted schemas.
  - Prefer additive changes and provide migrations.

- **Security and privacy by default**
  - Never persist secrets (API keys) or log sensitive prompt material unintentionally.
  - If you store prompts for debugging, gate it behind a config flag and redact aggressively.

