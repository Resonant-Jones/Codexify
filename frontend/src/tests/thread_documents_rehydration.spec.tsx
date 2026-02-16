import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { AxiosResponse } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import App from "@/App";
import api from "@/lib/api";
import {
  __resetAuthStateForTests,
  __setAuthStateForTests,
} from "@/lib/authState";

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: () => () => {},
  }),
}));

describe("Thread document rehydration", () => {
  beforeEach(() => {
    localStorage.clear();
    __resetAuthStateForTests();
    __setAuthStateForTests({
      status: "authenticated",
      ready: true,
      token: "test-token",
    });
    window.history.pushState({}, "", "/chat/101");
    Object.defineProperty(window, "matchMedia", {
      writable: true,
      value: vi.fn().mockImplementation((query: string) => ({
        matches: false,
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      })),
    });
  });

  afterEach(() => {
    __resetAuthStateForTests();
    vi.restoreAllMocks();
  });

  it("rehydrates linked documents on bootstrap and thread switch", async () => {
    const user = userEvent.setup();

    const getSpy = vi.spyOn(api, "get").mockImplementation((url: string) => {
      if (url === "/chat/threads") {
        return Promise.resolve({
          data: {
            threads: [
              { id: 101, title: "Thread 101", last_message: "" },
              { id: 202, title: "Thread 202", last_message: "" },
            ],
          },
        } as AxiosResponse);
      }
      if (url === "/media/documents") {
        return Promise.resolve({
          data: { documents: [] },
        } as AxiosResponse);
      }
      if (url === "/threads/101/documents") {
        return Promise.resolve({
          data: {
            ok: true,
            documents: [
              {
                id: "doc-101",
                title: "Bootstrap Plan",
                relation: "attached",
                created_at: "2026-02-11T01:00:00Z",
                format: "md",
              },
            ],
          },
        } as AxiosResponse);
      }
      if (url === "/threads/202/documents") {
        return Promise.resolve({
          data: {
            ok: true,
            documents: [
              {
                id: "doc-202",
                title: "Switch Checklist",
                relation: "attached",
                created_at: "2026-02-11T02:00:00Z",
                format: "md",
              },
            ],
          },
        } as AxiosResponse);
      }
      return Promise.resolve({ data: { documents: [] } } as AxiosResponse);
    });

    render(<App />);

    await user.click(screen.getByRole("button", { name: /^documents$/i }));

    await waitFor(() => {
      expect(
        getSpy.mock.calls.some(([path]) => path === "/threads/101/documents")
      ).toBe(true);
    });

    expect(await screen.findByText("Bootstrap Plan")).toBeInTheDocument();

    await act(async () => {
      window.history.pushState({}, "", "/chat/202");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(
        getSpy.mock.calls.some(([path]) => path === "/threads/202/documents")
      ).toBe(true);
    });

    expect(await screen.findByText("Switch Checklist")).toBeInTheDocument();
    expect(screen.queryByText("Bootstrap Plan")).not.toBeInTheDocument();
  });
});
