# Plan: UI Improvements & Conversation Management

This plan implements pinning, archiving, duplicating conversations, and collapsible processing stages in the chat interface.

## Phase 1: Backend Support
Support for pinning, archiving, and duplicating conversations in the storage layer and API.

- [x] Task: TDD - Update Storage Model (Backend) 3592faf
  - Add `is_pinned` and `is_archived` fields to Conversation model.
  - Update `storage.py` to handle these fields.
- [x] Task: TDD - Implement Duplicate Conversation Logic (Backend) 59d0565
  - Add a method in `storage.py` to clone a conversation and its messages.
- [x] Task: TDD - Update API Endpoints (Backend) ae4e624
  - Update GET `/conversations` to support filtering or include status flags.
  - Add PATCH `/conversations/{id}` to update pinned/archived status.
  - Add POST `/conversations/{id}/duplicate` endpoint.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Backend Support' (Protocol in workflow.md)

## Phase 2: Sidebar UI Improvements
Enhanced conversation list with pinning and archiving features.

- [ ] Task: TDD - Implement Pinning UI & Sidebar Reordering (Frontend)
  - Update `Sidebar.jsx` to group and sort pinned conversations at the top.
  - Add pin/unpin visual indicators.
- [ ] Task: TDD - Implement Archiving UI & Archive Toggle (Frontend)
  - Add archive icon on hover in `Sidebar.jsx`.
  - Implement the "Archived" accordion section at the bottom.
- [ ] Task: TDD - Implement Permanent Deletion and Bulk Actions (Frontend)
  - Add trashcan icon for archived items.
  - Implement "Empty Trash" functionality.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Sidebar UI Improvements' (Protocol in workflow.md)

## Phase 3: Header Actions & Conversation Duplication
Ellipsis menu in the header for advanced conversation actions.

- [ ] Task: TDD - Implement Conversation Header Ellipsis Menu (Frontend)
  - Add a dropdown/popover component in the conversation title bar.
  - Options: Duplicate, Archive, Delete.
- [ ] Task: TDD - Wire up Menu Actions to API (Frontend)
  - Connect Duplicate action to the new backend endpoint.
  - Ensure UI updates immediately after archiving or deleting from the header.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Header Actions & Conversation Duplication' (Protocol in workflow.md)

## Phase 4: Collapsible Processing Stages
Improve chat interface density by collapsing intermediate stages.

- [ ] Task: TDD - Create Collapsible Section Component (Frontend)
  - Develop a reusable component for toggling content visibility.
- [ ] Task: TDD - Integrate Collapsible Sections in ChatInterface (Frontend)
  - Wrap Stage 1 (Council) and Stage 2 (Review) in the new component.
  - Ensure they start collapsed by default.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Collapsible Processing Stages' (Protocol in workflow.md)
