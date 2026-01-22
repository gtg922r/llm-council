# AGENTS.md - Technical Notes for Symposia

This file contains technical details, architectural decisions, and important implementation notes for future development sessions.

## Project Overview

Symposia is a 3-stage deliberation system where multiple LLMs collaboratively answer user questions. The key innovation is anonymized peer review in Stage 2, preventing models from playing favorites.

## Architecture

The backend follows a **Hexagonal Architecture** (Ports & Adapters) pattern. See `CURRENT_ARCHITECTURE.md` for detailed diagrams.

### Quick Reference

| Layer | Location | Responsibility |
|-------|----------|---------------|
| Interface | `backend/main.py` | FastAPI routes, HTTP handling |
| Application | `backend/application/` | CouncilOrchestrator, prompts |
| Domain | `backend/domain/` | Pydantic models, pure functions |
| Ports | `backend/ports.py` | Abstract interfaces |
| Infrastructure | `backend/infrastructure/` | OpenRouter adapter, JSON storage |

### Key Components

**`backend/application/council_service.py`** - The Orchestrator
- `CouncilOrchestrator` - Single source of truth for all council workflow
- `run_council()` - Async generator yielding domain events
- `chairman_followup()` - Handle follow-up questions
- Injects `LLMProvider` and `ConversationRepository`

**`backend/application/prompts.py`** - Pure Prompt Templates
- `build_ranking_prompt()` - Stage 2 ranking prompt
- `build_chairman_synthesis_prompt()` - Stage 3 chairman prompt
- `build_chairman_followup_prompt()` - Follow-up prompt
- `build_title_generation_prompt()` - Title generation
- `create_label_to_model_mapping()` - Anonymization mapping

**`backend/domain/council_logic.py`** - Pure Functions
- `parse_ranking_from_text()` - Extract FINAL RANKING section
- `calculate_aggregate_rankings()` - Compute average ranks

**`backend/domain/models.py`** - Pydantic Models
- `Conversation`, `UserMessage`, `AssistantMessage`
- `Stage1Result`, `Stage2Result`, `AggregateRanking`
- `AssistantMetadata` (contains `label_to_model` and rankings)

**`backend/ports.py`** - Abstract Interfaces
- `ConversationRepository` - Storage abstraction
- `LLMProvider` - LLM API abstraction

**`backend/infrastructure/openrouter_adapter.py`**
- `OpenRouterAdapter` implements `LLMProvider`
- Handles retries, timeouts, parallel queries

**`backend/infrastructure/json_repository.py`**
- `JsonConversationRepository` implements `ConversationRepository`
- JSON file storage in `data/conversations/`

**`backend/config.py`**
- `COUNCIL_MODELS` - List of OpenRouter model identifiers
- `CHAIRMAN_MODEL` - Model for final synthesis
- Backend runs on **port 8001**

### Frontend Structure (`frontend/src/`)

**`App.jsx`**
- Main orchestration: manages conversations list and current conversation
- Handles message sending and metadata storage

**`components/ChatInterface.jsx`**
- Multiline textarea (3 rows, resizable)
- Enter to send, Shift+Enter for new line

**`components/Stage1.jsx`**
- Tab view of individual model responses
- ReactMarkdown rendering

**`components/Stage2.jsx`**
- Tab view showing RAW evaluation text from each model
- De-anonymization happens CLIENT-SIDE for display
- Shows "Extracted Ranking" below each evaluation
- Aggregate rankings shown with average position

**`components/Stage3.jsx`**
- Final synthesized answer from chairman
- Green-tinted background to highlight conclusion

## Key Design Decisions

### Single Source of Truth
All council workflow logic is in `CouncilOrchestrator`. No duplication.

### Dependency Injection
Adapters are instantiated in `main.py` and injected into the orchestrator.

### Domain Events
The orchestrator yields domain events:
- `StageStarted`, `StageProgress`, `StageCompleted`
- `TitleGenerated`, `RunCompleted`

This enables both streaming and non-streaming endpoints to use the same code.

### Pure Prompt Functions
`prompts.py` contains pure functions that build prompt strings. No async, no network.

### Stage 2 Prompt Format
The Stage 2 prompt is specific to ensure parseable output:
1. Evaluate each response individually first
2. Provide "FINAL RANKING:" header
3. Numbered list format: "1. Response C"
4. No additional text after ranking section

### De-anonymization Strategy
- Models receive: "Response A", "Response B", etc.
- Backend creates mapping: `{"Response A": "openai/gpt-5.1", ...}`
- Frontend displays model names in **bold** for readability

## Important Implementation Details

### Relative Imports
All backend modules use relative imports (e.g., `from .config import ...`). Run as `python -m backend.main`.

### Port Configuration
- **Production**: Port 8000 (single server serves both API and frontend)
- **Development Backend**: Port 8001
- **Development Frontend**: Port 5173 (Vite dev server with proxy to backend)

### Testing
Tests mock at the **port level**, not internal functions:
```python
class MockLLM(LLMProvider):
    async def chat(self, model, messages, **kwargs):
        return {"content": "Mock response"}

orchestrator = CouncilOrchestrator(
    llm_provider=MockLLM(),
    conversation_repo=mock_repo
)
```

## Data Flow Summary

```
User Query
    ↓
CouncilOrchestrator.run_council()
    ↓
Stage 1: Parallel queries → [individual responses]
    ↓
Stage 2: Anonymize → Parallel ranking → [evaluations + parsed rankings]
    ↓
Aggregate Rankings Calculation
    ↓
Stage 3: Chairman synthesis
    ↓
Return: Domain events → HTTP response
    ↓
Frontend: Display with tabs + validation UI
```

## Production Deployment

### Location
- **Directory**: `/home/exedev/symposia`
- **URL**: https://symposia.exe.xyz:8000/
- **Health Check**: https://symposia.exe.xyz:8000/api/health

### Systemd Service
The production instance runs as a systemd service called `symposia`.

```bash
# Service management
sudo systemctl status symposia    # Check status
sudo systemctl restart symposia   # Restart service
sudo systemctl stop symposia      # Stop service
journalctl -u symposia -f         # View logs (follow)
journalctl -u symposia -n 100     # View last 100 log lines
```

### Service Configuration
- Service file: `/etc/systemd/system/symposia.service`
- Source: `~/symposia/symposia.service`
- Runs uvicorn directly from venv: `/home/exedev/symposia/.venv/bin/uvicorn`

### Deploying Changes
```bash
cd ~/symposia

# Backend changes only:
sudo systemctl restart symposia

# Frontend changes:
cd frontend && npm run build && cd ..
sudo systemctl restart symposia

# After updating service file:
sudo cp symposia.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl restart symposia
```

### Production Architecture
In production, the FastAPI backend serves both:
1. API endpoints at `/api/*`
2. Static frontend files from `frontend/dist/`
3. SPA catch-all route serves `index.html` for client-side routing

## Development Workflows

### Running Locally (Development)
```bash
./install.sh
./start.sh
```
This runs backend on port 8001 and Vite dev server on port 5173 with hot reload.

### Dev Auth Mode
`start.sh` automatically sets `DEV_AUTH=true` which enables:
- A **Dev Login** button on the login screen (green, with `<>` icon)
- Static auth token `dev-token-symposia` accepted by backend
- No Firebase/Google sign-in required for testing

To manually enable dev auth:
```bash
DEV_AUTH=true uv run python -m backend.main
```

Dev auth creates a user with:
- UID: `dev-user-12345`
- Email: `dev@symposia.local`
- Name: `Dev User`

**Security**: Dev auth is NEVER enabled in production (the systemd service doesn't set `DEV_AUTH`).

### Running Tests
```bash
source .venv/bin/activate
python -m pytest backend/tests tests/ -v
```

### Creating a New Feature Worktree
```bash
git worktree add ../feat-new-ability -b feat/new-ability master
cd ../feat-new-ability
./install.sh
cp ../symposia/.env .
```

## Common Gotchas

1. **Module Import Errors**: Always run as `python -m backend.main` from project root
2. **CORS Issues**: Frontend must match allowed origins in `main.py`
3. **Ranking Parse Failures**: If models don't follow format, fallback regex extracts patterns
4. **Metadata Persistence**: `label_to_model` and rankings are now persisted in `AssistantMetadata`

## Future Enhancement Ideas

- Configurable council/chairman via UI
- Per-token streaming responses
- Export conversations to markdown/PDF
- Model performance analytics
- Custom ranking criteria
- Alternative LLM providers (Anthropic direct, etc.)
