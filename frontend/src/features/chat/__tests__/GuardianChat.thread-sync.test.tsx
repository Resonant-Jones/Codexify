import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import GuardianChat from "@/features/chat/GuardianChat";
import type { ComposerInferenceMode } from "@/types/inference";
import type { Thread, ThreadConfig } from "@/types/ui";

const liveEventHandlers = vi.hoisted(
  () =>
    new Map<
      string,
      Set<(event: { type: string; data: unknown }) => void>
    >()
);

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

const chatMocks = vi.hoisted(() => {
  return {
    activateThread: vi.fn().mockResolvedValue([]),
    refreshSnapshot: vi.fn().mockResolvedValue([]),
    loadOlderMessages: vi.fn().mockResolvedValue([]),
    completionState: {
      isCompleting: false,
      activeTaskId: null as string | null,
      activeThreadId: null as number | null,
      startedAt: null as number | null,
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
});

const inferenceMocks = vi.hoisted(() => {
  const state = {
    phase: "idle",
    threadId: null as number | null,
    taskId: null as string | null,
    providerId: null as string | null,
    modelId: null as string | null,
    mode: "default",
    startedAt: null as number | null,
    updatedAt: Date.now(),
    statusText: null as string | null,
    detailText: null as string | null,
    errorText: null as string | null,
    canCancel: false,
    canSwitchToFast: false,
    isPendingCancel: false,
  };

  return {
    state,
    requestCancel: vi.fn(async () => true),
    reset: vi.fn(() => {
      state.phase = "idle";
      state.threadId = null;
      state.taskId = null;
      state.providerId = null;
      state.modelId = null;
      state.mode = "default";
      state.startedAt = null;
      state.updatedAt = Date.now();
      state.statusText = null;
      state.detailText = null;
      state.errorText = null;
      state.canCancel = false;
      state.canSwitchToFast = false;
      state.isPendingCancel = false;
    }),
    startRequest: vi.fn(
      ({
        threadId,
        providerId,
        modelId,
        mode,
      }: {
        threadId: number;
        providerId: string | null;
        modelId: string | null;
        mode: string;
      }) => {
        state.phase = "sending";
        state.threadId = threadId;
        state.providerId = providerId;
        state.modelId = modelId;
        state.mode = mode;
        state.taskId = null;
        state.startedAt = Date.now();
        state.updatedAt = Date.now();
        state.canCancel = false;
        state.canSwitchToFast = false;
        state.isPendingCancel = false;
      }
    ),
    attachTask: vi.fn((taskId: string) => {
      state.taskId = taskId;
      state.phase = "streaming";
      state.updatedAt = Date.now();
      state.canCancel = true;
      state.canSwitchToFast = false;
    }),
    markCompleted: vi.fn(() => {
      state.phase = "completed";
      state.updatedAt = Date.now();
      state.canCancel = false;
      state.canSwitchToFast = false;
      state.isPendingCancel = false;
    }),
    markFailed: vi.fn((errorText: string) => {
      state.phase = "failed";
      state.errorText = errorText;
      state.updatedAt = Date.now();
      state.canCancel = false;
      state.canSwitchToFast = false;
      state.isPendingCancel = false;
    }),
    markCancelled: vi.fn(() => {
      state.phase = "cancelled";
      state.updatedAt = Date.now();
      state.canCancel = false;
      state.canSwitchToFast = false;
      state.isPendingCancel = false;
    }),
  };
});

vi.mock("@/lib/api", () => ({
  default: apiSpies,
  buildChatCompletePath: (threadId: string | number) =>
    `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  updateThreadConfig: async (
    threadId: string | number,
    patch: Record<string, unknown>
  ) => {
    const response = await apiSpies.patch(
      `/chat/threads/${threadId}/config`,
      patch
    );
    return response?.data ?? {};
  },
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
    activateThread: chatMocks.activateThread,
    refreshSnapshot: chatMocks.refreshSnapshot,
    loadOlderMessages: chatMocks.loadOlderMessages,
    completionState: chatMocks.completionState,
    startCompletion: chatMocks.startCompletion,
    endCompletion: chatMocks.endCompletion,
    updateCompletionTaskId: chatMocks.updateCompletionTaskId,
    startCompletionSession: chatMocks.startCompletionSession,
    reassociateCompletionSession: chatMocks.reassociateCompletionSession,
    updateCompletionSessionTurnId: chatMocks.updateCompletionSessionTurnId,
    finalizeCompletionSession: chatMocks.finalizeCompletionSession,
    handleIncomingAssistantMessage: chatMocks.handleIncomingAssistantMessage,
    isCompletionInFlight: chatMocks.isCompletionInFlight,
    setCompletionInFlight: chatMocks.setCompletionInFlight,
  }),
}));

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: (
      eventType: string,
      handler: (event: { type: string; data: unknown }) => void
    ) => {
      const listeners = liveEventHandlers.get(eventType) ?? new Set();
      listeners.add(handler);
      liveEventHandlers.set(eventType, listeners);
      return () => {
        const existing = liveEventHandlers.get(eventType);
        if (!existing) return;
        existing.delete(handler);
        if (existing.size === 0) {
          liveEventHandlers.delete(eventType);
        }
      };
    },
  }),
}));

vi.mock("@/features/chat/hooks/useInferenceRequestState", () => ({
  describeInferenceRequestState: () => ({
    canonicalState: "idle",
    delayDetailText: null,
    timings: {},
  }),
  useInferenceRequestState: () => ({
    state: inferenceMocks.state,
    startRequest: inferenceMocks.startRequest,
    attachTask: inferenceMocks.attachTask,
    markCompleted: inferenceMocks.markCompleted,
    markFailed: inferenceMocks.markFailed,
    markCancelled: inferenceMocks.markCancelled,
    requestCancel: inferenceMocks.requestCancel,
    reset: inferenceMocks.reset,
  }),
}));

vi.mock("@/features/chat/hooks/useLlmCatalog", () => ({
  isChatSelectableModel: () => true,
  describeModelCapability: () => "Text-only chat",
  useLlmCatalog: () => {
    const providers = [
      {
        id: "local",
        displayName: "Local",
        enabled: true,
        authorized: true,
        available: true,
        models: [
          {
            id: "qwen3.5:14b",
            canonicalId: "qwen3.5:14b",
            runtime: { reasoning: { mode: "no_think" } },
          },
        ],
      },
    ];
    return {
      providers,
      getProviderById: (providerId: string | null | undefined) =>
        providers.find((provider) => provider.id === providerId) ?? null,
      getModelById: (modelId: string | null | undefined) =>
        providers
          .flatMap((provider) => provider.models)
          .find((model) => model.id === modelId) ?? null,
      findProviderForModel: (modelId: string | null | undefined) =>
        providers.find((provider) =>
          provider.models.some((model) => model.id === modelId)
        ) ?? null,
    };
  },
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

function createThreadConfig(overrides: Partial<ThreadConfig> = {}): ThreadConfig {
  return {
    providerId: "local",
    modelId: "qwen3.5:14b",
    inferenceMode: "auto",
    retrievalSource: "project",
    personaId: null,
    ...overrides,
  };
}

function buildActiveThread(id: string, title?: string): Thread {
  return {
    id,
    title: title ?? `Thread ${id}`,
    lastMessage: "",
    unread: 0,
    participants: [
      { id: "me", name: "tester" },
      { id: "bot", name: "Guardian" },
    ],
    messages: [],
    threadConfig: createThreadConfig(),
  };
}

function renderWithActiveThread(
  thread: Thread,
  overrides?: { onNewChat?: () => void }
) {
  const onNewChat = overrides?.onNewChat ?? vi.fn();

  function Harness() {
    return (
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={thread as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={onNewChat}
        sessionTabs={[
          {
            tabId: "tab-1" as any,
            threadId: thread.id,
            title: thread.title,
            providerId: "local",
            modelId: "qwen3.5:14b",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: "auto",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
        activeProviderId={"local"}
        activeModelId={"qwen3.5:14b"}
        activeInferenceMode={"auto"}
        onSessionProviderChange={vi.fn()}
        onSessionModelChange={vi.fn()}
        onSessionInferenceModeChange={vi.fn()}
      />
    );
  }

  const result = render(<Harness />);
  return { ...result, onNewChat };
}

describe("GuardianChat thread-created live-event bridge", () => {
  beforeEach(() => {
    liveEventHandlers.clear();
    vi.clearAllMocks();
  });

  it("triggers threads-refresh when thread.created event arrives from another client", async () => {
    const activeThread = buildActiveThread("77", "Thread 77");
    const onNewChat = vi.fn();
    renderWithActiveThread(activeThread, { onNewChat });

    // Capture the window event for cfy:threads:refresh
    let refreshEvent: CustomEvent | null = null;
    const onRefresh = (e: Event) => {
      refreshEvent = e as CustomEvent;
    };
    window.addEventListener("cfy:threads:refresh", onRefresh);

    // Verify the subscription was registered
    const handlers = liveEventHandlers.get("thread.created");
    expect(handlers).toBeDefined();
    expect(handlers?.size).toBe(1);

    // Simulate another client creating thread 99
    const handler = [...handlers!][0];
    handler({
      type: "thread.created",
      data: { thread_id: 99, title: "New Client Thread", user_id: "other", project_id: 42 },
    });

    // The threads-refresh window event should have been dispatched
    await waitFor(() => {
      expect(refreshEvent).not.toBeNull();
    });

    expect(refreshEvent?.detail).toMatchObject({
      kind: "create",
      id: 99,
      remote: true,
    });

    // Active thread must not be switched
    expect(onNewChat).not.toHaveBeenCalled();

    window.removeEventListener("cfy:threads:refresh", onRefresh);
  });

  it("does not auto-switch into the new thread created by another client", async () => {
    const activeThread = buildActiveThread("77", "Thread 77");
    const onNewChat = vi.fn();
    renderWithActiveThread(activeThread, { onNewChat });

    // The onNewChat callback must not be called before or after a remote event
    const handlers = liveEventHandlers.get("thread.created");
    expect(handlers).toBeDefined();

    const handler = [...handlers!][0];
    handler({
      type: "thread.created",
      data: { thread_id: 88, title: "Remote Thread" },
    });

    // Let any effects settle
    await waitFor(() => {
      // onNewChat is never called by the live-event bridge
    }, { timeout: 500 });

    expect(onNewChat).not.toHaveBeenCalled();
  });

  it("does not dispatch refresh for the event type when payload is missing a thread id", async () => {
    const activeThread = buildActiveThread("77");
    renderWithActiveThread(activeThread);

    let refreshCount = 0;
    const onRefresh = () => {
      refreshCount++;
    };
    window.addEventListener("cfy:threads:refresh", onRefresh);

    const handlers = liveEventHandlers.get("thread.created");
    expect(handlers).toBeDefined();

    const handler = [...handlers!][0];
    // Fire with data that has no thread_id
    handler({ type: "thread.created", data: { title: "no thread id" } });

    // No refresh should fire — guards kick in when thread_id is missing
    await waitFor(() => {}, { timeout: 200 });

    expect(refreshCount).toBe(0);

    window.removeEventListener("cfy:threads:refresh", onRefresh);
  });
});
