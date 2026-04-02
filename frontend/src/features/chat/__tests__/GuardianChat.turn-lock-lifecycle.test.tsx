import { act, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

const liveEventHandlers = vi.hoisted(
  () => new Map<string, Set<(event: { type: string; data: unknown }) => void>>()
);

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

const chatMocks = vi.hoisted(() => {
  const completionInFlight = new Set<number>();
  const completionState = {
    isCompleting: false,
    activeTaskId: null as string | null,
    activeThreadId: null as number | null,
    startedAt: null as number | null,
  };

  const resetState = () => {
    completionInFlight.clear();
    completionState.isCompleting = false;
    completionState.activeTaskId = null;
    completionState.activeThreadId = null;
    completionState.startedAt = null;
  };

  return {
    completionState,
    activateThread: vi.fn().mockResolvedValue([]),
    refreshSnapshot: vi.fn().mockResolvedValue([]),
    loadOlderMessages: vi.fn().mockResolvedValue([]),
    startCompletion: vi.fn((threadId: number, taskId: string) => {
      completionInFlight.add(threadId);
      completionState.isCompleting = true;
      completionState.activeTaskId = taskId;
      completionState.activeThreadId = threadId;
      completionState.startedAt = Date.now();
    }),
    endCompletion: vi.fn(() => {
      if (completionState.activeThreadId != null) {
        completionInFlight.delete(completionState.activeThreadId);
      }
      completionState.isCompleting = false;
      completionState.activeTaskId = null;
      completionState.activeThreadId = null;
      completionState.startedAt = null;
    }),
    updateCompletionTaskId: vi.fn((taskId: string | null) => {
      completionState.activeTaskId = taskId;
    }),
    startCompletionSession: vi.fn(),
    reassociateCompletionSession: vi.fn(() => true),
    updateCompletionSessionTurnId: vi.fn(() => true),
    finalizeCompletionSession: vi.fn(({ taskId }: { taskId: string }) => {
      if (!taskId) return false;
      if (
        completionState.activeTaskId &&
        taskId !== completionState.activeTaskId
      ) {
        return false;
      }
      if (completionState.activeThreadId != null) {
        completionInFlight.delete(completionState.activeThreadId);
      }
      completionState.isCompleting = false;
      completionState.activeTaskId = null;
      completionState.activeThreadId = null;
      completionState.startedAt = null;
      return true;
    }),
    handleIncomingAssistantMessage: vi.fn(() => false),
    isCompletionInFlight: vi.fn((threadId: number | null | undefined) =>
      threadId != null ? completionInFlight.has(threadId) : false
    ),
    setCompletionInFlight: vi.fn((threadId: number, value: boolean) => {
      if (!Number.isFinite(threadId)) return;
      if (value) {
        completionInFlight.add(threadId);
      } else {
        completionInFlight.delete(threadId);
        if (completionState.activeThreadId === threadId) {
          completionState.isCompleting = false;
          completionState.activeTaskId = null;
          completionState.activeThreadId = null;
          completionState.startedAt = null;
        }
      }
    }),
    resetState,
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

  const reset = vi.fn(() => {
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
  });

  return {
    state,
    requestCancel: vi.fn(async () => true),
    reset,
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
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  updateThreadConfig: async (threadId: string | number, patch: Record<string, unknown>) => {
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

vi.mock("@/features/chat/components", () => ({
  Composer: ({
    isTurnInFlight,
    onSend,
    onProviderChange,
  }: {
    isTurnInFlight?: boolean;
    onSend: (text: string) => Promise<void>;
    onProviderChange?: (providerId: string) => void;
  }) => (
    <div data-testid="composer-stub">
      <div data-testid="lock-state">
        {isTurnInFlight ? "locked" : "unlocked"}
      </div>
      <button type="button" data-testid="composer-send" onClick={() => void onSend("hello")}>
        Send
      </button>
      <button
        type="button"
        data-testid="composer-provider-switch"
        onClick={() => onProviderChange?.("remote")}
      >
        Switch provider
      </button>
    </div>
  ),
}));

vi.mock("@/features/chat/ChatView", () => ({
  default: ({ onCancelInference }: { onCancelInference?: () => void }) => (
    <button type="button" data-testid="chat-cancel" onClick={() => onCancelInference?.()}>
      Cancel inference
    </button>
  ),
}));

vi.mock("@/features/chat/components/GuardianThreadApprovalRail", () => ({
  default: () => <div data-testid="approval-rail-stub" />,
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
    subscribe: (eventType: string, handler: (event: { type: string; data: unknown }) => void) => {
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
  isChatSelectableModel: (model: {
    supportsChat?: boolean;
    modelKind?: string;
  } | null | undefined) => Boolean(model && model.supportsChat !== false && model.modelKind !== "utility"),
  describeModelCapability: (model: {
    supportsVision?: boolean;
    supportsChat?: boolean;
    modelKind?: string;
  } | null | undefined) =>
    !model || model.supportsChat === false || model.modelKind === "utility"
      ? "Utility model"
      : model.supportsVision
        ? "Vision-capable chat"
        : "Text-only chat",
  useLlmCatalog: () => {
    const providers = [
      {
        id: "local",
        displayName: "Local",
        enabled: true,
        authorized: true,
        available: true,
        models: [{ id: "local-model", canonicalId: "local-model" }],
      },
      {
        id: "remote",
        displayName: "Remote",
        enabled: true,
        authorized: true,
        available: true,
        models: [{ id: "remote-model", canonicalId: "remote-model" }],
      },
    ];
    return {
      providers,
      getProviderById: (providerId: string | null | undefined) =>
        providers.find((provider) => provider.id === providerId) ?? null,
      getModelById: (modelId: string | null | undefined) =>
        providers.flatMap((provider) => provider.models).find((model) => model.id === modelId) ??
        null,
      findProviderForModel: (modelId: string | null | undefined) =>
        providers.find((provider) =>
          provider.models.some(
            (model) => model.id === modelId && model.modelKind !== "utility"
          )
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

function emitLiveEvent(type: string, data: Record<string, unknown>) {
  const listeners = liveEventHandlers.get(type);
  if (!listeners) return;
  act(() => {
    for (const handler of listeners) {
      handler({ type, data });
    }
  });
}

function renderChat(overrides: {
  onSessionProviderChange?: (providerId: string | null) => void;
} = {}) {
  const onSessionProviderChange =
    overrides.onSessionProviderChange ?? vi.fn();

  render(
    <GuardianChat
      guardianName="Guardian"
      userName="tester"
      activeThread={{ id: "1", title: "Thread 1" } as any}
      onSendMessage={vi.fn().mockResolvedValue(undefined)}
      onNewChat={vi.fn()}
      sessionTabs={[
        {
          tabId: "tab-1",
          threadId: "1",
          title: "Thread 1",
          providerId: "local",
          modelId: "local-model",
          createdAt: "2026-03-06T00:00:00.000Z",
          updatedAt: "2026-03-06T00:00:00.000Z",
          inferenceMode: "default",
        } as any,
      ]}
      activeSessionTabId={"tab-1" as any}
      activeProviderId="local"
      activeModelId="local-model"
      onSessionProviderChange={onSessionProviderChange}
      onSessionModelChange={vi.fn()}
    />
  );

  return { onSessionProviderChange };
}

describe("GuardianChat turn lock lifecycle", () => {
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    liveEventHandlers.clear();
    chatMocks.resetState();
    inferenceMocks.reset();
    inferenceMocks.requestCancel.mockResolvedValue(true);
    apiMock.get.mockResolvedValue({ data: {} });
    apiMock.post.mockImplementation(async (url: string) => {
      if (url === "/chat/1/complete") {
        return { data: { task_id: "task-1" } };
      }
      if (url === "/api/tasks/task-1/cancel") {
        return { data: { ok: true } };
      }
      return { data: {} };
    });
  });

  it("clears the lock when completion start fails with backend error", async () => {
    apiMock.post.mockImplementation(async (url: string) => {
      if (url === "/chat/1/complete") {
        const error: any = new Error("boom");
        error.response = { status: 500, data: { detail: "boom" } };
        throw error;
      }
      return { data: {} };
    });

    renderChat();
    await screen.findByTestId("composer-stub");

    expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    fireEvent.click(screen.getByTestId("composer-send"));

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
  });

  it("clears the lock on successful terminal events even without turn_id and stays idempotent", async () => {
    renderChat();
    await screen.findByTestId("composer-stub");

    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    emitLiveEvent("task.completed", {
      thread_id: 1,
      task_id: "task-1",
    });

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });

    emitLiveEvent("task.completed", {
      thread_id: 1,
      task_id: "task-1",
    });

    expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
  });

  it("clears the lock on completion.error when task_id is missing but active thread matches", async () => {
    renderChat();
    await screen.findByTestId("composer-stub");

    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    emitLiveEvent("completion.error", {
      thread_id: 1,
      error: "stream dropped",
    });

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
  });

  it("cancelling inference releases lock and clears request-scoped state", async () => {
    renderChat();
    await screen.findByTestId("composer-stub");

    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    inferenceMocks.requestCancel.mockResolvedValueOnce(false);
    fireEvent.click(screen.getByTestId("chat-cancel"));

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
    expect(inferenceMocks.requestCancel).toHaveBeenCalled();
    expect(inferenceMocks.reset).toHaveBeenCalled();
  });

  it("provider switch during active request unwinds lock and keeps composer usable", async () => {
    const { onSessionProviderChange } = renderChat();
    await screen.findByTestId("composer-stub");

    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    fireEvent.click(screen.getByTestId("composer-provider-switch"));

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
    expect(inferenceMocks.requestCancel).toHaveBeenCalled();
    expect(inferenceMocks.reset).toHaveBeenCalled();
    expect(onSessionProviderChange).toHaveBeenCalledWith("remote");
  });
});
