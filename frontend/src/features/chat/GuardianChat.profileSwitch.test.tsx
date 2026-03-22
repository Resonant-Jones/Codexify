import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";
import { configureGC } from "@/dcw-services/gc";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatCompletePath: () => "/chat/complete",
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
}));

vi.mock("@/components/ui/dropdown-menu", () => ({
  DropdownMenu: ({ children }: any) => <div>{children}</div>,
  DropdownMenuTrigger: ({ children, asChild, ...props }: any) => {
    if (asChild) return children;
    return (
      <button type="button" {...props}>
        {children}
      </button>
    );
  },
  DropdownMenuContent: ({ children }: any) => <div>{children}</div>,
  DropdownMenuItem: ({ children, onClick, ...props }: any) => (
    <button type="button" onClick={onClick} {...props}>
      {children}
    </button>
  ),
}));

vi.mock("@/features/chat/components", () => ({
  Composer: () => <div data-testid="composer-stub" />,
}));

vi.mock("@/features/chat/ChatView", () => ({
  default: () => <div data-testid="chat-view-stub" />,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/features/chat/useChat", () => ({
  default: () => ({
    messages: [],
    loading: false,
    error: null,
    hasMore: false,
    activateThread: vi.fn(),
    refreshSnapshot: vi.fn().mockResolvedValue([]),
    loadOlderMessages: vi.fn().mockResolvedValue([]),
    completionState: {
      isCompleting: false,
      activeTaskId: null,
      activeThreadId: null,
      startedAt: null,
    },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
    updateCompletionTaskId: vi.fn(),
    startCompletionSession: vi.fn(),
    reassociateCompletionSession: vi.fn(() => true),
    updateCompletionSessionTurnId: vi.fn(() => true),
    finalizeCompletionSession: vi.fn(() => true),
    handleIncomingAssistantMessage: vi.fn(() => false),
    isCompletionInFlight: vi.fn(() => false),
    setCompletionInFlight: vi.fn(),
  }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: () => () => {},
  }),
}));

vi.mock("@/state/contextTrace", () => ({
  setTrace: vi.fn(),
}));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => <div data-testid="prompt-cost-indicator" />,
}));

vi.mock("@/components/SessionRail/SessionRail", () => ({
  default: () => <div data-testid="session-rail-stub" />,
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

type FetchResponseOptions = {
  ok: boolean;
  body: any;
  contentType?: string;
  status?: number;
};

function makeFetchResponse({
  ok,
  body,
  contentType = "application/json",
  status,
}: FetchResponseOptions) {
  return Promise.resolve({
    ok,
    status: status ?? (ok ? 200 : 500),
    headers: {
      get: (key: string) =>
        key.toLowerCase() === "content-type" ? contentType : null,
    },
    json: async () => body,
    text: async () =>
      typeof body === "string" ? body : JSON.stringify(body),
  });
}

function renderChat() {
  return render(
    <GuardianChat
      guardianName="Guardian"
      userName="tester"
      activeThread={{ id: "1", title: "Thread" } as any}
      onSendMessage={vi.fn().mockResolvedValue(undefined)}
      onNewChat={vi.fn()}
      sessionTabs={[
        {
          tabId: "tab-1",
          title: "Tab 1",
          modelId: "default",
          createdAt: "2026-03-06T00:00:00.000Z",
          updatedAt: "2026-03-06T00:00:00.000Z",
        } as any,
      ]}
      activeSessionTabId={"tab-1" as any}
    />
  );
}

describe("GuardianChat profile switching", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    configureGC({ base: "http://backend.test" });
    vi.stubGlobal("fetch", vi.fn());
    mockApi.get.mockImplementation(async (url: string) => {
      if (url === "/llm/catalog") {
        return { data: { providers: [] } };
      }
      if (url === "/health/llm") {
        return { data: { ok: true, status: "online" } };
      }
      if (url === "/chat/1/profile") {
        return {
          data: {
            profile: { id: "default", mode: "cloud" },
            profiles: [],
          },
        };
      }
      return { data: {} };
    });
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("targets the system profiles switch endpoint on success", async () => {
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      makeFetchResponse({ ok: true, body: { ok: true } })
    );
    vi.spyOn(window, "prompt").mockReturnValue("local_mode");

    renderChat();

    fireEvent.click(screen.getByText("Switch profile…"));

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalled();
    });

    const [url, init] = fetchMock.mock.calls[0];
    expect(String(url)).toBe("http://backend.test/api/system-profiles/switch");
    expect(init?.method).toBe("POST");
    expect(JSON.parse(init?.body as string)).toEqual({
      thread_id: 1,
      profile_id: "local_mode",
    });
    expect(mockApi.post).not.toHaveBeenCalledWith(
      "/tools/execute",
      expect.anything()
    );
  });

  it("surfaces switch failures and never falls back to tools.execute", async () => {
    const fetchMock = globalThis.fetch as unknown as ReturnType<typeof vi.fn>;
    fetchMock.mockResolvedValueOnce(
      makeFetchResponse({
        ok: false,
        body: "switch failed",
        contentType: "text/plain",
        status: 500,
      })
    );
    vi.spyOn(window, "prompt").mockReturnValue("local_mode");

    const toastHandler = vi.fn();
    window.addEventListener("cfy:toast", toastHandler);

    renderChat();

    fireEvent.click(screen.getByText("Switch profile…"));

    await waitFor(() => {
      expect(toastHandler).toHaveBeenCalled();
    });

    const event = toastHandler.mock.calls[0][0] as CustomEvent;
    expect(event.detail?.message).toBe("switch failed");
    expect(mockApi.post).not.toHaveBeenCalledWith(
      "/tools/execute",
      expect.anything()
    );

    window.removeEventListener("cfy:toast", toastHandler);
  });
});
