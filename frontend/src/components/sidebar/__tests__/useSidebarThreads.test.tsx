import { act, renderHook } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import useSidebarThreads from "../useSidebarThreads";
import api from "@/lib/api";
import type { Thread } from "@/types/ui";

vi.mock("@/lib/api", () => ({
  default: {
    patch: vi.fn(),
    delete: vi.fn(),
  },
}));

const mockApi = api as unknown as {
  patch: ReturnType<typeof vi.fn>;
  delete: ReturnType<typeof vi.fn>;
};

function createThread(id: string, title?: string, projectId?: string | null): Thread {
  return {
    id,
    title: title ?? `Thread ${id}`,
    lastMessage: "",
    unread: 0,
    participants: [],
    messages: [],
    projectId,
  };
}

function captureToastEvents() {
  const toasts: Array<{ kind?: string; message?: string }> = [];
  const listener = (event: Event) => {
    toasts.push((event as CustomEvent).detail ?? {});
  };
  window.addEventListener("cfy:toast", listener as EventListener);
  return {
    toasts,
    cleanup: () => window.removeEventListener("cfy:toast", listener as EventListener),
  };
}

describe("useSidebarThreads delete flow", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("calls backend delete and removes thread locally on success", async () => {
    mockApi.delete.mockResolvedValueOnce({ data: { ok: true } });
    const toastCapture = captureToastEvents();
    const initialThreads = [createThread("11"), createThread("22")];
    const { result } = renderHook(
      ({ threads }) =>
        useSidebarThreads({
          initialThreads: threads,
        }),
      { initialProps: { threads: initialThreads } }
    );

    await act(async () => {
      await result.current.deleteThread("11");
    });

    expect(mockApi.delete).toHaveBeenCalledWith("/chat/11");
    expect(result.current.threads.map((thread) => thread.id)).toEqual(["22"]);
    expect(
      toastCapture.toasts.some(
        (detail) => detail.kind === "success" && detail.message === "Thread deleted"
      )
    ).toBe(true);
    toastCapture.cleanup();
  });

  it("falls back to legacy delete route when primary route returns 404", async () => {
    mockApi.delete
      .mockRejectedValueOnce({ response: { status: 404 } })
      .mockResolvedValueOnce({ data: { ok: true } });

    const initialThreads = [createThread("11"), createThread("22")];
    const { result } = renderHook(
      ({ threads }) =>
        useSidebarThreads({
          initialThreads: threads,
        }),
      { initialProps: { threads: initialThreads } }
    );

    await act(async () => {
      await result.current.deleteThread("11");
    });

    expect(mockApi.delete.mock.calls.map((call) => call[0])).toEqual([
      "/chat/11",
      "/chat/threads/11",
    ]);
    expect(result.current.threads.map((thread) => thread.id)).toEqual(["22"]);
  });

  it("keeps local thread state intact and emits an error toast on delete failure", async () => {
    mockApi.delete.mockRejectedValueOnce({ response: { status: 500 } });
    const toastCapture = captureToastEvents();
    const initialThreads = [createThread("11"), createThread("22")];
    const { result } = renderHook(
      ({ threads }) =>
        useSidebarThreads({
          initialThreads: threads,
        }),
      { initialProps: { threads: initialThreads } }
    );

    let thrown: any = null;
    try {
      await result.current.deleteThread("11");
    } catch (error) {
      thrown = error;
    }

    expect(thrown).toMatchObject({ response: { status: 500 } });

    expect(result.current.threads.map((thread) => thread.id)).toEqual(["11", "22"]);
    expect(
      toastCapture.toasts.some(
        (detail) =>
          detail.kind === "error" &&
          detail.message === "Delete failed (500). Please try again."
      )
    ).toBe(true);
    toastCapture.cleanup();
  });

  it("treats unknown project ids as General in the sidebar bucket", () => {
    const initialThreads = [
      createThread("11", "General thread"),
      createThread("22", "Imported thread", "imported-project"),
      createThread("33", "Scoped thread", "project-1"),
    ];

    const projects = [
      { id: "general-1", name: "General", icon: "📁" },
      { id: "project-1", name: "Engineering", icon: "🧭" },
    ];

    const { result } = renderHook(
      ({ threads, sidebarProjects }) =>
        useSidebarThreads({
          initialThreads: threads,
          projects: sidebarProjects,
        }),
      {
        initialProps: {
          threads: initialThreads,
          sidebarProjects: projects,
        },
      }
    );

    expect(result.current.scopeLabel).toBe("General");
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual(["11", "22"]);
    expect(result.current.looseCount).toBe(2);
  });

  it("prefers the canonical General project id when an imported alias also cleans to General", () => {
    const initialThreads = [
      createThread("11", "Canonical general thread", "general-2"),
      createThread("22", "Imported general thread", "general-1"),
      createThread("33", "Scoped thread", "project-1"),
    ];

    const projects = [
      {
        id: "general-1",
        name: "ChatGPT - General",
        icon: "📁",
        metadata: { import_source: "chatgpt" },
      },
      { id: "general-2", name: "General", icon: "📁" },
      { id: "project-1", name: "Engineering", icon: "🧭" },
    ];

    const { result } = renderHook(
      ({ threads, sidebarProjects }) =>
        useSidebarThreads({
          initialThreads: threads,
          projects: sidebarProjects,
        }),
      {
        initialProps: {
          threads: initialThreads,
          sidebarProjects: projects,
        },
      }
    );

    expect(result.current.scopeLabel).toBe("General");
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual(["11"]);
    expect(result.current.looseCount).toBe(1);
  });
});
