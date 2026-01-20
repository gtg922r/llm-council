# Current Architecture: Hexagonal (Ports & Adapters)

**Status:** ✅ Fully Implemented  
**Date:** January 2026

---

## Architecture Overview

The LLM Council backend now follows a clean **Hexagonal Architecture** (Ports & Adapters) pattern. This decouples business logic from infrastructure, enabling testability and future portability.

```
┌─────────────────────────────────────────────────────────────────┐
│                     Interface Layer                              │
│                   backend/main.py                                │
│              (FastAPI routes - HTTP only)                        │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Application Layer                             │
│               backend/application/                               │
│  ┌────────────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │ council_service.py │  │ prompts.py    │  │ prompt_builder  │ │
│  │ (Orchestrator)     │  │ (Templates)   │  │ (Content Builder)│ │
│  └────────────────────┘  └───────────────┘  └─────────────────┘ │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Domain Layer                                │
│                   backend/domain/                                │
│  ┌────────────────────┐  ┌───────────────────────────────────┐  │
│  │ models.py          │  │ council_logic.py                   │  │
│  │ (Pydantic Models)  │  │ (Pure Functions: parse, calculate) │  │
│  └────────────────────┘  └───────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Ports                                     │
│                    backend/ports.py                              │
│  ┌──────────────────────────┐  ┌───────────────────────────┐    │
│  │ ConversationRepository   │  │ LLMProvider               │    │
│  │ (Abstract Interface)     │  │ (Abstract Interface)      │    │
│  └──────────────────────────┘  └───────────────────────────┘    │
└───────────────────────────┬─────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────────┐
│                   Infrastructure Layer                           │
│                backend/infrastructure/                           │
│  ┌────────────────────┐  ┌───────────────┐  ┌─────────────────┐ │
│  │ json_repository.py │  │ openrouter_   │  │ blob_store.py   │ │
│  │ (JSON Files)       │  │ adapter.py    │  │ (File Storage)  │ │
│  └────────────────────┘  └───────────────┘  └─────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

---

## Layer Details

### 1. Interface Layer (`backend/main.py`)

**Responsibility:** HTTP request/response handling only.

- FastAPI routes for REST API
- Request validation via Pydantic
- Converts between HTTP and domain events
- Dependency injection of services

**Key Principle:** No business logic. Routes only call the Orchestrator.

### 2. Application Layer (`backend/application/`)

**Responsibility:** Orchestration of the council workflow.

| Module | Purpose |
|--------|--------|
| `council_service.py` | **CouncilOrchestrator** - Single source of truth for all council workflow logic. Runs 3-stage process, emits domain events. |
| `prompts.py` | Pure functions for building LLM prompts. No I/O, no async. |
| `prompt_builder.py` | Builds user prompt content with file attachments. |

**Key Principle:** The Orchestrator is an async generator that yields domain events (`StageStarted`, `StageCompleted`, etc.).

### 3. Domain Layer (`backend/domain/`)

**Responsibility:** Pure business logic and data models.

| Module | Purpose |
|--------|--------|
| `models.py` | Pydantic models: `Conversation`, `Message`, `Stage1Result`, `Stage2Result`, `AssistantMetadata`, etc. |
| `council_logic.py` | Pure functions: `parse_ranking_from_text()`, `calculate_aggregate_rankings()` |

**Key Principle:** No async, no I/O, no external dependencies. Pure Python only.

### 4. Ports (`backend/ports.py`)

**Responsibility:** Define abstract interfaces for external dependencies.

```python
class ConversationRepository(ABC):
    def get(id) -> Conversation
    def save(conversation) -> None
    def list() -> List[Metadata]
    def delete(id) -> None

class LLMProvider(ABC):
    async def chat(model, messages) -> Dict
    async def stream_chat(model, messages) -> AsyncGenerator
```

**Key Principle:** Business logic depends on these interfaces, not on concrete implementations.

### 5. Infrastructure Layer (`backend/infrastructure/`)

**Responsibility:** Concrete implementations of ports.

| Module | Implements | External System |
|--------|------------|----------------|
| `json_repository.py` | `ConversationRepository` | Local JSON files |
| `openrouter_adapter.py` | `LLMProvider` | OpenRouter API |
| `blob_store.py` | - | Local file storage for attachments |

**Key Principle:** Easily swappable. Can replace `JsonRepository` with `FirestoreRepository` without changing business logic.

---

## Data Flow

```
User HTTP Request
      │
      ▼
[main.py] Route Handler
      │
      ▼
[CouncilOrchestrator.run_council()]
      │
      ├─► Stage 1: Query COUNCIL_MODELS in parallel
      │         │
      │         ▼
      │   [LLMProvider.chat()] × N models
      │         │
      │         ▼
      │   yield StageCompleted(stage=1, data=stage1_results)
      │
      ├─► Stage 2: Query rankings in parallel  
      │         │
      │         ▼
      │   [prompts.build_ranking_prompt()]
      │   [LLMProvider.chat()] × N models
      │   [council_logic.parse_ranking_from_text()]
      │   [council_logic.calculate_aggregate_rankings()]
      │         │
      │         ▼
      │   yield StageCompleted(stage=2, data=stage2_results)
      │
      └─► Stage 3: Chairman synthesis
                │
                ▼
          [prompts.build_chairman_synthesis_prompt()]
          [LLMProvider.chat(CHAIRMAN_MODEL)]
                │
                ▼
          yield StageCompleted(stage=3, data=stage3_result)
                │
                ▼
          yield RunCompleted()
```

---

## Key Design Decisions

### 1. Single Source of Truth

All council workflow logic is in `CouncilOrchestrator`. There is no duplication.

### 2. Dependency Injection

Adapters are instantiated in `main.py` and injected:
```python
conversation_repo = JsonConversationRepository(data_dir=config.DATA_DIR)
llm_provider = OpenRouterAdapter(api_key=config.OPENROUTER_API_KEY)

orchestrator = CouncilOrchestrator(
    llm_provider=llm_provider, 
    conversation_repo=conversation_repo,
    blob_store=blob_store
)
```

### 3. Domain Events

The orchestrator yields domain events instead of raw data:
- `StageStarted(stage=1, total=4)`
- `StageProgress(stage=1, completed=2, total=4)`
- `StageCompleted(stage=1, data=[...])`
- `TitleGenerated(title="...")`
- `RunCompleted()`

This enables both streaming and non-streaming endpoints to use the same code path.

### 4. Pure Prompt Functions

`prompts.py` contains pure functions that build prompt strings:
- `build_ranking_prompt(query, stage1_results)`
- `build_chairman_synthesis_prompt(query, stage1, stage2)`
- `build_chairman_followup_prompt(...)`
- `build_title_generation_prompt(query)`

No async, no network calls.

---

## Testing Strategy

### Unit Tests
- `test_council_domain.py` - Tests pure functions in `council_logic.py`
- `test_council_service.py` - Tests orchestrator with mock LLMProvider
- `test_domain_models.py` - Tests Pydantic models
- `test_prompt_builder.py` - Tests prompt construction

### Integration Tests
- `test_message_stream.py` - Tests SSE streaming endpoint
- `test_message_end_to_end.py` - Tests full message flow
- `test_api_improvements.py` - Tests API endpoints

### Mock Strategy

Tests mock at the **port level**, not at internal functions:
```python
class MockLLM(LLMProvider):
    async def chat(self, model, messages, **kwargs):
        return {"content": "Mock response"}

orchestrator = CouncilOrchestrator(
    llm_provider=MockLLM(),
    conversation_repo=mock_repo
)
```

---

## File Structure

```
backend/
├── main.py                    # FastAPI app, routes, DI setup
├── config.py                  # Configuration (models, API keys)
├── ports.py                   # Abstract interfaces
├── storage.py                 # Legacy storage (for backward compat)
│
├── application/
│   ├── council_service.py     # CouncilOrchestrator (THE orchestrator)
│   ├── prompts.py             # Pure prompt templates
│   └── prompt_builder.py      # Prompt content builder
│
├── domain/
│   ├── models.py              # Pydantic domain models
│   └── council_logic.py       # Pure functions (parse, calculate)
│
├── infrastructure/
│   ├── json_repository.py     # JSON file storage adapter
│   ├── openrouter_adapter.py  # OpenRouter API adapter
│   └── blob_store.py          # File attachment storage
│
└── tests/
    ├── unit/                  # Unit tests
    └── integration/           # Integration tests
```

---

## Future Enhancements

With this architecture, these are now easy to implement:

1. **Database Migration:** Create `FirestoreRepository` implementing `ConversationRepository`
2. **Alternative LLM Providers:** Create `AnthropicAdapter` implementing `LLMProvider`
3. **Streaming Improvements:** Add per-token streaming by extending `stream_chat`
4. **Caching:** Add a caching decorator around `LLMProvider.chat`
5. **Rate Limiting:** Add middleware at the adapter level
