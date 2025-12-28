# Track Spec: Council Resilience & Error Handling

## Goal
Enhance the reliability of the LLM Council by implementing robust error handling for external API interactions. The system should gracefully handle timeouts, rate limits, and service failures from OpenRouter/LLM providers without crashing the entire application or stalling the user experience.

## Core Requirements
1.  **Individual Model Failures:** If a single model fails (timeout, 5xx error, etc.) during Stage 1 (Initial Opinions) or Stage 2 (Review), the process should continue with the remaining models.
    -   The UI should clearly indicate which model failed and why (e.g., "Error: Timeout").
    -   The Chairman (Stage 3) should proceed with the available successful responses.
2.  **Global Timeout Configuration:** Implement a configurable timeout for API requests to prevent indefinite hanging.
3.  **Retry Logic:** Implement a simple retry mechanism (e.g., 1 retry) for transient errors (e.g., 429 Rate Limit, 503 Service Unavailable).
4.  **User Feedback:** Provide clear, non-intrusive error messages in the frontend for partial failures.

## Technical Scope
-   **Backend (`backend/openrouter.py`, `backend/council.py`):**
    -   Wrap `httpx` calls with error handling (try/except blocks).
    -   Update `asyncio.gather` usage to allow partial successes (e.g., `return_exceptions=True`).
    -   Add logging for specific error types.
-   **Frontend (`frontend/src/components/ChatInterface.jsx`, etc.):**
    -   Update state management to handle "error" states for individual model responses.
    -   Render error indicators in the model tabs/response areas.

## Out of Scope
-   Complex circuit breaker patterns (keep it simple for now).
-   Changing the core UI layout (just adding error states).
