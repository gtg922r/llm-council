# LLM Council Architecture

This document describes the current architecture and data flow of the LLM Council application, with emphasis on how intent and data move from the frontend to the backend, to external APIs and storage, and back.

## High-Level Overview

LLM Council is a 3-stage deliberation system implemented as:

- A React frontend (Vite) in `frontend/` that manages conversations, file uploads, and presentation of the three stages.
- A FastAPI backend in `backend/` that orchestrates model calls, performs anonymized peer review, and persists conversation history to JSON files.
- An external LLM provider (OpenRouter) that supplies all model responses.

The system is intentionally split into three stages:

1. **Stage 1**: Collect responses from a fixed set of council models in parallel.
2. **Stage 2**: Ask the same models to rank the Stage 1 responses, using anonymized labels.
3. **Stage 3**: A chairman model synthesizes the final answer using all prior context.

A separate “Chairman follow-up” path skips Stages 1 and 2 and only asks the chairman model to respond with the previous context.

## Top-Level Data Flow

### Conversation List and Metadata

- **Frontend** calls `GET /api/conversations` to fetch a list of conversation metadata.
- **Backend** reads `data/conversations/*.json`, extracts metadata (id, title, flags, count), and returns a sorted list.
- **Frontend** stores this in memory state (`App.jsx`) and renders it in the sidebar.

### Create Conversation

- **Frontend** calls `POST /api/conversations`.
- **Backend** creates a JSON file in `data/conversations/` with an empty messages list and returns the full conversation object.
- **Frontend** inserts the new conversation into local state and marks it active.

### Send Message (Default Council Flow)

1. **Frontend** reads file contents in the browser using `FileReader` and creates a payload:
   - `content`: user text
   - `files`: list of `{name, content, size}`
2. **Frontend** calls `POST /api/conversations/{id}/message/stream` for streaming results by default.
3. **Backend** stores the user message in the JSON file, including any file content.
4. **Backend** assembles the prompt by appending file blocks:
   - `--- FILE: name ---` + file content + `--- END FILE: name ---`
5. **Backend** runs the 3-stage process, streaming progress as Server-Sent Events (SSE):
   - Stage 1 start/progress/complete
   - Stage 2 start/progress/complete (including metadata)
   - Stage 3 start/complete
   - Title generation (only on first message)
   - Completion
6. **Frontend** consumes SSE events and updates the current conversation message in-place (showing progress and results as each stage arrives).
7. **Backend** stores the final assistant message in the JSON file (stage1, stage2, stage3).

### Send Message (Non-Streaming)

- **Frontend** uses `POST /api/conversations/{id}/message` for a non-streaming response.
- **Backend** runs the full council flow and returns a single response object that includes:
  - `stage1`: list of model responses
  - `stage2`: list of model evaluations and parsed rankings
  - `stage3`: chairman response
  - `metadata`: `label_to_model` and `aggregate_rankings`
- **Backend** stores the assistant message (stage1/2/3) in JSON; metadata is *not* persisted.
- **Frontend** attaches `metadata` to the in-memory message only.

### Chairman Follow-Up Flow

- Triggered when the user clicks “Send Message to Chairman” (frontend sets `target_model = "chairman"`).
- **Frontend** calls `POST /api/conversations/{id}/message` (non-streaming) with `target_model`.
- **Backend** finds the most recent assistant message and extracts:
  - original user query (best-effort)
  - stored stage1, stage2, and stage3 content
- **Backend** sends a single follow-up prompt to the chairman model and returns only stage3.
- **Backend** stores this assistant message with empty stage1/stage2 arrays.

## Backend Architecture

### Entry Point

- `backend/main.py` defines the FastAPI app, routes, CORS, and SSE endpoint.
- Runs on port 8001 via `uvicorn` (see `backend/main.py`).

### Core Modules

- `backend/config.py`
  - Defines `COUNCIL_MODELS` and `CHAIRMAN_MODEL`.
  - Loads `OPENROUTER_API_KEY` from `.env`.
  - Defines the OpenRouter API base URL and data directory.

- `backend/openrouter.py`
  - `query_model`: makes a single POST to OpenRouter, returns `{content, reasoning_details}`.
  - `query_models_parallel`: runs `query_model` for multiple models via `asyncio.gather`.

- `backend/council.py`
  - `stage1_collect_responses`: parallel council model answers.
  - `stage2_collect_rankings`: anonymizes and asks for ranking; parses ranking.
  - `stage3_synthesize_final`: chairman synthesis.
  - `calculate_aggregate_rankings`: compute average position per model.
  - `generate_conversation_title`: separate LLM call for a short title.
  - `run_full_council`: orchestrates all three stages.
  - `chairman_followup`: follow-up with prior context.

- `backend/storage.py`
  - JSON-based persistence in `data/conversations/`.
  - Each conversation is a file `{id}.json` with full message history.
  - Provides CRUD for conversations and message append operations.

### Backend Data Flow Details

#### Stage 1

- Inputs: user prompt (including file blocks).
- Calls OpenRouter in parallel for all `COUNCIL_MODELS`.
- Produces `stage1` list: `{model, response, status}` per model.

#### Stage 2

- Inputs: `stage1` responses + user query.
- Anonymizes successful results as `Response A`, `Response B`, etc.
- Creates `label_to_model` mapping for de-anonymization.
- Asks each model to critique and rank all responses.
- Parses the `FINAL RANKING` section to extract `parsed_ranking`.
- Produces `stage2` list: `{model, ranking, parsed_ranking, status}`.

#### Stage 3

- Inputs: `stage1` and `stage2` content + original query.
- Builds a “chairman prompt” that includes all responses and rankings.
- Calls the `CHAIRMAN_MODEL` once to synthesize the final response.

#### Metadata Handling

- `label_to_model` and `aggregate_rankings` are computed in memory.
- Metadata is returned to the frontend but is **not** persisted in the JSON store.
- As a result, any UI features relying on metadata are only available immediately after a request and are not available when reloading historical conversations from disk.

### Conversation Storage

Conversations are stored in `data/conversations/{id}.json` with a structure like:

```json
{
  "id": "...",
  "created_at": "...",
  "title": "...",
  "is_pinned": false,
  "is_archived": false,
  "has_unread": false,
  "messages": [
    {
      "role": "user",
      "content": "...",
      "files": [{"name": "...", "content": "...", "size": 123}]
    },
    {
      "role": "assistant",
      "stage1": [...],
      "stage2": [...],
      "stage3": {"model": "...", "response": "..."}
    }
  ]
}
```

Notes:

- User messages persist any attached file contents. There is no separate storage for attachments.
- Assistant messages persist only stage content, not metadata.
- Title updates are stored to the same JSON file.

## Frontend Architecture

### Entry Points

- `frontend/src/main.jsx` mounts the app.
- `frontend/src/App.jsx` orchestrates state, API calls, and user actions.

### State Management

State is held entirely in memory using React `useState` and `useEffect`.

- `conversations`: list of conversation metadata (sidebar)
- `currentConversation`: active conversation (full message history)
- `pendingConversationIds`: tracks requests in flight
- `loadingConversationId`: controls UI loading states

There is no browser persistence of messages or metadata. The only persistent browser data is theme preference (see below).

### API Client

- `frontend/src/api.js` wraps REST and SSE calls to the backend.
- Streaming updates use `fetch` with `ReadableStream` parsing of `text/event-stream`.

### Message Send Flow (Frontend)

1. User types input or attaches files.
2. Files are read locally with `FileReader` and passed to API as text.
3. UI immediately appends a user message and a placeholder assistant message.
4. Streaming events update that assistant message in place:
   - Stage 1/2/3 data
   - Progress and loading flags
   - Metadata (only present in streaming event or non-stream response)
5. On completion, the UI refreshes the conversation list and clears pending flags.

### File Handling (Frontend)

- File uploads are text-only and validated client-side for:
  - Extension allowlist
  - Maximum size of 1MB
- Files are not uploaded as binary; they are read into memory and sent as strings.

### Theme Storage

- `ThemeContext` stores the user’s theme selection in `localStorage` under `llm-council-theme`.
- The theme is applied as a document `data-theme` attribute and `dark` class toggle.

## External Dependencies and APIs

### OpenRouter

- All LLM calls are made via OpenRouter at `https://openrouter.ai/api/v1/chat/completions`.
- Each request includes `model` and `messages`.
- Responses are assumed to contain `choices[0].message.content`.

### Browser APIs

- `FileReader` for text file ingestion.
- `fetch` for HTTP and SSE streaming.
- `localStorage` for theme persistence.

## Network and Deployment Considerations

- Backend listens on port `8001`.
- Frontend expects the backend on the same origin by default (`API_BASE = ''`).
- CORS is configurable:
  - In Codespaces or DEBUG mode, wildcard origins are allowed.
  - In production, only `http://localhost:5173` and `http://localhost:3000` are allowed.

## Error Handling and Resilience

- OpenRouter failures are handled per-model; failures return `None` and are captured as error statuses.
- Stage 1 and Stage 2 continue even if some models fail.
- If *all* models fail in Stage 1, Stage 2/3 are skipped and a failure response is returned.
- Streaming endpoint emits an `error` event for exceptions; non-streaming returns HTTP error codes.

## Summary of Where Data Lives

### Browser

- **In-memory state**: conversations, current conversation, stage results, metadata.
- **Persistent storage**: theme preference in `localStorage`.
- **Not persisted**: conversation contents, metadata, or message history.

### Backend

- **File-based storage**: `data/conversations/*.json` contains all conversation history, including user messages, assistant stages, and file contents.
- **Not persisted**: label/model mapping and aggregate rankings (metadata) are returned to the frontend only.

### External

- **OpenRouter**: all LLM requests and responses flow through OpenRouter’s API. The backend sends user content and file content in the prompt payload.

## Sequence Diagram (Narrative)

1. User creates a new conversation (frontend → backend → JSON file created).
2. User submits message with optional files (frontend reads files → backend stores full user message and builds prompt).
3. Backend calls OpenRouter in parallel for Stage 1 responses.
4. Backend anonymizes responses and calls OpenRouter for Stage 2 rankings.
5. Backend computes aggregate rankings and calls OpenRouter for Stage 3 synthesis.
6. Backend stores the assistant response in JSON and returns results (or streams them) to the frontend.
7. Frontend updates UI with each stage and renders final answer.
8. When the conversation is reloaded, backend returns only stored data (no metadata).

