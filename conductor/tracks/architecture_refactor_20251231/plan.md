# Plan: Comprehensive Architectural Refactor (Hexagonal Architecture)

This plan follows the 5-phase refactor guide to move the application to a Modular Hexagonal architecture, improving persistence, performance, and testability.

## Phase 0: Preparation
- [x] Task: Clean existing data (Delete `data/conversations/` and `data/blobs/`) 2e15e4e
- [x] Task: Initialize new backend test infrastructure (Create `backend/tests/unit`, `backend/tests/integration`) 66242d0

## Phase 1: Domain Modeling & Metadata Persistence [checkpoint: c15007a]
- [x] Task: Define Pydantic models in `backend/domain/models.py` (Conversation, Message, CouncilRun) 65e3ccb
- [x] Task: Implement `metadata` field in `AssistantMessage` for peer rankings and label maps 65e3ccb
- [x] Task: Update `council.py` logic to use and populate new Domain models 4877cc4
- [x] Task: Update `storage.py` to handle Pydantic serialization/deserialization 0940af9
- [x] Task: Conductor - User Manual Verification 'Phase 1: Domain Modeling & Metadata Persistence' (Protocol in workflow.md) c15007a

## Phase 2: The Blob-Store Split [checkpoint: 04512ab]
- [x] Task: Create `backend/infrastructure/blob_store.py` for local file persistence b024a83
- [x] Task: Update `UserMessage` domain model to use `file_reference_id` 6a8e847
- [x] Task: Refactor Prompt Builder to resolve `file_reference_id` via `BlobStore` 03a411b
- [x] Task: Update `storage.py` (or new repository) to save/load blobs during conversation persistence 6a8e847
- [x] Task: Conductor - User Manual Verification 'Phase 2: The Blob-Store Split' (Protocol in workflow.md) 04512ab

## Phase 3: Infrastructure Abstraction (The Repository Pattern)
- [x] Task: Define abstract interfaces in `backend/ports.py` (`ConversationRepository`, `LLMProvider`) fbc7c73
- [x] Task: Implement `backend/infrastructure/json_repository.py` (implements `ConversationRepository`) a535146
- [x] Task: Implement `backend/infrastructure/openrouter_adapter.py` (implements `LLMProvider`) 5968f29
- [x] Task: Refactor `main.py` routes to use Port interfaces (Dependency Injection) 3cf8790
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
