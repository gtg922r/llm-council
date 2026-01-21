import '@testing-library/jest-dom';

// Mock window.matchMedia for responsive hooks
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query) => ({
    matches: false, // Default to desktop view in tests
    media: query,
    onchange: null,
    addListener: () => {}, // Deprecated but needed for older browsers
    removeListener: () => {}, // Deprecated but needed for older browsers
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => {},
  }),
});
