# Track Spec: Unified Input & File Context

## Overview
Enhance the Symposia user experience by allowing users to provide text-based files as context for their queries. This track also involves unifying the message input component across the main conversation and Chairman follow-ups to ensure feature parity and design consistency.

## Functional Requirements
1.  **Unified Input Component:**
    -   Create a reusable `ChatInput` component to replace the separate input fields in `ChatInterface` (main) and `FollowUpInput` (chairman).
    -   The component must support multi-line text, expansion, and sending messages.
2.  **File Context Support:**
    -   **Drag & Drop:** Users can drag text-based files into the input area.
    -   **Visual Feedback:** Dragging over the input highlights the border and displays a "Drop files here" overlay.
    -   **Manual Attachment:** A subtle attachment icon (paperclip) placed right under the "expand" button.
    -   **File Validation:** Support plain text (.txt, .md, .csv, and source code files). Reject files > 1MB.
3.  **File Management (UI):**
    -   Attached files appear as removable chips/tags above or within the input area.
    -   Users can delete attached files before sending the message.
4.  **Message History:**
    -   **File Visualization:** Attached file chips must be displayed within the user's message block in the conversation view, providing a visual record of the context provided.
5.  **Context Transmission:**
    -   File content and filename are included in the message payload.
    -   The payload follows an idiomatic approach for the API (concatenating content with clear delimiters).

## Non-Functional Requirements
- **Performance:** File reading (FileReader API) must be asynchronous and non-blocking.
- **UX:** The interface must remain clean and elegant, highlighting the presence of files without cluttering the view.

## Acceptance Criteria
- [ ] A single `ChatInput` component is used for both new messages and Chairman follow-ups.
- [ ] Dragging a valid text file highlights the input and shows the "Drop files here" overlay.
- [ ] Dropped files appear as chips with names and a delete option.
- [ ] Attempting to drop a file > 1MB or a non-text file triggers a clear error/notification.
- [ ] Clicking the attachment icon opens the system file picker.
- [ ] When a message with files is sent, the models (Stage 1) and Chairman (Stage 3) receive the file content.
- [ ] **The conversation view displays file chips within the user's sent message.**
- [ ] Sending a message clears both the text input and the attached files.

## Out of Scope
- Support for PDF, images, or binary files.
- Persistent file storage on the server (files are ephemeral turn context).
