# Plan: Dark Mode Support

## Phase 1: Foundation & Theme Management
- [x] Task: Create `ThemeContext` to manage `theme` state ('light', 'dark', 'system') [55f38a8]
- [x] Task: Implement `useTheme` hook for easy access to theme state and toggle [435f048]
- [x] Task: Add unit tests for `ThemeContext` logic (system detection, state transitions) [05ff946]
- [~] Task: Conductor - User Manual Verification 'Phase 1: Foundation & Theme Management' (Protocol in workflow.md)

## Phase 2: CSS Infrastructure & Variables
- [ ] Task: Refactor `index.css` to use CSS variables for all core colors (background, text, border, etc.)
- [ ] Task: Define Light Mode variable values
- [ ] Task: Define Dark Mode variable values (Material Gray palette)
- [ ] Task: Implement a mechanism to apply the `.dark` class (or data-theme attribute) to the document root
- [ ] Task: Add unit tests to verify CSS variable application based on theme state
- [ ] Task: Conductor - User Manual Verification 'Phase 2: CSS Infrastructure & Variables' (Protocol in workflow.md)

## Phase 3: UI Component Styling & Toggle
- [ ] Task: Create a `ThemeToggle` component with Lucide icons (Sun/Moon/Monitor)
- [ ] Task: Integrate `ThemeToggle` into the `Sidebar` component
- [ ] Task: Update `App.css` and component-specific CSS to use the new CSS variables
- [ ] Task: Implement "Elevation" shading for message bubbles in `Stage1`, `Stage2`, and `Stage3` components
- [ ] Task: Add CSS transitions for smooth theme switching
- [ ] Task: Write component tests for `ThemeToggle` and Sidebar integration
- [ ] Task: Conductor - User Manual Verification 'Phase 3: UI Component Styling & Toggle' (Protocol in workflow.md)

## Phase 4: Specialized Content & Refinement
- [ ] Task: Update syntax highlighting styles for `react-markdown` code blocks to use a dark theme
- [ ] Task: Implement `localStorage` persistence for the theme preference
- [ ] Task: Add unit tests for `localStorage` persistence and system preference sync
- [ ] Task: Conductor - User Manual Verification 'Phase 4: Specialized Content & Refinement' (Protocol in workflow.md)
