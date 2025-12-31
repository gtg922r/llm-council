# Specification: Comprehensive Architectural Refactor (Hexagonal Architecture)

## Overview
This track implements a full architectural overhaul of the LLM-Council application, moving from a script-based monolith to a Modular Hexagonal (Ports & Adapters) architecture as defined in `ARCHITECTURE_REFACTOR.md`. The goal is to decouple business logic from infrastructure, fix the "persistence amnesia" bug, and improve long-term maintainability and testability.

## Goals
- **Decoupling:** Separate Domain logic, Application orchestration, Infrastructure adapters, and API interfaces.
- **Persistence Fix:** Ensure peer rankings and anonymized labels are saved in conversation metadata and persist across reloads.
- **Performance:** Implement a "Blob Store" to handle large file attachments separately from the main conversation JSON.
- **Testability:** Enable unit testing of the "Council" logic without requiring live API calls.
- **Consistency:** Unify streaming and non-streaming logic into a single Service layer.

## Functional Requirements

### Phase 1: Domain Modeling & Metadata
- Define Pydantic models in `backend/domain/models.py` for `Conversation`, `Message`, and `CouncilRun`.
- Add a `metadata` field to `AssistantMessage` to store `anonymized_label_map` and `aggregate_rankings`.
- Update logic to populate and persist this metadata.

### Phase 2: Blob-Store Split
- Implement `backend/infrastructure/blob_store.py` for local file storage.
- Update `UserMessage` to store `file_reference_id` instead of raw content.
- Refactor Prompt Builder to fetch content from the Blob Store.

### Phase 3: Infrastructure Abstraction (Repository Pattern)
- Define abstract interfaces in `backend/ports.py` for `ConversationRepository` and `LLMProvider`.
- Implement `JsonConversationRepository` and `OpenRouterAdapter`.
- Inject these dependencies into FastAPI routes via the Application layer.

### Phase 4: Service Layer Unification
- Create `CouncilService` to orchestrate the multi-stage workflow.
- Implement an Event-Driven architecture where the service yields domain events (e.g., `StageStarted`, `ModelThinking`).
- Update FastAPI routes to consume these events for both SSE and standard responses.

### Phase 5: Frontend Alignment
- Update the React frontend to handle the standardized `AssistantMessage` and its metadata.
- Refactor frontend state management to react to the new Domain Events.

## Non-Functional Requirements
- **Test-Driven Development:** Update and restructure the test suite (`backend/tests/`) to match the new layers.
- **Statelessness:** Ensure the Application layer remains stateless, relying on repositories for persistence.
- **Type Safety:** Strict use of Pydantic and type hints throughout the backend.

## Acceptance Criteria
- A full council run completes, and refreshing the page retains all rankings and label mappings.
- Large files attached to messages are stored as individual files in `data/blobs/`, keeping the conversation JSON small.
- The `backend/main.py` file contains no direct file system or OpenRouter-specific logic.
- The frontend correctly displays the progress of each stage using the new event stream.
- All backend tests pass in the new architecture.

## Out of Scope
- Migration of existing conversation data (starting with a clean `data/` directory).
- Introduction of new LLM providers or database engines (e.g., SQL/NoSQL).
- Major UI redesigns.
