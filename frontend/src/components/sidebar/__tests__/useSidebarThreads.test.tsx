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

function createThread(id: string, overrides: Partial<Thread> = {}): Thread {
  return {
    id,
    title: `Thread ${id}`,
    lastMessage: "",
    unread: 0,
    participants: [],
    messages: [],
    ...overrides,
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

    let thrown: unknown = null;
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
});

describe("useSidebarThreads provenance filters", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    window.localStorage.clear();
  });

  it("deduplicates canonical provenance options by source key and filters every matching imported thread", () => {
    const initialThreads = [
      createThread("11", {
        projectId: "project-1",
        title: "ChatGPT import A",
        metadata: { import_source: "chatgpt" },
      }),
      createThread("22", {
        projectId: "project-1",
        title: "ChatGPT import B",
        metadata: { provider: "ChatGPT" },
      }),
      createThread("33", {
        projectId: "project-1",
        title: "OpenAI import",
        metadata: { source: "openai" },
      }),
      createThread("44", {
        projectId: "project-1",
        title: "Native thread",
      }),
    ];

    const { result } = renderHook(
      ({ threads }) =>
        useSidebarThreads({
          initialThreads: threads,
          projectId: "project-1",
          projects: [{ id: "project-1", name: "Engineering", icon: "🧭" }],
        }),
      { initialProps: { threads: initialThreads } }
    );

    expect(result.current.provenanceOptions).toEqual([
      { value: "chatgpt", label: "ChatGPT" },
      { value: "openai", label: "OpenAI" },
    ]);
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual([
      "11",
      "22",
      "33",
      "44",
    ]);

    act(() => {
      result.current.setProvenanceFilter("chatgpt");
    });
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual(["11", "22"]);

    act(() => {
      result.current.setProvenanceFilter("openai");
    });
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual(["33"]);

    act(() => {
      result.current.setProvenanceFilter(null);
    });
    expect(result.current.displayThreads.map((thread) => thread.id)).toEqual([
      "11",
      "22",
      "33",
      "44",
    ]);
  });
});
