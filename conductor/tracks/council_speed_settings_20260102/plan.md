# Plan: Council Speed Settings (Fast vs. Smart)

## Phase 1: Backend Infrastructure
- [ ] Task: Define Model Groups in `backend/config.py`
  - Define `COUNCIL_MODELS_SMART`, `COUNCIL_MODELS_FAST`, `CHAIRMAN_MODEL_SMART`, and `CHAIRMAN_MODEL_FAST`.
- [ ] Task: Update `backend/main.py` request models
  - Add `council_mode: str = "smart"` to `SendMessageRequest`.
- [ ] Task: Refactor `backend/council.py` for dynamic model selection
  - Update `run_full_council` and Stage functions to accept `council_models` and `chairman_model` parameters.
- [ ] Task: Update `backend/main.py` API handlers
  - Update `send_message` and `send_message_stream` to pass the correct models based on `council_mode`.
- [ ] Task: Verify Backend Changes
  - Write a test script or use `curl` to verify that passing `council_mode: "fast"` uses the correct models.
- [ ] Task: Conductor - User Manual Verification 'Phase 1: Backend Infrastructure' (Protocol in workflow.md)

## Phase 2: Frontend Integration
- [ ] Task: Update Frontend API calls
  - Update `frontend/src/api.js` to include `councilMode` in message requests.
- [ ] Task: Add State Management for Council Mode
  - Add `councilMode` to `ThemeContext` (or a new settings context) in `frontend/src/context/ThemeContext.jsx`.
  - Ensure it defaults to "smart" and is not persisted in LocalStorage.
- [ ] Task: Implement Settings UI
  - Update `frontend/src/components/Sidebar.jsx` (or wherever the gear icon popover is) to include the "Council Members" toggle.
  - Style the toggle to match the existing UI.
- [ ] Task: Conductor - User Manual Verification 'Phase 2: Frontend Integration' (Protocol in workflow.md)

## Phase 3: Testing & Polishing
- [ ] Task: End-to-End Testing
  - Manually verify the toggle works and affects the response speed/model attribution.
- [ ] Task: UI/UX Refinement
  - Add tooltips or help text explaining the modes.
- [ ] Task: Conductor - User Manual Verification 'Phase 3: Testing & Polishing' (Protocol in workflow.md)
