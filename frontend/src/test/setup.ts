import "@testing-library/jest-dom/vitest";
import { afterEach, expect, vi } from "vitest";
import * as matchers from "@testing-library/jest-dom/matchers";
import { cleanup } from "@testing-library/react";

expect.extend(matchers);

function createStorageMock(): Storage {
  const store = new Map<string, string>();
  return {
    get length() {
      return store.size;
    },
    clear() {
      store.clear();
    },
    getItem(key: string) {
      return store.has(key) ? store.get(key) ?? null : null;
    },
    key(index: number) {
      return Array.from(store.keys())[index] ?? null;
    },
    removeItem(key: string) {
      store.delete(key);
    },
    setItem(key: string, value: string) {
      store.set(key, String(value));
    },
  } as Storage;
}

if (typeof window !== "undefined") {
  const storage = window.localStorage;
  if (typeof storage?.clear !== "function") {
    const storageMock = createStorageMock();
    Object.defineProperty(window, "localStorage", {
      configurable: true,
      value: storageMock,
    });
    Object.defineProperty(window, "sessionStorage", {
      configurable: true,
      value: createStorageMock(),
    });
  }
}

// Ensure React Testing Library cleans up between tests
afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

// Expose a Jest-compatible global so tests using `jest.fn` / `jest.clearAllMocks` still work
(globalThis as any).jest = vi;

// Provide a matchMedia mock for components that expect it (e.g. using CSS/media queries)
if (typeof window !== "undefined" && typeof window.matchMedia !== "function") {
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
