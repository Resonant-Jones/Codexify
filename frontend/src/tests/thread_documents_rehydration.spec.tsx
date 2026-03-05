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

// JSDOM lacks scrollIntoView in some environments; stub for auto-scroll logic
if (!Element.prototype.scrollIntoView) {
  Element.prototype.scrollIntoView = vi.fn();
}

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

    const getSpy = vi.spyOn(api, "get").mockImplementation((url: string, config?: any) => {
      if (url === "/api/projects") {
        return Promise.resolve({
          data: [{ id: 1, name: "General" }],
        } as AxiosResponse);
      }
      if (url === "/chat/threads") {
        return Promise.resolve({
          data: {
            threads: [
              { id: 101, title: "Thread 101", last_message: "", project_id: 11 },
              { id: 202, title: "Thread 202", last_message: "", project_id: 22 },
            ],
          },
        } as AxiosResponse);
      }
      if (url === "/media/documents") {
        const projectId = Number(config?.params?.project_id ?? 0);
        if (projectId === 11) {
          return Promise.resolve({
            data: {
              documents: [
                {
                  id: "doc-101",
                  title: "Bootstrap Plan",
                  filename: "Bootstrap Plan.md",
                  thread_id: 101,
                  project_id: 11,
                  format: "md",
                },
                {
                  id: "doc-101-other",
                  title: "Other Thread Doc",
                  filename: "Other Thread Doc.md",
                  thread_id: 999,
                  project_id: 11,
                  format: "md",
                },
              ],
            },
          } as AxiosResponse);
        }
        if (projectId === 22) {
          return Promise.resolve({
            data: {
              documents: [
                {
                  id: "doc-202",
                  title: "Switch Checklist",
                  filename: "Switch Checklist.md",
                  thread_id: 202,
                  project_id: 22,
                  format: "md",
                },
              ],
            },
          } as AxiosResponse);
        }
        return Promise.resolve({
          data: { documents: [] },
        } as AxiosResponse);
      }
      return Promise.resolve({ data: { documents: [] } } as AxiosResponse);
    });

    render(<App />);

    await user.click(screen.getByRole("button", { name: /^documents$/i }));

    await waitFor(() => {
      expect(
        getSpy.mock.calls.some(
          ([path, cfg]) =>
            path === "/media/documents" &&
            Number((cfg as any)?.params?.project_id) === 11
        )
      ).toBe(true);
    });

    expect(await screen.findByText("Bootstrap Plan")).toBeInTheDocument();

    await act(async () => {
      window.history.pushState({}, "", "/chat/202");
      window.dispatchEvent(new PopStateEvent("popstate"));
    });

    await waitFor(() => {
      expect(
        getSpy.mock.calls.some(
          ([path, cfg]) =>
            path === "/media/documents" &&
            Number((cfg as any)?.params?.project_id) === 22
        )
      ).toBe(true);
    });

    expect(await screen.findByText("Switch Checklist")).toBeInTheDocument();
    expect(screen.queryByText("Bootstrap Plan")).not.toBeInTheDocument();
  });
});
