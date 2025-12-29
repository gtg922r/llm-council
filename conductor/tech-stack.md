# Tech Stack

## Backend
- **Language:** Python (>=3.10)
- **Framework:** FastAPI
- **HTTP Client:** httpx (async) for communicating with OpenRouter
- **Data Validation:** Pydantic
- **Web Server:** Uvicorn

## Frontend
- **Language:** JavaScript (ES modules)
- **Framework:** React
- **Build Tool:** Vite
- **Markdown Rendering:** react-markdown
- **Icons:** lucide-react
- **Styling:** Standard CSS

## Tooling & Infrastructure
- **Python Package Management:** uv
- **JavaScript Package Management:** npm
- **LLM Gateway:** OpenRouter API
- **Local Development:**
  - Backend: http://localhost:8001 (FastAPI)
  - Frontend: http://localhost:5173 (Vite with Development Proxy to Backend)
  - Testing:
    - Backend: pytest
    - Frontend: Vitest + React Testing Library + @vitest/coverage-v8
  - **Codespaces Support:** Automatically detects `CODESPACES` environment to relax CORS and enable seamless tunneling via the Vite proxy.

## Changes & Deviations
- **2025-12-29:** Added Vitest and React Testing Library to the frontend tech stack to support TDD as required by the project workflow.
