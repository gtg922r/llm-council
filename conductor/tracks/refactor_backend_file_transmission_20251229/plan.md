# Implementation Plan: Refactor Backend File Transmission

## Phase 1: Backend Data Model & Storage
Refactor the backend to support structured file context in the API and storage layer.

- [x] Task: Backend - Update `backend/main.py` Pydantic models to include `FileContext` and `files` list in requests. (5793505)
- [x] Task: Backend - Update `backend/storage.py` to accept and store `files` in `add_user_message`. (9fc6cfa)
- [x] Task: Backend - Implement `build_prompt_content` helper in `backend/main.py` (or utility) to concatenate text + files. (2a6799c)
- [ ] Task: Backend - Update `send_message` logic to use `build_prompt_content` and store files correctly.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Backend Data Model & Storage' (Protocol in workflow.md)

## Phase 2: Frontend API Integration
Update the frontend to send structured file objects instead of concatenating strings.

- [ ] Task: Frontend - Update `api.js` to accept and transmit `files` array in `sendMessage` and `sendMessageStream`.
- [ ] Task: Frontend - Update `App.jsx` to remove string concatenation logic and pass `stagedFiles` to the API.
- [ ] Task: Frontend - Verify `ChatInterface.jsx` and `ChatInput.jsx` correctly handle the new flow (mostly cleanup).
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend API Integration' (Protocol in workflow.md)

## Phase 3: Verification & Cleanup
Ensure end-to-end functionality and backward compatibility.

- [ ] Task: Test - Write comprehensive backend tests for `build_prompt_content` and storage logic.
- [ ] Task: Test - Verify end-to-end flow with a new conversation containing files.
- [ ] Task: Test - Verify backward compatibility with existing conversations.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Cleanup' (Protocol in workflow.md)
