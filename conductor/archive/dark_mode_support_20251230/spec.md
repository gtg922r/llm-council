# Spec: Dark Mode Support

## Overview
Add a high-quality, elegant dark mode to the Symposia application. The implementation will prioritize user comfort, modern aesthetics (Material-inspired dark grays), and seamless integration with system settings while providing manual overrides.

## Functional Requirements
- **System Detection:** Automatically detect and apply the user's system/browser color scheme preference (`prefers-color-scheme`) on initial load.
- **Manual Toggle:** Provide a UI toggle (e.g., in the Sidebar) to switch between Light and Dark modes.
- **Persistence:** Save the user's manual preference (Light, Dark, or System) in local storage so it persists across sessions.
- **Theme Application:**
    - Update the background, text colors, and component styles (Sidebar, Message Bubbles, Inputs) when the theme changes.
    - Message bubbles should use elevation (varying dark gray shades) to create depth in dark mode.
- **Syntax Highlighting:** Update code block styling to use a dark-compatible theme (e.g., Atom One Dark or similar).

## Non-Functional Requirements
- **Performance:** Theme switching should be instantaneous without page reloads.
- **Elegance:** Use CSS transitions (`0.3s ease`) for color changes to ensure a polished feel.
- **Accessibility:** Ensure all color combinations meet WCAG AA contrast standards in both modes.

## Acceptance Criteria
- [ ] Application starts in dark mode if the system preference is set to dark.
- [ ] User can manually toggle between modes via a Sidebar button.
- [ ] Manual preference survives a page refresh.
- [ ] Code blocks are legible and styled for dark mode.
- [ ] Message bubbles are distinct from the background via elevation/shading.

## Out of Scope
- Custom accent color selection (beyond the default brand colors).
- High-contrast "Pure Black" mode (sticking to Material Grays as specified).
