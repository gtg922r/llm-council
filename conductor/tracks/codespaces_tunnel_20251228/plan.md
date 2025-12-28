# Plan: Codespaces Frontend-Backend Tunneling

## Phase 1: Backend Environment & CORS Configuration
Focus on making the backend aware of the Codespaces environment and dynamically adjusting CORS permissions.

- [x] Task: Implement Environment-Aware Configuration logic in `backend/config.py` to detect `CODESPACES` or `DEBUG` mode. 1d6afb0
- [ ] Task: Update `backend/main.py` to use dynamic CORS origins based on the detected environment.
- [ ] Task: Conductor - User Manual Verification 'Backend Environment & CORS Configuration' (Protocol in workflow.md)

## Phase 2: Frontend Proxy & Client Refactor
Configure the frontend build tool to handle request forwarding and update the API client to use origin-agnostic paths.

- [ ] Task: Configure `frontend/vite.config.js` with a development proxy for the `/api` prefix.
- [ ] Task: Refactor `frontend/src/api.js` to remove the hardcoded `API_BASE` and use relative paths.
- [ ] Task: Conductor - User Manual Verification 'Frontend Proxy & Client Refactor' (Protocol in workflow.md)

## Phase 3: Integration & Validation
Verify that the entire system works seamlessly within a GitHub Codespace.

- [ ] Task: Perform end-to-end connectivity test: verify stage-by-stage LLM Council execution through the proxied frontend.
- [ ] Task: Verify that the system still functions correctly in a standard local (non-Codespace) environment.
- [ ] Task: Conductor - User Manual Verification 'Integration & Validation' (Protocol in workflow.md)
