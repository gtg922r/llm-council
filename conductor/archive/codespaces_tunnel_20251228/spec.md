# Specification: Codespaces Frontend-Backend Tunneling

## Overview
Enable seamless communication between the React frontend and FastAPI backend when running within GitHub Codespaces. This involves resolving CORS issues and configuring a development proxy to ensure the frontend can reach the backend elegantly and safely.

## Functional Requirements
1.  **Vite Proxy Configuration:**
    - Update `frontend/vite.config.js` to proxy all requests starting with `/api` to `http://localhost:8001`.
    - Ensure the proxy supports WebSockets if necessary (for SSE stability).
2.  **Frontend API Client Refactor:**
    - Update `frontend/src/api.js` to use a relative path for `API_BASE` instead of a hardcoded `localhost` URL.
3.  **Dynamic Backend CORS:**
    - Update `backend/main.py` and `backend/config.py` to allow flexible CORS origins (e.g., wildcard or specific Codespace patterns) when the system detects it is running in a GitHub Codespace (via `CODESPACES` env var) or when a `DEVELOPMENT` flag is active.

## Non-Functional Requirements
- **Environment Awareness:** The system must distinguish between production-like and development/Codespace environments to avoid over-relaxing security in production.
- **Idiomatic Implementation:** Use standard Vite and FastAPI patterns for proxying and middleware.

## Acceptance Criteria
- [ ] The frontend can be accessed via its Codespace-generated URL.
- [ ] API requests from the frontend to the backend succeed without CORS "Preflight" errors in the browser console.
- [ ] The backend correctly identifies the environment and applies the appropriate CORS policy.
- [ ] The application remains functional in a standard local environment (non-Codespaces).

## Out of Scope
- Implementing a production-grade reverse proxy (like Nginx).
- Changing the core logic of the Symposia council stages.
