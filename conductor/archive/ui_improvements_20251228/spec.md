# Specification: UI Improvements & Conversation Management

## Overview
This track focuses on enhancing the user interface and conversation management capabilities of the Symposia application. Key features include archiving, pinning, and duplicating conversations, as well as improving the density of the chat interface by collapsing intermediate processing stages.

## Functional Requirements

### 1. Conversation Management (Sidebar)
- **Pinning:** Users can "pin" conversations. Pinned conversations must always appear at the top of the sidebar list.
- **Archiving:** 
    - An "Archive" icon appears when hovering over a conversation in the sidebar.
    - Clicking the icon moves the conversation to a dedicated "Archived" section.
- **Archived Section:**
    - A collapsible accordion section at the bottom of the sidebar containing all archived conversations.
    - **Restore:** Users can move a conversation from "Archived" back to the active list.
    - **Permanent Deletion:** Mousing over an archived conversation exposes a trashcan icon to delete the conversation permanently.
    - **Bulk Action:** An "Empty Trash" button to permanently delete all archived conversations.
- **Persistence:** All states (pinned, archived) must be stored in the backend to ensure consistency across sessions.

### 2. Conversation Header Actions
- A "three dots" (ellipsis) menu icon in the top-right title bar of the active conversation.
- **Menu Options:**
    - **Duplicate:** Creates a copy of the current conversation, including all messages and council steps up to the current point.
    - **Archive:** Moves the current conversation to the archive.
    - **Delete:** Permanently deletes the current conversation.

### 3. Chat Interface Refinement
- **Collapsible Stages:**
    - Stage 1 (Council Responses) and Stage 2 (Peer Reviews) must be wrapped in collapsible components.
    - By default, these stages must start in a **collapsed** state to focus the user on the final synthesis.
    - Users can toggle these sections per-message to inspect the intermediate reasoning/reviews.

## Non-Functional Requirements
- **Responsive Design:** UI elements should remain functional and visually appealing on various screen sizes.
- **State Consistency:** UI should immediately reflect backend changes (e.g., pinning/archiving) without requiring a full page refresh.

## Acceptance Criteria
- [ ] Conversations can be pinned/unpinned, and the order reflects this correctly.
- [ ] Conversations can be archived and restored.
- [ ] "Archived" section is collapsible and supports permanent deletion (individual and bulk).
- [ ] The header menu correctly triggers duplicate, archive, and delete actions.
- [ ] Stage 1 and Stage 2 content is hidden by default but accessible via a toggle.
- [ ] All management states persist after a page reload.

## Out of Scope
- Search functionality within conversations.
- Editing existing messages in a conversation.
