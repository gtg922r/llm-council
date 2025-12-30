# Implementation Plan: Refactor Backend File Transmission

## Phase 1: Backend Data Model & Storage [checkpoint: f882363]
Refactor the backend to support structured file context in the API and storage layer.

- [x] Task: Backend - Update `backend/main.py` Pydantic models to include `FileContext` and `files` list in requests. (be774ff)
- [x] Task: Backend - Update `backend/storage.py` to accept and store `files` in `add_user_message`. (e5ecd78)
- [x] Task: Backend - Implement `build_prompt_content` helper in `backend/main.py` (or utility) to concatenate text + files. (c22ce8a)
- [x] Task: Backend - Update `send_message` logic to use `build_prompt_content` and store files correctly. (a7c259e)
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Data Model & Storage' (Protocol in workflow.md) (f882363)

## Phase 2: Frontend API Integration [checkpoint: 8327687]
Update the frontend to send structured file objects instead of concatenating strings.

- [x] Task: Frontend - Update `api.js` to accept and transmit `files` array in `sendMessage` and `sendMessageStream`. (ac51460)
- [x] Task: Frontend - Update `App.jsx` to remove string concatenation logic and pass `stagedFiles` to the API. (9440617)
- [x] Task: Frontend - Verify `ChatInterface.jsx` and `ChatInput.jsx` correctly handle the new flow (mostly cleanup). (1fb8179)
- [x] Task: Conductor - User Manual Verification 'Phase 2: Frontend API Integration' (Protocol in workflow.md) (cfcc6cc)

## Phase 3: Verification & Cleanup
Ensure end-to-end functionality and backward compatibility.

- [x] Task: Test - Write comprehensive backend tests for `build_prompt_content` and storage logic. (df620dc)
- [x] Task: Test - Verify end-to-end flow with a new conversation containing files. (be6f5d2)
- [ ] Task: Test - Verify backward compatibility with existing conversations.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Verification & Cleanup' (Protocol in workflow.md)
