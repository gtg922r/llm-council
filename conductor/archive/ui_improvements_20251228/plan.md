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

## Phase 4: Collapsible Processing Stages [checkpoint: 843d39e]
Improve chat interface density by collapsing intermediate stages.

- [x] Task: TDD - Create Collapsible Section Component (Frontend) 53c9532
- [x] Task: TDD - Integrate Collapsible Sections in ChatInterface (Frontend) 843d39e
- [x] Task: Conductor - User Manual Verification 'Phase 4: Collapsible Processing Stages' (Protocol in workflow.md) 843d39e

## Phase 5: Lucide Icon Integration [checkpoint: 587b518]
Replace emojis and simple text icons with a consistent icon library.

- [x] Task: TDD - Install lucide-react (Frontend) 35f397a
- [x] Task: TDD - Update Sidebar Icons (Frontend) 587b518
- [x] Task: TDD - Update Header Menu Icons (Frontend) 587b518
- [x] Task: TDD - Update Collapsible Section Icons (Frontend) 587b518
- [x] Task: Conductor - User Manual Verification 'Phase 5: Lucide Icon Integration' (Protocol in workflow.md) 587b518

## Phase 6: Title Editing [checkpoint: b3ea609]
Allow users to click and edit the conversation title in the main header.

- [x] Task: TDD - Create EditableTitle Component (Frontend) 6d41c72
- [x] Task: TDD - Integrate EditableTitle into ChatInterface (Frontend) b3ea609
- [x] Task: Conductor - User Manual Verification 'Phase 6: Title Editing' (Protocol in workflow.md) b3ea609


