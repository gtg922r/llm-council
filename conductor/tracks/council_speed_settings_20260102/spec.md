# Specification: Council Speed Settings (Fast vs. Smart)

## Overview
Introduce a new setting in the application's settings (gear icon) that allows users to toggle between two tiers of LLM Council members: **Smart** (High-quality, higher latency) and **Fast** (Lower latency, efficient). This setting will dictate which models are used for the 3-stage orchestration process.

## Functional Requirements
### 1. Model Group Definitions
- **Smart (Default):**
  - Council Members: `openai/gpt-5.2`, `google/gemini-3-pro-preview`, `anthropic/claude-opus-4.5`, `x-ai/grok-4`
  - Chairman: `google/gemini-3-pro-preview`
- **Fast:**
  - Council Members: `google/gemini-2.5-flash-lite`, `google/gemini-2.5-flash`, `x-ai/grok-4.1-fast`
  - Chairman: `google/gemini-3-flash-preview`

### 2. User Interface
- Add a "Council Mode" or "Council Members" toggle/radio group to the existing Settings popover (gear icon).
- Options: "Smart" (selected by default) and "Fast".
- Provide a brief tooltip or subtext explaining the difference (e.g., "Smart: Higher quality, slower" vs "Fast: Rapid responses, lower cost").

### 3. State Management & Persistence
- The setting state will be managed in the frontend (e.g., React context).
- **Session-based:** The setting does NOT persist across browser reloads. It always defaults to "Smart" upon initial load.
- Switching modes applies to the next message sent in any conversation.

### 4. Backend Integration
- Update the API to accept an optional `council_mode` parameter (or similar) in message requests.
- The backend should use the appropriate model group based on the provided mode.
- If no mode is provided, default to "Smart".

## Non-Functional Requirements
- **Performance:** Switching modes should be instantaneous in the UI.
- **Reliability:** Backend should gracefully handle model group selection.

## Acceptance Criteria
- [ ] Settings popover includes the "Council Members" setting.
- [ ] Selecting "Fast" results in Stage 1 and Stage 2 using the Flash/Fast models.
- [ ] Selecting "Fast" results in Stage 3 (Chairman) using `gemini-3-flash-preview`.
- [ ] Refreshing the page resets the setting to "Smart".
- [ ] Existing messages are not retroactively affected or labeled differently, but the next message follows the new setting.

## Out of Scope
- Per-model individual selection.
- Permanent persistence of the setting in a database or LocalStorage.
