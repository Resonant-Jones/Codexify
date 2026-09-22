import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

vi.mock("@/lib/api", async (importOriginal) => ({
  ...await importOriginal<typeof import("@/lib/api")>(),
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
  },
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatThreadsPath: () => "/api/chat/threads",
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  hasRequestAuthCredential: vi.fn(() => true),
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
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

vi.mock("@/features/guardian/components/Composer", () => ({
  Composer: ({
    onSend,
    presentationMode,
  }: {
    onSend?: (text: string) => Promise<void>;
    presentationMode?: "landing" | "conversation";
  }) => (
    <div data-testid="composer-stub" data-presentation-mode={presentationMode}>
      <textarea data-testid="composer-textarea" placeholder="Write a message…" />
      <input data-testid="composer-input" />
      <div data-testid="composer-contenteditable" contentEditable suppressContentEditableWarning />
      <button type="button" data-testid="composer-send" onClick={() => void onSend?.("First prompt")}>
        Send
      </button>
    </div>
  ),
}));

vi.mock("@/features/chat/ChatView", () => ({
  default: () => <div data-testid="chat-view-stub" />,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/features/chat/useChat", () => {
  // Match the hook's stable snapshot/callback identities across presentation renders.
  const snapshot = {
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
  };
  return { default: () => snapshot };
});

vi.mock("@/hooks/useLiveEvents", () => {
  const snapshot = { subscribe: () => () => {} };
  return { useLiveEvents: () => snapshot };
});

vi.mock("@/state/contextTrace", () => ({
  setTrace: vi.fn(),
}));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => <div data-testid="prompt-cost-indicator" />,
}));

vi.mock("@/components/SessionRail/SessionRail", () => ({
  default: ({ onActivateTab, onOpenTab }: any) => (
    <div data-testid="session-rail-stub">
      <button
        type="button"
        data-testid="session-rail-manual-open"
        onClick={() => onOpenTab?.()}
      >
        Open Tab
      </button>
      <button
        type="button"
        data-testid="session-rail-manual-activate"
        onClick={() => onActivateTab?.("tab-2")}
      >
        Activate Tab 2
      </button>
    </div>
  ),
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

const mockApi = api as unknown as {
  get: ReturnType<typeof vi.fn>;
  post: ReturnType<typeof vi.fn>;
};

const BASE_TABS = [
  {
    tabId: "tab-1",
    title: "Tab 1",
    modelId: "default",
    createdAt: "2026-03-06T00:00:00.000Z",
    updatedAt: "2026-03-06T00:00:00.000Z",
  },
  {
    tabId: "tab-2",
    title: "Tab 2",
    modelId: "default",
    createdAt: "2026-03-06T00:00:00.000Z",
    updatedAt: "2026-03-06T00:00:00.000Z",
  },
  {
    tabId: "tab-3",
    title: "Tab 3",
    modelId: "default",
    createdAt: "2026-03-06T00:00:00.000Z",
    updatedAt: "2026-03-06T00:00:00.000Z",
  },
] as const;

type GuardianChatProps = Parameters<typeof GuardianChat>[0];

function setPlatform(platform: string) {
  Object.defineProperty(window.navigator, "platform", {
    configurable: true,
    value: platform,
  });
}

function renderShortcutChat(props: Partial<GuardianChatProps> = {}) {
  const onSessionTabActivate = props.onSessionTabActivate ?? vi.fn();
  const onSessionTabOpen = props.onSessionTabOpen ?? vi.fn();
  const onNewChat = props.onNewChat ?? vi.fn();
  const result = render(
    <GuardianChat
      guardianName="Guardian"
      userName="tester"
      activeThread={{ id: "draft", title: "Draft" } as any}
      onSendMessage={vi.fn().mockResolvedValue(undefined)}
      onNewChat={onNewChat}
      sessionTabs={props.sessionTabs ?? ([...BASE_TABS] as any)}
      activeSessionTabId={props.activeSessionTabId ?? ("tab-1" as any)}
      onSessionTabActivate={onSessionTabActivate as any}
      onSessionTabOpen={onSessionTabOpen}
      {...props}
    />
  );
  return {
    ...result,
    onSessionTabActivate,
    onSessionTabOpen,
    onNewChat,
  };
}

describe("GuardianChat session tab keyboard shortcuts", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    setPlatform("Win32");
    mockApi.get.mockImplementation(async (url: string) => {
      if (url === "/llm/catalog") {
        return { data: { providers: [] } };
      }
      if (url === "/health/llm") {
        return {
          data: {
            ok: true,
            status: "online",
            provider: "local",
            model: "default",
            error: null,
          },
        };
      }
      return { data: {} };
    });
  });

  it("opens a new session tab on Cmd+T for macOS", () => {
    setPlatform("MacIntel");
    const { onSessionTabOpen } = renderShortcutChat();

    const event = new KeyboardEvent("keydown", {
      key: "t",
      metaKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);

    expect(onSessionTabOpen).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("opens a new session tab on Ctrl+T for non-macOS", () => {
    const { onSessionTabOpen } = renderShortcutChat();

    const event = new KeyboardEvent("keydown", {
      key: "t",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);

    expect(onSessionTabOpen).toHaveBeenCalledTimes(1);
    expect(event.defaultPrevented).toBe(true);
  });

  it("activates the next tab on Ctrl+Tab and wraps from last to first", () => {
    const { onSessionTabActivate, rerender } = renderShortcutChat({
      activeSessionTabId: "tab-2" as any,
    });

    const firstEvent = new KeyboardEvent("keydown", {
      key: "Tab",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(firstEvent);
    expect(onSessionTabActivate).toHaveBeenCalledWith("tab-3");
    expect(firstEvent.defaultPrevented).toBe(true);

    rerender(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "draft", title: "Draft" } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[...BASE_TABS] as any}
        activeSessionTabId={"tab-3" as any}
        onSessionTabActivate={onSessionTabActivate as any}
        onSessionTabOpen={vi.fn()}
      />
    );

    const wrapEvent = new KeyboardEvent("keydown", {
      key: "Tab",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(wrapEvent);
    expect(onSessionTabActivate).toHaveBeenLastCalledWith("tab-1");
    expect(wrapEvent.defaultPrevented).toBe(true);
  });

  it("activates the previous tab on Ctrl+Shift+Tab and wraps from first to last", () => {
    const { onSessionTabActivate } = renderShortcutChat({
      activeSessionTabId: "tab-1" as any,
    });

    const event = new KeyboardEvent("keydown", {
      key: "Tab",
      ctrlKey: true,
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(event);

    expect(onSessionTabActivate).toHaveBeenCalledWith("tab-3");
    expect(event.defaultPrevented).toBe(true);
  });

  it("treats next/previous shortcuts as no-op when only one tab exists", () => {
    const { onSessionTabActivate } = renderShortcutChat({
      sessionTabs: [
        {
          tabId: "tab-1",
          title: "Tab 1",
          modelId: "default",
          createdAt: "2026-03-06T00:00:00.000Z",
          updatedAt: "2026-03-06T00:00:00.000Z",
        } as any,
      ],
      activeSessionTabId: "tab-1" as any,
    });

    const nextEvent = new KeyboardEvent("keydown", {
      key: "Tab",
      ctrlKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(nextEvent);

    const previousEvent = new KeyboardEvent("keydown", {
      key: "Tab",
      ctrlKey: true,
      shiftKey: true,
      bubbles: true,
      cancelable: true,
    });
    document.dispatchEvent(previousEvent);

    expect(onSessionTabActivate).not.toHaveBeenCalled();
    expect(nextEvent.defaultPrevented).toBe(true);
    expect(previousEvent.defaultPrevented).toBe(true);
  });

  it("keeps next-tab switching active when focus is in text-entry controls", () => {
    const { onSessionTabActivate } = renderShortcutChat({
      activeSessionTabId: "tab-1" as any,
    });

    const targets = [
      screen.getByTestId("composer-textarea"),
      screen.getByTestId("composer-input"),
      screen.getByTestId("composer-contenteditable"),
    ];

    for (const target of targets) {
      (target as HTMLElement).focus();
      fireEvent.keyDown(target, { key: "Tab", ctrlKey: true });
    }

    expect(onSessionTabActivate).toHaveBeenCalledTimes(3);
    expect(onSessionTabActivate).toHaveBeenNthCalledWith(1, "tab-2");
    expect(onSessionTabActivate).toHaveBeenNthCalledWith(2, "tab-2");
    expect(onSessionTabActivate).toHaveBeenNthCalledWith(3, "tab-2");
  });

  it("routes keyboard and manual tab activation through the same callback path", async () => {
    const user = userEvent.setup();
    const { onSessionTabActivate } = renderShortcutChat({
      activeSessionTabId: "tab-1" as any,
    });

    await user.click(screen.getByTestId("session-rail-manual-activate"));
    fireEvent.keyDown(document, { key: "Tab", ctrlKey: true });

    expect(onSessionTabActivate).toHaveBeenNthCalledWith(1, "tab-2");
    expect(onSessionTabActivate).toHaveBeenNthCalledWith(2, "tab-2");
  });

  it("adds only the explicit finite, reduced-motion-safe sidebar hint", async () => {
    const onSidebarToggle = vi.fn();
    const props = {
      activeThread: { id: "42", title: "Active" } as any,
      isSidebarVisible: false, sidebarRevealAttention: true, onSidebarToggle,
    };
    const view = renderShortcutChat(props);
    const reveal = screen.getByRole("button", { name: "Show sidebar" });
    expect(reveal).toHaveAttribute("data-sidebar-attention", "intro");
    const style = view.container.querySelector("style")?.textContent;
    expect(style).toContain("prefers-reduced-motion: no-preference");
    expect(style).toContain("guardian-sidebar-glint 700ms ease-in-out 2");
    expect(style).not.toContain("infinite");
    view.rerender(<GuardianChat guardianName="Guardian" userName="tester" onSendMessage={vi.fn().mockResolvedValue(undefined)} {...props} />);
    expect(screen.getByRole("button", { name: "Show sidebar" })).toBe(reveal);
    await userEvent.setup().click(reveal);
    expect(onSidebarToggle).toHaveBeenCalledTimes(1);
    view.rerender(<GuardianChat guardianName="Guardian" userName="tester" onSendMessage={vi.fn().mockResolvedValue(undefined)} {...props} sidebarRevealAttention={false} />);
    expect(reveal).not.toHaveAttribute("data-sidebar-attention");
  });

  it("leaves an ordinarily hidden sidebar reveal unanimated", () => {
    renderShortcutChat({ isSidebarVisible: false, onSidebarToggle: vi.fn() });
    expect(screen.getByRole("button", { name: "Show sidebar" })).not.toHaveAttribute("data-sidebar-attention");
  });

  it("renders the prompt-first state with the shared Composer and no transcript", () => {
    renderShortcutChat();

    const landingUnit = screen.getByTestId("guardian-landing-unit");
    const greeting = screen.getByTestId("guardian-prompt-first-surface");
    const composer = screen.getByTestId("composer-stub");

    expect(greeting).toHaveTextContent(/tester/);
    expect(landingUnit).toContainElement(greeting);
    expect(landingUnit).toContainElement(composer);
    expect(greeting.compareDocumentPosition(composer)).toBe(
      Node.DOCUMENT_POSITION_FOLLOWING
    );
    expect(composer).toBeInTheDocument();
    expect(composer).toHaveAttribute(
      "data-presentation-mode",
      "landing"
    );
    expect(screen.queryByTestId("chat-view-stub")).not.toBeInTheDocument();
  });

  it("retains the active-thread transcript layout", () => {
    renderShortcutChat({ activeThread: { id: "42", title: "Active" } as any });

    expect(screen.getByTestId("chat-view-stub")).toBeInTheDocument();
    expect(screen.queryByTestId("guardian-prompt-first-surface")).not.toBeInTheDocument();
    expect(screen.getByTestId("composer-stub")).toHaveAttribute(
      "data-presentation-mode",
      "conversation"
    );
  });

  it("creates a durable thread only after the first prompt is submitted", async () => {
    const user = userEvent.setup();
    const onThreadPersisted = vi.fn();
    mockApi.post.mockImplementation(async (url: string) => {
      if (url === "/api/chat/threads") {
        return { data: { id: 77 } };
      }
      if (url === "/chat/77/complete") {
        return { data: { task_id: "task-77" } };
      }
      return { data: {} };
    });

    renderShortcutChat({ onThreadPersisted });

    expect(mockApi.post).not.toHaveBeenCalled();
    await user.click(screen.getByTestId("composer-send"));

    await waitFor(() => {
      expect(mockApi.post).toHaveBeenCalledWith(
        "/api/chat/threads",
        expect.objectContaining({ title: "First prompt" })
      );
    });
    expect(mockApi.post).toHaveBeenCalledWith("/chat/77/messages", {
      role: "user",
      content: "First prompt",
      project_id: undefined,
    });
    expect(onThreadPersisted).toHaveBeenCalledWith(
      77,
      "First prompt",
      expect.objectContaining({ tabId: "tab-1" })
    );
    expect(window.location.pathname).toBe("/chat/77");
  });
});
