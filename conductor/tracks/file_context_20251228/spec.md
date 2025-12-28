# Track Spec: Drag & Drop File Context

## Goal
Enable users to provide additional context to the LLM Council by dragging and dropping text-based files (or using a file picker) into the chat interface. The content of these files should be included in the context sent to each model, allowing them to answer questions based on the provided documents/code.

## Functional Requirements
1.  **File Input:**
    -   **Drag & Drop:** The chat input area should accept dropped files. Visual feedback (e.g., border highlight) should indicate when a file is being dragged over the zone.
    -   **File Picker:** A "paperclip" or "attachment" icon button should trigger the system file dialog.

2.  **File Staging (UI):**
    -   Selected files should appear as **chips/tags** above the text input field.
    -   Each chip displays the filename and an "x" button to remove the file from the staging area.
    -   Users can attach multiple files to a single message.

3.  **Processing & Transmission:**
    -   **Constraint:** Only text-based files (e.g., `.txt`, `.md`, code files) are allowed.
    -   **Size Limit:** Files larger than ~1MB should be rejected with a user-facing error to prevent token overflow.
    -   **Payload Construction:** When the message is sent, the content of the attached files is read by the frontend.
    -   **Idiomatic Context:** The file content is **concatenated** with the user's text message.
        -   Format:
            ```text
            [User's typed message]

            --- Context File: filename.txt ---
            [File Content]
            ----------------------------------
            ```
        -   This ensures compatibility across different LLM providers (OpenRouter) that may not all support specialized "file" message types similarly.

4.  **Backend Handling:**
    -   The backend receives the single concatenated string. No schema changes are required for the `messages` structure, but the total prompt length will increase.

## Non-Functional Requirements
-   **Performance:** Reading file content client-side should be fast and not freeze the UI.
-   **Clarity:** The distinction between user text and file context must be clear to the LLMs to avoid confusion.

## Acceptance Criteria
-   [ ] Dragging a file over the input area highlights the drop zone.
-   [ ] Dropping a file adds it as a chip above the input.
-   [ ] Clicking the attachment button opens the file picker and adds selected files as chips.
-   [ ] Clicking "x" on a chip removes the file.
-   [ ] Non-text files or files >1MB trigger an alert and are not added.
-   [ ] Sending the message clears the file chips.
-   [ ] The final message sent to the backend includes the file content formatted with clear delimiters.
-   [ ] The LLM Council responses reflect knowledge of the file content.

## Out of Scope
-   PDF parsing or OCR for images.
-   Server-side file storage/upload (files are ephemeral context for the current turn).
-   File persistence across page reloads (unless already handled by message history).
