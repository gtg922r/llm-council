# Track Plan: Unified Input & File Context

## Phase 1: Refactor - Unified ChatInput Component [checkpoint: 29bb3fe]
- [x] Task: Create a reusable `ChatInput` component with basic messaging functionality (text, expansion, enter-to-send) bc7d836
- [x] Task: Integrate `ChatInput` into `ChatInterface.jsx` for the main conversation input 797e997
- [x] Task: Integrate `ChatInput` into the Chairman follow-up flow (replacing or refactoring `FollowUpInput.jsx`) acfb4b2
- [x] Task: Conductor - User Manual Verification 'Refactor - Unified ChatInput Component' (Protocol in workflow.md) c6e32c4

## Phase 2: Frontend - File Staging & UI [checkpoint: c6e32c4]
- [ ] Task: Implement Drag & Drop logic in `ChatInput` with border highlights and a "Drop files here" overlay.
- [ ] Task: Add a file attachment icon (paperclip) to `ChatInput` and integrate with the system file picker.
- [ ] Task: Implement file validation (size < 1MB, text-based extensions) and staging state management.
- [ ] Task: Render removable file chips for currently staged files within `ChatInput`.
- [ ] Task: Conductor - User Manual Verification 'Frontend - File Staging & UI' (Protocol in workflow.md)

## Phase 3: Transmission & Rendering
- [ ] Task: Update the message submission logic to read staged file contents and concatenate them into the payload with clear delimiters.
- [ ] Task: Update the conversation history rendering to display file chips within the user's message blocks.
- [ ] Task: Ensure that sending a message correctly clears both text and staged files.
- [ ] Task: Conductor - User Manual Verification 'Transmission & Rendering' (Protocol in workflow.md)

## Phase 4: End-to-End Verification
- [ ] Task: Perform a full council run with multiple text files to verify correct context injection and Chairman synthesis.
- [ ] Task: Conductor - User Manual Verification 'End-to-End Verification' (Protocol in workflow.md)
