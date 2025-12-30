# Implementation Plan: Multi-Conversation UX Improvements

## Phase 1: Backend Persistence & API [checkpoint: bc1181a]
Introduce the `has_unread` field to the data model and expose it via the API.

- [x] Task: Backend - Update `storage.py` to include `has_unread` in conversation model and default it to `False` [88d77fd]
- [x] Task: Backend - Update `main.py` Pydantic models (`ConversationMetadata`, `Conversation`) to include `has_unread` [0cf6618]
- [x] Task: Backend - Update `add_assistant_message` in `storage.py` to set `has_unread = True` [4eaed7d]
- [x] Task: Backend - Create/Update `PATCH /api/conversations/{id}` logic to allow clearing `has_unread` [bf7987f]
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Backend Persistence & API' (Protocol in workflow.md)

## Phase 2: Frontend Unread Indicator (Blue Dot)
Implement the visual "unread" indicator in the sidebar and the logic to clear it.

- [x] Task: Frontend - Update `api.js` to handle the new `has_unread` field and provide a `markAsRead` function [9cb8f66]
- [ ] Task: Frontend - Modify `Sidebar.jsx` to display a blue dot if `conv.has_unread` is true
- [ ] Task: Frontend - Add logic in `App.jsx` to call `markAsRead` when a conversation is selected
- [ ] Task: Frontend - Add logic in `App.jsx` to automatically clear `has_unread` if a message arrives while the conversation is already active
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Unread Indicator (Blue Dot)' (Protocol in workflow.md)

## Phase 3: Frontend Pending Indicator (Pulsing Grey Dot)
Implement the visual "pending" indicator to track background processing.

- [ ] Task: Frontend - Add `pendingConversations` state (Set/Map) to `App.jsx`
- [ ] Task: Frontend - Update `handleSendMessage` to add/remove conversation IDs from `pendingConversations`
- [ ] Task: Frontend - Update `Sidebar.jsx` to display a pulsing grey dot if a conversation ID is in `pendingConversations`
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Frontend Pending Indicator (Pulsing Grey Dot)' (Protocol in workflow.md)

## Phase 4: CSS Styling & Polish
Finalize the animations and visual styles for both indicators.

- [ ] Task: Frontend - Define CSS for the blue dot and the pulsing grey dot in `Sidebar.css`
- [ ] Task: Frontend - Ensure responsive design and mobile-friendly touch targets for the indicators
- [ ] Task: Conductor - User Manual Verification 'Phase 4: CSS Styling & Polish' (Protocol in workflow.md)
