# Track Specification: Refactor Backend File Transmission

## 1. Overview
This track refactors the mechanism for sending file context from the frontend to the backend. Currently, the frontend concatenates file content directly into the user message string. The goal is to transmit files as structured data in the API payload, store them distinctly in the backend, and handle the prompt construction (concatenation) on the server side just before querying the LLM.

## 2. Functional Requirements

### 2.1 API Update (`backend/main.py`)
-   **Update `SendMessageRequest` Model:**
    -   Add a `files` field: `List[FileContext]`.
    -   Define `FileContext` Pydantic model with:
        -   `name` (str)
        -   `content` (str)
        -   `size` (int, optional)
-   **Update `send_message` and `send_message_stream` Endpoints:**
    -   Accept the new `files` list from the request.
    -   Pass these files to the storage layer.
    -   Use a helper function to construct the final prompt for the LLM.

### 2.2 Storage Update (`backend/storage.py`)
-   **Update `add_user_message` Function:**
    -   Accept an optional `files` argument.
    -   Store the `files` list within the message object in the JSON storage.
    -   Ensure backward compatibility for messages without files.

### 2.3 Prompt Construction Logic
-   **Create Helper Function (`build_prompt_content`):**
    -   Input: User text message, List of File objects.
    -   Output: A single formatted string for the LLM.
    -   Format:
        ```text
        [User Message]

        --- FILE: [filename] ---
        [file content]
        --- END FILE: [filename] ---
        ```
    -   This function is called in `send_message` before `run_full_council` or `query_model`.

### 2.4 Frontend Update (`frontend/src`)
-   **Update `api.js`:**
    -   Modify `sendMessage` and `sendMessageStream` to accept a `files` array containing the full file object (name, content, size).
    -   Update the fetch body to include this `files` array.
-   **Update `App.jsx`:**
    -   **Stop** concatenating file content into the `content` string.
    -   Read file contents using `FileReader`.
    -   Pass the array of file objects (with content) to the `api.sendMessage` calls.

## 3. Non-Functional Requirements
-   **Separation of Concerns:** Storage preserves raw user intent; prompt construction handles LLM formatting.
-   **Clean Code:** Use Pydantic models for validation.
-   **Testability:** Logic for prompt construction should be easily unit testable.

## 4. Acceptance Criteria
-   [ ] **API Payload:** Inspecting the network request shows `files` as a structured array, not part of the `content` string.
-   [ ] **Storage:** Inspecting `data/conversations/*.json` shows messages with a distinct `files` attribute.
-   [ ] **LLM Context:** The LLM still receives the full context (text + files) and answers correctly.
-   [ ] **Backward Compatibility:** Existing conversations (without `files` field) continue to load and function without errors.

## 5. Out of Scope
-   Binary file support (images, PDFs) - strictly text-based files for now.
-   Database migration scripts (assuming JSON schema flexibility handles this).
