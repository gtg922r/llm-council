# Plan: Comprehensive Architectural Refactor (Hexagonal Architecture)

This plan follows the 5-phase refactor guide to move the application to a Modular Hexagonal architecture, improving persistence, performance, and testability.

## Phase 0: Preparation
- [x] Task: Clean existing data (Delete `data/conversations/` and `data/blobs/`)
- [x] Task: Initialize new backend test infrastructure (Create `backend/tests/unit`, `backend/tests/integration`)

## Phase 1: Domain Modeling & Metadata Persistence
- [x] Task: Define Pydantic models in `backend/domain/models.py` (Conversation, Message, CouncilRun)
- [x] Task: Implement `metadata` field in `AssistantMessage` for peer rankings and label maps
- [x] Task: Update `council.py` logic to use and populate new Domain models
- [x] Task: Update `storage.py` to handle Pydantic serialization/deserialization
- [x] Task: Conductor - User Manual Verification 'Phase 1: Domain Modeling & Metadata Persistence' (Protocol in workflow.md)

## Phase 2: The Blob-Store Split
- [x] Task: Create `backend/infrastructure/blob_store.py` for local file persistence
- [x] Task: Update `UserMessage` domain model to use `file_reference_id`
- [x] Task: Refactor Prompt Builder to resolve `file_reference_id` via `BlobStore`
- [x] Task: Update `storage.py` (or new repository) to save/load blobs during conversation persistence
- [x] Task: Conductor - User Manual Verification 'Phase 2: The Blob-Store Split' (Protocol in workflow.md)

## Phase 3: Infrastructure Abstraction (The Repository Pattern)
- [x] Task: Define abstract interfaces in `backend/ports.py` (`ConversationRepository`, `LLMProvider`)
- [x] Task: Implement `backend/infrastructure/json_repository.py` (implements `ConversationRepository`)
- [x] Task: Implement `backend/infrastructure/openrouter_adapter.py` (implements `LLMProvider`)
- [x] Task: Refactor `main.py` routes to use Port interfaces (Dependency Injection)
- [x] Task: Conductor - User Manual Verification 'Phase 3: Infrastructure Abstraction (The Repository Pattern)' (Protocol in workflow.md)

## Phase 4: Service Layer Unification
- [x] Task: Implement `backend/application/council_service.py` (`CouncilOrchestrator`)
- [x] Task: Implement Domain Events (e.g., `StageStarted`, `ModelThinking`) as Pydantic models
- [x] Task: Refactor service to be an Async Generator yielding Domain Events
- [x] Task: Update FastAPI routes to consume `CouncilService` events for SSE and non-streaming responses
- [x] Task: Conductor - User Manual Verification 'Phase 4: Service Layer Unification' (Protocol in workflow.md)

## Phase 5: Frontend Alignment
- [x] Task: Update `frontend/src/api.js` to handle standardized `AssistantMessage` structure
- [x] Task: Update `ChatInterface.jsx` and components to display peer rankings from metadata
- [x] Task: Refactor frontend state machine to handle explicit Domain Events from SSE
- [x] Task: Conductor - User Manual Verification 'Phase 5: Frontend Alignment' (Protocol in workflow.md)

## Completion Summary

All phases have been successfully completed. The architecture refactor achieved the following goals:

### Key Accomplishments

1. **Domain Layer** (`backend/domain/`):
   - Created comprehensive Pydantic models for `Conversation`, `UserMessage`, `AssistantMessage`
   - Added `CouncilMetadata` with `label_to_model` and `aggregate_rankings` (fixes persistence amnesia)
   - Defined domain events for the event-driven architecture

2. **Infrastructure Layer** (`backend/infrastructure/`):
   - `BlobStore`: Content-addressable storage for file attachments
   - `JsonConversationRepository`: Implements `ConversationRepository` port
   - `OpenRouterAdapter`: Implements `LLMProvider` port

3. **Application Layer** (`backend/application/`):
   - `CouncilService`: Unified orchestrator yielding domain events
   - Single code path for both streaming and non-streaming responses

4. **Interface Layer** (`backend/main.py`):
   - Dependency injection via FastAPI's `Depends()`
   - No direct file system or API-specific logic
   - Routes consume service events for SSE/JSON responses

5. **Tests**:
   - 71 tests passing (33 unit tests + 38 integration/existing tests)
   - Coverage of domain models, blob store, repository, and council service

### Acceptance Criteria Met

- ✅ Metadata (rankings, label mappings) persists across page reloads
- ✅ File attachments stored in `data/blobs/`, keeping conversation JSON small
- ✅ `backend/main.py` contains no direct file system or OpenRouter-specific logic
- ✅ Frontend correctly displays metadata from persisted assistant messages
- ✅ All backend tests pass
