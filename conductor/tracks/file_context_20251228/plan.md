# Track Plan: Drag & Drop File Context

## Phase 1: Frontend - File Staging & UI Components
- [ ] Task: Create a `FileAttachment` component to render the chips/tags for staged files.
- [ ] Task: Update the `ChatInterface.jsx` input form to support drag-and-drop events and file selection.
- [ ] Task: Implement file validation (size < 1MB, text-only) and error notification (e.g., using `alert` or a simple UI message).
- [ ] Task: Manage the list of staged files in the `ChatInterface` state (reading content using `FileReader`).
- [ ] Task: Conductor - User Manual Verification 'Frontend - File Staging & UI Components' (Protocol in workflow.md)

## Phase 2: Frontend - Message Payload & Transmission
- [ ] Task: Modify the message submission logic in `frontend/src/api.js` or `App.jsx` to concatenate file contents with the user's text message using the specified delimiters.
- [ ] Task: Ensure that sending a message clears the staged files from the UI.
- [ ] Task: Update the message display in `ChatInterface.jsx` to potentially collapse or hide large file context in the conversation history (UX refinement).
- [ ] Task: Conductor - User Manual Verification 'Frontend - Message Payload & Transmission' (Protocol in workflow.md)

## Phase 3: End-to-End Verification
- [ ] Task: Perform a full council run with a real text file to verify that the models (Stage 1) and the Chairman (Stage 3) correctly acknowledge the file content.
- [ ] Task: Conductor - User Manual Verification 'End-to-End Verification' (Protocol in workflow.md)
