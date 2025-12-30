# Track Specification: Multi-Conversation UX Improvements

## 1. Overview
This track focuses on improving the user experience when managing multiple concurrent conversations. It introduces visual indicators in the sidebar to show when a background conversation is processing ("pending") and when it has finished processing but hasn't been viewed yet ("unread").

## 2. Functional Requirements

### 2.1 Backend Data Model
-   **Update `backend/storage.py`:**
    -   Add a `has_unread` boolean field to the conversation data model.
    -   Default `has_unread` to `False` for new conversations.
    -   Expose this field in the `ConversationMetadata` and `Conversation` Pydantic models in `backend/main.py`.

### 2.2 Backend Logic
-   **Mark as Unread:** When an assistant message finishes generating (Stream Complete) for a conversation that is *not* the currently active one (handled via frontend logic triggering an update, or backend inference), the system should update the conversation's `has_unread` status to `True`.
    -   *Refinement:* Since the backend doesn't inherently know which conversation is "active" on the frontend, the backend will simply set `has_unread = True` whenever a new assistant message is fully added. The frontend will be responsible for immediately clearing this if the user is watching it, or the backend can blindly set it and the frontend clears it upon "read".
    -   *Decision:* The backend `add_assistant_message` function will set `has_unread = True`.

-   **Mark as Read:** Provide an API endpoint (or update existing ones) to set `has_unread` to `False`.
    -   Likely a `PATCH /api/conversations/{id}` update.

### 2.3 Frontend UI - Sidebar
-   **Pending Indicator:**
    -   **Trigger:** Display when a request has been sent to a conversation but processing is not yet complete.
    -   **Visual:** A subtle pulsing grey dot (similar size/location to the "new" dot).
    -   **Logic:** The frontend must track "pending" states for conversations based on its own network activity (since it initiates the requests).

-   **Unread Indicator:**
    -   **Trigger:** Display when a conversation has `has_unread: true`.
    -   **Visual:** A solid blue dot.
    -   **Logic:**
        -   If the conversation is currently active (open and focused), the blue dot should *not* appear (or be immediately dismissed).
        -   If the conversation is in the background, the blue dot appears upon completion.

### 2.4 Frontend Logic - State Management
-   **Pending State:** Managed locally in React state (e.g., a `pendingConversations` set/map).
-   **Unread State:** Sourced from the backend `has_unread` field.
-   **Dismissal:**
    -   When a user clicks/selects a conversation, trigger the "Mark as Read" action (API call) to clear the blue dot.
    -   If the user is currently viewing the conversation when a message arrives, automatically trigger "Mark as Read" or prevent the state from persisting as unread.

## 3. Non-Functional Requirements
-   **Persistence:** The "unread" state must persist across browser refreshes (ensured by backend storage).
-   **Subtlety:** Indicators should be distinct but not distracting (pulsing grey for pending, solid blue for unread).
-   **Performance:** Polling or state updates for the indicators should not degrade sidebar rendering performance.

## 4. Acceptance Criteria
-   [ ] **Pending:** Sending a message in Conversation A shows a pulsing grey dot in the sidebar for Conversation A.
-   [ ] **Unread:** When Conversation A finishes (while viewing Conversation B), the grey dot is replaced by a solid blue dot.
-   [ ] **Persistence:** Refreshing the page preserves the blue dot for unread conversations.
-   [ ] **Dismissal:** Clicking Conversation A removes the blue dot.
-   [ ] **Active View:** Sending a message while staying in Conversation A does *not* result in a persistent blue dot (it might flicker or be suppressed).

## 5. Out of Scope
-   Real-time websocket push notifications for "unread" status (we will rely on the existing response flow or simple state re-fetching).
-   Unread counts (just a binary "has unread" dot).
