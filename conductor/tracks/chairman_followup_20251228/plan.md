# Track Plan: Chairman Follow-up Interaction

## Phase 1: Backend Support for Follow-up Context
- [x] Task: Create a reproduction script/test case to verify the current context construction for the Chairman and simulate a follow-up request. [d535e1d]
- [x] Task: Modify `backend/council.py` (or create a new function) to support generating a prompt that includes the previous conversation history (Original Query -> Council Context -> Chairman Response -> User Follow-up). [d535e1d]
- [x] Task: Update the API endpoint in `backend/main.py` (likely `/api/conversations/{conversation_id}/message`) to handle a "follow-up" flag or detect context to route strictly to the Chairman instead of the full Council. [8c770b8]
    -   *Design Note:* Alternatively, create a specific endpoint `/api/conversations/{conversation_id}/follow-up` to keep logic clean.
- [ ] Task: Conductor - User Manual Verification 'Backend Support for Follow-up Context' (Protocol in workflow.md)

## Phase 2: Frontend UI for Follow-up
- [ ] Task: Create a new `FollowUpInput` component that contains the "Send Message to Chairman" button and the conditionally rendered text input.
- [ ] Task: Update `ChatInterface.jsx` to render this `FollowUpInput` component after the last assistant message if the process is complete.
- [ ] Task: Wire up the `FollowUpInput` to call the appropriate backend API (new endpoint or modified existing one) with the user's message.
- [ ] Task: Handle the API response to append the User's message and the Chairman's new response to the local conversation state so it renders immediately.
- [ ] Task: Conductor - User Manual Verification 'Frontend UI for Follow-up' (Protocol in workflow.md)
