# Plan: Dark Mode Support

## Phase 1: Foundation & Theme Management [checkpoint: 2a1c312]
- [x] Task: Create `ThemeContext` to manage `theme` state ('light', 'dark', 'system') [55f38a8]
- [x] Task: Implement `useTheme` hook for easy access to theme state and toggle [435f048]
- [x] Task: Add unit tests for `ThemeContext` logic (system detection, state transitions) [05ff946]
- [x] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Theme Management' (Protocol in workflow.md) [2a1c312]

## Phase 2: CSS Infrastructure & Variables [checkpoint: 815af5d]
- [x] Task: Refactor `index.css` to use CSS variables for all core colors (background, text, border, etc.) [1888ff9]
- [x] Task: Define Light Mode variable values [3d5e262]
- [x] Task: Define Dark Mode variable values (Material Gray palette) [36b4af7]
- [x] Task: Implement a mechanism to apply the `.dark` class (or data-theme attribute) to the document root [f74d46b]
- [x] Task: Add unit tests to verify CSS variable application based on theme state [5e29b0f]
- [x] Task: Conductor - User Manual Verification 'Phase 2: CSS Infrastructure & Variables' (Protocol in workflow.md) [815af5d]

## Phase 3: UI Component Styling & Toggle
- [x] Task: Create a `ThemeToggle` component with Lucide icons (Sun/Moon/Monitor) [5bad792]
- [x] Task: Integrate `ThemeToggle` into the `Sidebar` component [35e85b7]
- [x] Task: Wrap `App` with `ThemeProvider` to supply theme context [f3f7517]
- [x] Task: Update `App.css` and component-specific CSS to use the new CSS variables [042d054]
- [x] Task: Implement "Elevation" shading for message bubbles in `Stage1`, `Stage2`, and `Stage3` components [bbc32f6]
- [x] Task: Add CSS transitions for smooth theme switching [cb4c27b]
- [x] Task: Write component tests for `ThemeToggle` and Sidebar integration [608ac7c]
- [~] Task: Conductor - User Manual Verification 'Phase 3: UI Component Styling & Toggle' (Protocol in workflow.md)

## Phase 4: Specialized Content & Refinement
- [x] Task: Refactor file upload UI styling to use theme variables in dark mode [e45a5a2]
- [x] Task: Update syntax highlighting styles for `react-markdown` code blocks to use a dark theme [c2d38b2]
- [x] Task: Implement `localStorage` persistence for the theme preference [1441f8f]
- [x] Task: Add unit tests for `localStorage` persistence and system preference sync [1441f8f]
- [~] Task: Conductor - User Manual Verification 'Phase 4: Specialized Content & Refinement' (Protocol in workflow.md)

## Phase 5: Settings Popover & Toggle Placement
- [x] Task: Move theme toggle into a sidebar settings popover triggered by a gear button [14222a9]
- [x] Task: Update UI tests for settings popover behavior [14222a9]
- [x] Task: Evenly space theme toggle icons within the settings popover [68a4b68]
- [x] Task: Refine hover/active contrast to use lighter shades across the UI [68a4b68]
- [x] Task: Apply accent-tinted hover styling across controls [6944779]
- [~] Task: Conductor - User Manual Verification 'Phase 5: Settings Popover & Toggle Placement' (Protocol in workflow.md)
