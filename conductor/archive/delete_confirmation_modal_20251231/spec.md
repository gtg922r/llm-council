# Track Specification: Delete Confirmation Modal

## 1. Overview
This track aims to improve the user experience and visual consistency of the application by replacing the native browser alert (`window.confirm`) with a custom, styled React Modal component for deletion confirmations. This change will affect both the single conversation deletion and the "delete all archived" actions.

## 2. Functional Requirements

### 2.1 Generic Modal Component
-   **Create `components/Modal.jsx`:**
    -   A generic, reusable modal container.
    -   **Backdrop:** A semi-transparent dark overlay covering the entire screen. Clicking this backdrop should close the modal (if configured to be dismissible).
    -   **Positioning:** Centered on the screen.
    -   **Accessibility:** Support closing via the `Esc` key.
    -   **Animation:** Simple fade-in/out for the backdrop and modal content.

### 2.2 Delete Confirmation Implementation
-   **Create `components/DeleteConfirmationModal.jsx` (or similar usage pattern):**
    -   Specific implementation using the generic `Modal`.
    -   **Content:**
        -   Warning Text: Clearly state the destructive nature of the action (e.g., "Are you sure you want to delete this conversation forever?").
        -   Visual Warning: Include a warning icon or text styling (e.g., color).
    -   **Actions:**
        -   **Cancel Button:** Outline/Secondary style. Closes the modal without action.
        -   **Delete Button:** Destructive/Red style. Confirms the action and triggers the deletion callback.

### 2.3 Integration
-   **Refactor `App.jsx`:**
    -   Remove `window.confirm` calls.
    -   Integrate the `DeleteConfirmationModal` (or generic `Modal` configured for delete) for:
        1.  Deleting the currently active conversation.
        2.  Deleting all archived conversations.
    -   Manage modal visibility state (open/closed) and target context (which item is being deleted) within the parent component or a new context if necessary.

## 3. Non-Functional Requirements
-   **Visual Consistency:**
    -   Use existing CSS variables (e.g., `--color-surface`, `--color-text`, `--color-danger`, `--color-elevation-1` vs `--color-elevation-3`) to ensure the modal looks "at home" in both Light and Dark modes.
    -   The backdrop should provide sufficient contrast.
-   **Responsiveness:** The modal should scale appropriately for smaller screens (max-width, padding).

## 4. Acceptance Criteria
-   [ ] **Single Delete:** Clicking "Delete Conversation" opens the custom modal.
    -   Clicking "Cancel", "Esc", or Backdrop closes it without deleting.
    -   Clicking "Delete" deletes the conversation and closes the modal.
-   [ ] **Archive Delete:** Clicking "Delete All Archived" opens the custom modal.
    -   Verify same behavior (Cancel/Delete) as single delete.
-   [ ] **Theming:** Verify the modal matches the current theme (Light/Dark).
-   [ ] **Keyboard Nav:** Verify `Esc` closes the modal.

## 5. Out of Scope
-   Complex focus trapping (unless easily achieved with a lightweight library or simple implementation).
-   "Undo" functionality (Toast notification with undo) - this is strictly a confirmation modal replacement.
