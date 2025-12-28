# Plan: UI Improvements & Conversation Management

This plan implements pinning, archiving, duplicating conversations, and collapsible processing stages in the chat interface.

## Phase 1: Backend Support [checkpoint: 6428a72]
Support for pinning, archiving, and duplicating conversations in the storage layer and API.

- [x] Task: TDD - Update Storage Model (Backend) 3592faf
- [x] Task: TDD - Implement Duplicate Conversation Logic (Backend) 59d0565
- [x] Task: TDD - Update API Endpoints (Backend) ae4e624
- [x] Task: Conductor - User Manual Verification 'Phase 1: Backend Support' (Protocol in workflow.md) 6428a72

## Phase 2: Sidebar UI Improvements
Enhanced conversation list with pinning and archiving features.

- [x] Task: TDD - Implement Pinning UI & Sidebar Reordering (Frontend) 3424f21
- [x] Task: TDD - Implement Archiving UI & Archive Toggle (Frontend) 3424f21
- [x] Task: TDD - Implement Permanent Deletion and Bulk Actions (Frontend) 3424f21
- [x] Task: Conductor - User Manual Verification 'Phase 2: Sidebar UI Improvements' (Protocol in workflow.md)

## Phase 3: Header Actions & Conversation Duplication [checkpoint: 40abf1d]
Ellipsis menu in the header for advanced conversation actions.

- [x] Task: TDD - Implement Conversation Header Ellipsis Menu (Frontend) b113ab4
- [x] Task: TDD - Wire up Menu Actions to API (Frontend) b113ab4
- [x] Task: Conductor - User Manual Verification 'Phase 3: Header Actions & Conversation Duplication' (Protocol in workflow.md) 40abf1d

## Phase 4: Collapsible Processing Stages
Improve chat interface density by collapsing intermediate stages.

- [ ] Task: TDD - Create Collapsible Section Component (Frontend)
  - Develop a reusable component for toggling content visibility.
- [ ] Task: TDD - Integrate Collapsible Sections in ChatInterface (Frontend)
  - Wrap Stage 1 (Council) and Stage 2 (Review) in the new component.
  - Ensure they start collapsed by default.
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Collapsible Processing Stages' (Protocol in workflow.md)
