# Architecture Review: LLM Council

## 1. Current Architecture

### Overview
LLM Council is a web-based application that orchestrates a "council" of multiple LLMs to answer user queries, peer-review each other, and synthesize a final answer.

### Backend (`backend/`)
- **Framework**: FastAPI with Uvicorn.
- **Orchestration**: `council.py` manages a 3-stage process:
    1.  **Stage 1 (Drafting)**: Parallel queries to multiple models (defined in `config.py`).
    2.  **Stage 2 (Peer Review)**: Responses are anonymized (labeled A, B, C...) and sent back to all models for ranking and critique.
    3.  **Stage 3 (Synthesis)**: A "Chairman" model synthesizes a final answer based on all drafts and reviews.
- **Concurrency**: Heavy use of `asyncio` for parallel model queries.
- **Streaming**: Uses Server-Sent Events (SSE) to stream progress and partial results to the frontend.
- **Storage**: File-system based JSON storage. Each conversation is a separate `.json` file in `data/conversations/`.
    - **Data Model**: `{ id, created_at, title, messages: [ { role, content, stage1, stage2, stage3 } ] }`

### Frontend (`frontend/src/`)
- **Framework**: React (Vite).
- **State Management**: Local component state (`useState`) in `App.jsx` pushed down to components.
- **Communication**: REST API for CRUD, SSE for streaming message generation.
- **De-anonymization**: The frontend receives a `label_to_model` mapping in the API response metadata to reveal which model wrote "Response A" etc.

### Critical Finding: Data Loss
Currently, the `metadata` (specifically `label_to_model` mapping and `aggregate_rankings`) is **NOT persisted** in the backend storage.
- It is calculated on-the-fly during the request.
- It is sent to the frontend via the SSE stream or API response.
- The frontend uses it for the current session.
- **Impact**: If a user reloads the page or re-opens a conversation later, the de-anonymization mapping is lost (unless the frontend can deterministically reconstruct it, which depends on stable sorting of Stage 1 results). The `aggregate_rankings` are also lost and must be re-calculated or are missing.

---

## 2. Proposed Refactor

### Priority 1: Persist Metadata (Fix Data Loss)
The `label_to_model` mapping is essential for the "transparency" feature of the app. It must be saved.

**Refactor Plan:**
1.  **Update Data Model**: Modify the message schema in `storage.py` (and the underlying JSON structure) to include a `metadata` field.
    ```python
    # Old
    { "role": "assistant", "stage1": [...], "stage2": [...], "stage3": {...} }
    
    # New
    { "role": "assistant", "stage1": [...], "stage2": [...], "stage3": {...}, "metadata": {...} }
    ```
2.  **Update Storage Logic**: Modify `storage.add_assistant_message` to accept and save `metadata`.
3.  **Update Controller**: Pass the generated metadata from `council.py` to `storage.add_assistant_message` in `main.py`.

### Priority 2: Improve Configuration
Currently, models are hardcoded in `config.py`.
- **Refactor**: Move model configuration to a `models.json` or allow environment-based configuration to make it easier to swap models without code changes.

### Priority 3: Robust Logging
Replace `print()` statements in `openrouter.py` and `main.py` with the standard `logging` module to allow for better debugging and error tracking in production/remote environments.

---

## 3. Architecture Guidelines

### Data Flow & Persistence
1.  **Complete State Persistence**: Any data required to fully reconstruct the UI state for a conversation **must** be persisted in the backend storage. Do not rely on ephemeral API responses for critical context (like the `label_to_model` map).
2.  **Deterministic Reconstruction**: If data is derived (like aggregate rankings), either persist it or ensure the inputs (Stage 2 rankings) are stored in a way that guarantees the same derivation every time. Persistence is preferred for performance and stability.
3.  **Immutable History**: Once a council session (message turn) is complete, its data (Stage 1/2/3 outputs) should be treated as immutable.

### API & Communication
1.  **Streaming First**: For long-running LLM processes, always prefer streaming (SSE) over blocking requests to provide immediate user feedback.
2.  **Graceful Degradation**: The system currently handles individual model failures gracefully (continuing with successful ones). This is a core principle—never fail the whole request because one sub-component (model) failed.

### Code Style & Structure
1.  **Service Isolation**: Keep the "Council" logic (`council.py`) separate from the Web/API logic (`main.py`) and the Persistence logic (`storage.py`).
2.  **Type Safety**: Continue using Pydantic models for API contracts (`BaseModel`) to ensure data validity.
