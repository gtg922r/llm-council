# Track Plan: Unified Input & File Context

## Phase 1: Refactor - Unified ChatInput Component [checkpoint: 29bb3fe]
- [x] Task: Create a reusable `ChatInput` component with basic messaging functionality (text, expansion, enter-to-send) bc7d836
- [x] Task: Integrate `ChatInput` into `ChatInterface.jsx` for the main conversation input 797e997
- [x] Task: Integrate `ChatInput` into the Chairman follow-up flow (replacing or refactoring `FollowUpInput.jsx`) acfb4b2
- [x] Task: Conductor - User Manual Verification 'Refactor - Unified ChatInput Component' (Protocol in workflow.md) c6e32c4

## Phase 2: Frontend - File Staging & UI [checkpoint: 9afc47f]
- [x] Task: Implement Drag & Drop logic in `ChatInput` with border highlights and a "Drop files here" overlay. c3fc1bd
- [x] Task: Add a file attachment icon (paperclip) to `ChatInput` and integrate with the system file picker. 0e03724
- [x] Task: Implement file validation (size < 1MB, text-based extensions) and staging state management. 2241b99
- [x] Task: Render removable file chips for currently staged files within `ChatInput`. 0a04288
- [x] Task: Conductor - User Manual Verification 'Frontend - File Staging & UI' (Protocol in workflow.md) 9afc47f

## Phase 3: Transmission & Rendering [checkpoint: e58d372]
- [x] Task: Update the message submission logic to read staged file contents and concatenate them into the payload with clear delimiters. 0eb45e5
- [x] Task: Update the conversation history rendering to display file chips within the user's message blocks. 43057ee
- [x] Task: Ensure that sending a message correctly clears both text and staged files. 1c95fbc
- [x] Task: Conductor - User Manual Verification 'Transmission & Rendering' (Protocol in workflow.md) e58d372

## Phase 4: End-to-End Verification [checkpoint: 0d1e21b]
- [x] Task: Perform a full council run with multiple text files to verify correct context injection and Chairman synthesis. ca76f51
- [x] Task: Conductor - User Manual Verification 'End-to-End Verification' (Protocol in workflow.md) e58d372
