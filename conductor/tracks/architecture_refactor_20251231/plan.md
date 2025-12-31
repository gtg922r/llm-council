# Plan: Comprehensive Architectural Refactor (Hexagonal Architecture)

This plan follows the 5-phase refactor guide to move the application to a Modular Hexagonal architecture, improving persistence, performance, and testability.

## Phase 0: Preparation
- [x] Task: Clean existing data (Delete `data/conversations/` and `data/blobs/`) 2e15e4e
- [x] Task: Initialize new backend test infrastructure (Create `backend/tests/unit`, `backend/tests/integration`) 66242d0

## Phase 1: Domain Modeling & Metadata Persistence
- [x] Task: Define Pydantic models in `backend/domain/models.py` (Conversation, Message, CouncilRun) 65e3ccb
- [x] Task: Implement `metadata` field in `AssistantMessage` for peer rankings and label maps 65e3ccb
- [ ] Task: Update `council.py` logic to use and populate new Domain models
- [ ] Task: Update `storage.py` to handle Pydantic serialization/deserialization
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Domain Modeling & Metadata Persistence' (Protocol in workflow.md)

## Phase 2: The Blob-Store Split
- [ ] Task: Create `backend/infrastructure/blob_store.py` for local file persistence
- [ ] Task: Update `UserMessage` domain model to use `file_reference_id`
- [ ] Task: Refactor Prompt Builder to resolve `file_reference_id` via `BlobStore`
- [ ] Task: Update `storage.py` (or new repository) to save/load blobs during conversation persistence
- [ ] Task: Conductor - User Manual Verification 'Phase 2: The Blob-Store Split' (Protocol in workflow.md)

## Phase 3: Infrastructure Abstraction (The Repository Pattern)
- [ ] Task: Define abstract interfaces in `backend/ports.py` (`ConversationRepository`, `LLMProvider`)
- [ ] Task: Implement `backend/infrastructure/json_repository.py` (implements `ConversationRepository`)
- [ ] Task: Implement `backend/infrastructure/openrouter_adapter.py` (implements `LLMProvider`)
- [ ] Task: Refactor `main.py` routes to use Port interfaces (Dependency Injection)
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Infrastructure Abstraction (The Repository Pattern)' (Protocol in workflow.md)

## Phase 4: Service Layer Unification
- [ ] Task: Implement `backend/application/council_service.py` (`CouncilOrchestrator`)
- [ ] Task: Implement Domain Events (e.g., `StageStarted`, `ModelThinking`) as Pydantic models
- [ ] Task: Refactor service to be an Async Generator yielding Domain Events
- [ ] Task: Update FastAPI routes to consume `CouncilService` events for SSE and non-streaming responses
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Service Layer Unification' (Protocol in workflow.md)

## Phase 5: Frontend Alignment
- [ ] Task: Update `frontend/src/api.js` to handle standardized `AssistantMessage` structure
- [ ] Task: Update `ChatInterface.jsx` and components to display peer rankings from metadata
- [ ] Task: Refactor frontend state machine to handle explicit Domain Events from SSE
- [ ] Task: Conductor - User Manual Verification 'Phase 5: Frontend Alignment' (Protocol in workflow.md)
