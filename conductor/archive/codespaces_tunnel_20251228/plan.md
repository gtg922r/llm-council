# Plan: Codespaces Frontend-Backend Tunneling

## Phase 1: Backend Environment & CORS Configuration [checkpoint: 2e04672]
Focus on making the backend aware of the Codespaces environment and dynamically adjusting CORS permissions.

- [x] Task: Implement Environment-Aware Configuration logic in `backend/config.py` to detect `CODESPACES` or `DEBUG` mode. 1d6afb0
- [x] Task: Update `backend/main.py` to use dynamic CORS origins based on the detected environment. 37288d1
- [x] Task: Conductor - User Manual Verification 'Backend Environment & CORS Configuration' (Protocol in workflow.md) 2e04672

## Phase 2: Frontend Proxy & Client Refactor [checkpoint: b0c4a08]
Configure the frontend build tool to handle request forwarding and update the API client to use origin-agnostic paths.

- [x] Task: Configure `frontend/vite.config.js` with a development proxy for the `/api` prefix. 2ea8b48
- [x] Task: Refactor `frontend/src/api.js` to remove the hardcoded `API_BASE` and use relative paths. 4f301eb
- [x] Task: Conductor - User Manual Verification 'Frontend Proxy & Client Refactor' (Protocol in workflow.md) b0c4a08

## Phase 3: Integration & Validation [checkpoint: 8c238f0]
Verify that the entire system works seamlessly within a GitHub Codespace.

- [x] Task: Perform end-to-end connectivity test: verify stage-by-stage Symposia council execution through the proxied frontend. 5be3f55
- [x] Task: Verify that the system still functions correctly in a standard local (non-Codespace) environment. 634af85
- [x] Task: Conductor - User Manual Verification 'Integration & Validation' (Protocol in workflow.md) 8c238f0
