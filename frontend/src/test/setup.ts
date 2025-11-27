import "@testing-library/jest-dom/vitest";
import { afterEach, expect, vi } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";
import { cleanup } from "@testing-library/react";

expect.extend(matchers);

// Ensure React Testing Library cleans up between tests
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Expose a Jest-compatible global so tests using `jest.fn` / `jest.clearAllMocks` still work
(globalThis as any).jest = vi;

// Provide a matchMedia mock for components that expect it (e.g. using CSS/media queries)
if (typeof window !== "undefined" && !("matchMedia" in window)) {
  Object.defineProperty(window, "matchMedia", {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener() {},
      removeListener() {},
      addEventListener() {},
      removeEventListener() {},
      dispatchEvent() {
        return false;
      },
    }),
  });
}
