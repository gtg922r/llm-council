# Track Plan: Council Resilience & Error Handling

## Phase 1: Backend Error Handling & Resilience
- [x] Task: Create a reproduction script/test case that simulates OpenRouter API failures (timeouts, 500s) to verify current behavior (crash vs. hang). [00154bf]
- [ ] Task: Modify `backend/openrouter.py` to add a configurable timeout and basic retry logic (1 retry) for `httpx` requests.
- [ ] Task: Update `backend/council.py` (specifically `get_initial_opinions` and `get_reviews`) to handle exceptions from individual model calls using `asyncio.gather(..., return_exceptions=True)` or similar pattern, ensuring one failure doesn't stop the batch.
- [ ] Task: Ensure the Chairman (Stage 3) logic in `backend/council.py` can handle missing or error-flagged inputs from previous stages.
- [ ] Task: Conductor - User Manual Verification 'Backend Error Handling & Resilience' (Protocol in workflow.md)

## Phase 2: Frontend Error Visualization
- [ ] Task: Update the API response format in `backend/main.py` or `backend/council.py` to explicitly return error status and messages for failed models instead of just crashing or returning null.
- [ ] Task: Update `frontend/src/components/ChatInterface.jsx` (and potentially `Stage1.jsx`, `Stage2.jsx`) to handle the new error status in the model response objects.
- [ ] Task: Implement visual indicators for failed models in the UI (e.g., a red warning icon or "Failed" text in the tab/response area) so the user knows a model didn't reply.
- [ ] Task: Conductor - User Manual Verification 'Frontend Error Visualization' (Protocol in workflow.md)
