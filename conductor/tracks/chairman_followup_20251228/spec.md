# Track Spec: Chairman Follow-up Interaction

## Goal
Enable users to engage in a follow-up conversation directly with the Chairman model after receiving the final synthesized response. This allows for clarification, refinement, or further exploration of the Chairman's synthesis without re-triggering the entire multi-model Council process.

## Functional Requirements
1.  **Initiation:**
    -   After the Chairman's final response (Stage 3) is displayed, a "Send Message to Chairman" button should appear at the bottom of the message group.
    -   Clicking this button reveals a text input field for the user to type their follow-up message.

2.  **Processing (Backend):**
    -   The system should process this follow-up as a direct interaction with the Chairman model.
    -   **Context Construction:** The context provided to the Chairman must include:
        -   The original user query.
        -   The full context from Stage 1 (Individual Responses) and Stage 2 (Peer Rankings) that was provided originally.
        -   The Chairman's initial response (Stage 3 output).
        -   The user's new follow-up message.
    -   The Council (Stage 1 & 2 models) should **NOT** be re-queried. This is a Chairman-only dialogue.

3.  **Display (Frontend):**
    -   The user's follow-up message and the Chairman's subsequent response should be appended to the conversation as new message blocks (not nested).
    -   The UI should clearly distinguish these follow-up messages as being part of the same logical "conversation" but distinct from the initial full Council run.

## Non-Functional Requirements
-   **Responsiveness:** The UI transition to reveal the input should be instant.
-   **Consistency:** The styling of the follow-up messages should match the existing chat interface (User vs. Assistant bubbles).

## Acceptance Criteria
-   [ ] A "Send Message to Chairman" button appears only after a completed Stage 3 response.
-   [ ] Clicking the button reveals an input field.
-   [ ] Submitting a follow-up sends a request to the backend that includes the full conversation history.
-   [ ] The backend correctly formats the prompt for the Chairman to include original context + previous answer + new question.
-   [ ] The Chairman's response is generated without re-running Stage 1 or Stage 2.
-   [ ] The new exchange appears in the chat log below the original response.

## Out of Scope
-   Re-triggering the full Council for follow-ups.
-   Branching conversations or complex threading UI.
