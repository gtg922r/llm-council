<div align="center">

# Symposia

### Your AI Council — Collective Intelligence from Multiple LLMs

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![React 19](https://img.shields.io/badge/react-19-61dafb.svg)](https://react.dev/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688.svg)](https://fastapi.tiangolo.com/)

<img src="header.jpg" alt="Symposia Header" width="700">

[Features](#features) • [Quick Start](#quick-start) • [How It Works](#how-it-works) • [Architecture](#architecture) • [Deployment](#deployment) • [Contributing](#contributing)

</div>

---

## Overview

**Symposia** transforms how you interact with AI by replacing single-model queries with a collaborative council of the world's leading LLMs. Instead of getting one perspective, you get a synthesized consensus from GPT, Claude, Gemini, Grok, and more — with transparent peer review and rankings.

Inspired by the deliberative processes of ancient Greek symposia and modern advisory boards, Symposia orchestrates AI models to evaluate, critique, and build upon each other's responses, delivering higher-quality answers than any single model alone.

> **Origin**: This project was originally created by [Ryan Gerstenkorn](https://github.com/gtg922r) as a weekend experiment. This fork extends it with production-ready features including Firebase authentication, Firestore persistence, streaming responses, and responsive design.

---

## Features

### 🏛️ Council Deliberation
- **Multi-Model Queries**: Send your question to 4+ top-tier LLMs simultaneously
- **Anonymized Peer Review**: Models evaluate each other's responses without knowing the source
- **Chairman Synthesis**: A designated model compiles the collective wisdom into a final answer
- **Aggregate Rankings**: See how models rank each other, with "street cred" scores

### 💬 Modern Chat Experience
- **Real-Time Streaming**: Watch responses build as each stage completes
- **Conversation History**: Persistent conversations with search, pin, and archive
- **Follow-Up Questions**: Continue discussions with the Chairman for deeper exploration
- **File Attachments**: Upload text files for context-aware responses
- **Dark/Light Themes**: Comfortable viewing in any environment

### ⚡ Two Speed Modes
| Mode | Models | Best For |
|------|--------|----------|
| **Smart** | GPT-5.2, Claude Opus 4.5, Gemini 3 Pro, Grok 4 | Complex analysis, research, important decisions |
| **Fast** | Gemini Flash, Claude Haiku, GPT-4.1 Nano, Llama 4 Scout | Quick questions, brainstorming, rapid iteration |

### 🔐 Enterprise-Ready
- **Firebase Authentication**: Secure Google Sign-In
- **Per-User Data Isolation**: Firestore-backed multi-tenant storage
- **Production Deployment**: Systemd service configuration included
- **Responsive Design**: Full mobile and desktop support

---

## Quick Start

### Prerequisites

- Python 3.10+
- Node.js 18+
- [uv](https://docs.astral.sh/uv/) (Python package manager)
- [OpenRouter API Key](https://openrouter.ai/) (for LLM access)
- Firebase Project (for authentication)

### Installation

```bash
# Clone the repository
git clone https://github.com/gtg922r/llm-council.git symposia
cd symposia

# Install all dependencies
./install.sh

# Or install manually:
# Backend
uv sync

# Frontend
cd frontend && npm install && cd ..
```

### Configuration

1. **Create `.env` file** in the project root:

```env
OPENROUTER_API_KEY=sk-or-v1-your-key-here
```

2. **Set up Firebase**:
   - Create a Firebase project at [console.firebase.google.com](https://console.firebase.google.com)
   - Enable Authentication with Google Sign-In
   - Enable Firestore Database
   - Download service account credentials to `firebase-service-account.json`
   - Copy `frontend/src/firebase.example.js` to `frontend/src/firebase.js` and add your config

3. **Customize models** (optional) in `backend/config.py`:

```python
SMART_COUNCIL_MODELS = [
    "openai/gpt-5.2",
    "google/gemini-3-pro-preview",
    "anthropic/claude-opus-4.5",
    "x-ai/grok-4",
]

SMART_CHAIRMAN_MODEL = "google/gemini-3-pro-preview"
```

### Running

```bash
# Development (with hot reload)
./start.sh
# Frontend: http://localhost:5173
# Backend:  http://localhost:8001

# Production (single server)
cd frontend && npm run build && cd ..
uv run uvicorn backend.main:app --host 0.0.0.0 --port 8000
# Access: http://localhost:8000
```

---

## How It Works

Symposia processes each query through a three-stage deliberation pipeline:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              USER QUERY                                     │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 1: First Opinions                                                    │
│  ─────────────────────────                                                  │
│  Query sent to all council models in parallel.                              │
│  Each model responds independently — no cross-contamination.                │
│                                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                    │
│  │   GPT    │  │  Claude  │  │  Gemini  │  │   Grok   │                    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘                    │
│       │             │             │             │                           │
│       └─────────────┴──────┬──────┴─────────────┘                           │
│                            ▼                                                │
│                    [4 Independent Responses]                                │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 2: Peer Review                                                       │
│  ────────────────────                                                       │
│  Each model reviews ALL responses, but identities are anonymized            │
│  ("Response A", "Response B", etc.) to prevent favoritism.                  │
│                                                                             │
│  Models evaluate: accuracy, completeness, reasoning quality                 │
│  Output: Individual rankings + detailed critiques                           │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │  GPT's Ranking:    1. Response C  2. Response A  3. Response B   │      │
│  │  Claude's Ranking: 1. Response A  2. Response C  3. Response D   │      │
│  │  Gemini's Ranking: 1. Response C  2. Response A  3. Response B   │      │
│  │  Grok's Ranking:   1. Response A  2. Response C  3. Response B   │      │
│  └──────────────────────────────────────────────────────────────────┘      │
│                            │                                                │
│                            ▼                                                │
│                   [Aggregate Rankings Calculated]                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│  STAGE 3: Chairman Synthesis                                                │
│  ───────────────────────────                                                │
│  The designated Chairman model receives:                                    │
│    • Original query                                                         │
│    • All individual responses                                               │
│    • All peer evaluations and rankings                                      │
│                                                                             │
│  Chairman synthesizes a final, comprehensive response that:                 │
│    • Incorporates the strongest points from each model                      │
│    • Addresses areas of agreement and disagreement                          │
│    • Provides balanced, well-reasoned conclusions                           │
│                                                                             │
│  ┌──────────────────────────────────────────────────────────────────┐      │
│  │                    FINAL COUNCIL RESPONSE                        │      │
│  │            (Synthesized from collective intelligence)            │      │
│  └──────────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Why This Works

1. **Diversity of Thought**: Different models have different training data, architectures, and reasoning patterns. Pooling them catches blind spots.

2. **Adversarial Validation**: When models rank each other's work anonymously, they naturally identify weaknesses and errors that a single model might miss.

3. **Meta-Cognitive Synthesis**: The Chairman has access to not just answers, but evaluations of those answers — enabling higher-order reasoning about what makes a good response.

---

## Architecture

Symposia follows **Hexagonal Architecture** (Ports & Adapters) for clean separation of concerns and testability.

```
┌─────────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (React 19)                           │
│                                                                         │
│   ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐        │
│   │    Sidebar      │  │  ChatInterface  │  │  Stage Views    │        │
│   │  (Conversations)│  │  (Main Chat)    │  │  (1, 2, 3)      │        │
│   └─────────────────┘  └─────────────────┘  └─────────────────┘        │
│                                                                         │
│   ┌─────────────────────────────────────────────────────────────┐      │
│   │  AuthContext  │  SettingsContext  │  API Client (SSE)       │      │
│   └─────────────────────────────────────────────────────────────┘      │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   │ HTTP/SSE + Bearer Token
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        BACKEND (FastAPI)                                │
│                                                                         │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                    Interface Layer                              │   │
│   │    • FastAPI Routes & Middleware                                │   │
│   │    • Request/Response Serialization                             │   │
│   │    • Firebase Token Verification                                │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                                ▼                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                   Application Layer                             │   │
│   │    • CouncilOrchestrator (3-stage workflow)                     │   │
│   │    • Prompt Templates (ranking, synthesis, follow-up)           │   │
│   │    • Domain Event Streaming                                     │   │
│   └────────────────────────────────────────────────────────────────┘   │
│                                │                                        │
│                 ┌──────────────┼──────────────┐                        │
│                 ▼              ▼              ▼                        │
│   ┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐           │
│   │  Domain Models  │  │    Ports    │  │  Domain Logic   │           │
│   │  • Conversation │  │  (Abstract) │  │  • Ranking Parse│           │
│   │  • Messages     │  │  • LLMPort  │  │  • Aggregation  │           │
│   │  • StageResults │  │  • RepoPort │  │                 │           │
│   └─────────────────┘  └──────┬──────┘  └─────────────────┘           │
│                               │                                        │
│                               ▼                                        │
│   ┌────────────────────────────────────────────────────────────────┐   │
│   │                  Infrastructure Layer                           │   │
│   │                                                                 │   │
│   │   ┌──────────────────┐  ┌──────────────────┐  ┌─────────────┐  │   │
│   │   │  OpenRouter      │  │  Firestore       │  │  Blob       │  │   │
│   │   │  Adapter         │  │  Repository      │  │  Store      │  │   │
│   │   │  (LLM Calls)     │  │  (Persistence)   │  │  (Files)    │  │   │
│   │   └────────┬─────────┘  └────────┬─────────┘  └─────────────┘  │   │
│   │            │                     │                              │   │
│   └────────────┼─────────────────────┼──────────────────────────────┘   │
│                │                     │                                  │
└────────────────┼─────────────────────┼──────────────────────────────────┘
                 │                     │
                 ▼                     ▼
        ┌────────────────┐    ┌────────────────┐
        │   OpenRouter   │    │   Firestore    │
        │   (GPT, Claude,│    │   (Google      │
        │    Gemini...)  │    │    Cloud)      │
        └────────────────┘    └────────────────┘
```

### Directory Structure

```
symposia/
├── backend/
│   ├── application/           # Use cases & orchestration
│   │   ├── council_service.py # 🎯 Core orchestrator (run_council, follow-up)
│   │   ├── prompts.py         # Pure prompt templates
│   │   └── prompt_builder.py  # Prompt assembly with attachments
│   ├── domain/                # Business entities & logic
│   │   ├── models.py          # Pydantic models (Conversation, Message...)
│   │   └── council_logic.py   # Pure functions (parse rankings, aggregate)
│   ├── infrastructure/        # External implementations
│   │   ├── openrouter_adapter.py  # LLM API integration
│   │   ├── firestore_repository.py # Cloud persistence
│   │   ├── firebase_auth.py   # Token verification
│   │   └── blob_store.py      # File storage
│   ├── ports.py               # Abstract interfaces (LLMProvider, Repository)
│   ├── config.py              # Environment & model configuration
│   └── main.py                # FastAPI app & dependency injection
│
├── frontend/
│   └── src/
│       ├── components/        # React UI components
│       │   ├── ChatInterface.jsx  # Main chat view
│       │   ├── Stage1.jsx     # Individual responses (tabs)
│       │   ├── Stage2.jsx     # Peer reviews & rankings
│       │   ├── Stage3.jsx     # Final synthesis
│       │   └── Sidebar.jsx    # Conversation list
│       ├── context/           # React contexts (Auth, Settings)
│       ├── api.js             # Backend API client
│       └── firebase.js        # Firebase configuration
│
├── tests/                     # Integration & unit tests
├── data/                      # Local storage (dev mode)
└── conductor/                 # Development tooling & specs
```

### Key Design Decisions

| Decision | Rationale |
|----------|----------|
| **Hexagonal Architecture** | Core logic is independent of LLM providers, databases, and frameworks. Easy to swap OpenRouter for direct APIs or add new storage backends. |
| **Domain Events** | `CouncilOrchestrator` yields events (`StageStarted`, `StageCompleted`) enabling both streaming and batch responses from the same code. |
| **Anonymized Ranking** | Prevents models from recognizing each other's "voice" and biasing evaluations. Labels (Response A, B, C) are mapped back after scoring. |
| **Dependency Injection** | Adapters instantiated in `main.py` and injected into orchestrator. Tests mock at port level, not internal functions. |

---

## Deployment

### Production with Systemd

```bash
# Build frontend assets
cd frontend && npm run build && cd ..

# Install service
sudo cp symposia.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable symposia
sudo systemctl start symposia

# Verify
systemctl status symposia
journalctl -u symposia -f
```

### Docker (Coming Soon)

```dockerfile
# Example Dockerfile
FROM python:3.11-slim
WORKDIR /app
COPY . .
RUN pip install uv && uv sync
RUN cd frontend && npm ci && npm run build
EXPOSE 8000
CMD ["uv", "run", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `FIREBASE_SERVICE_ACCOUNT` | No | Path to Firebase credentials (default: `firebase-service-account.json`) |
| `DEBUG` | No | Enable debug mode |

---

## API Reference

All endpoints require Bearer token authentication (Firebase ID token).

### Conversations

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/conversations` | List all conversations |
| `POST` | `/api/conversations` | Create new conversation |
| `GET` | `/api/conversations/{id}` | Get conversation with messages |
| `PATCH` | `/api/conversations/{id}` | Update title, pin, archive status |
| `DELETE` | `/api/conversations/{id}` | Delete conversation |
| `POST` | `/api/conversations/{id}/duplicate` | Duplicate conversation |

### Messages

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/conversations/{id}/message` | Send message (batch response) |
| `POST` | `/api/conversations/{id}/message/stream` | Send message (SSE streaming) |

### Health

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/health` | Health check (no auth required) |

### Message Request Body

```json
{
  "content": "What is the meaning of life?",
  "files": [
    {
      "name": "context.txt",
      "content": "Base64 encoded content...",
      "size": 1234
    }
  ],
  "target_model": null,       // "chairman" for follow-up
  "model_mode": "smart"       // "smart" or "fast"
}
```

### SSE Event Types

```javascript
// Stage lifecycle
{ "type": "stage_start", "stage": 1, "total": 4 }
{ "type": "stage_progress", "stage": 1, "completed": 2, "total": 4 }
{ "type": "stage_complete", "stage": 1, "data": [...] }

// Metadata
{ "type": "title_complete", "title": "Discussion about life" }
{ "type": "complete" }

// Errors
{ "type": "error", "message": "..." }
```

---

## Testing

```bash
# Activate virtual environment
source .venv/bin/activate

# Run all tests
python -m pytest tests/ backend/tests/ -v

# With coverage
python -m pytest tests/ backend/tests/ --cov=backend --cov-report=html

# Frontend tests
cd frontend && npm test
```

### Test Strategy

- **Unit Tests**: Pure domain functions (ranking parsing, aggregation)
- **Integration Tests**: Orchestrator with mocked LLM/Repository ports
- **Component Tests**: React components with Testing Library

---

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork & Branch**: Create a feature branch from `master`
2. **Architecture**: Respect the hexagonal layers — don't import infrastructure in domain
3. **Testing**: Add tests for new functionality
4. **Types**: Use Pydantic models for data, type hints throughout
5. **Commits**: Clear, descriptive commit messages

### Development Workflow

```bash
# Create a worktree for your feature
git worktree add ../feat-my-feature -b feat/my-feature master
cd ../feat-my-feature
./install.sh
cp ../symposia/.env .

# Make changes, test, commit
python -m pytest tests/ -v
git commit -am "feat: add my feature"
```

---

## Tech Stack

| Layer | Technology | Version |
|-------|------------|--------|
| **Frontend** | React | 19.x |
| **Build** | Vite | 7.x |
| **Styling** | CSS Modules | - |
| **Icons** | Lucide React | 0.5x |
| **Markdown** | react-markdown | 10.x |
| **Backend** | FastAPI | 0.115+ |
| **Validation** | Pydantic | 2.9+ |
| **HTTP Client** | httpx | 0.27+ |
| **Auth** | Firebase Admin | 6.x |
| **Database** | Firestore | - |
| **LLM Gateway** | OpenRouter | - |
| **Package Manager** | uv | - |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

---

## Acknowledgments

- **[Andrej Karpathy](https://twitter.com/karpathy)** — Original author of the [llm-council](https://github.com/karpathy/llm-council) repository
- **[OpenRouter](https://openrouter.ai/)** — Unified LLM API access
- **[Firebase](https://firebase.google.com/)** — Authentication and database

---

<div align="center">

**[⬆ Back to Top](#symposia)**

Built with 🏛️ by the open source community

</div>
