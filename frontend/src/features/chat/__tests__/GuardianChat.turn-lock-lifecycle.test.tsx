import {
  act,
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

const liveEventsMock = vi.hoisted(() => {
  const handlers = new Map<
    string,
    Set<(event: { type: string; data: unknown }) => void>
  >();
  const subscribe = vi.fn(
    (
      eventType: string,
      handler: (event: { type: string; data: unknown }) => void
    ) => {
      const listeners = handlers.get(eventType) ?? new Set();
      listeners.add(handler);
      handlers.set(eventType, listeners);
      return () => {
        const existing = handlers.get(eventType);
        if (!existing) return;
        existing.delete(handler);
        if (existing.size === 0) {
          handlers.delete(eventType);
        }
      };
    }
  );
  return { handlers, subscribe };
});

const taskSources = vi.hoisted(() => ({
  instances: [] as (EventTarget & {
    url: string;
    close: ReturnType<typeof vi.fn>;
  })[],
}));

vi.mock("@/lib/guardianEventSource", () => {
  class GuardianEventSource extends EventTarget {
    static CLOSED = 2;
    readonly url: string;
    readyState = 1;
    onerror: ((event: Event) => void) | null = null;
    close = vi.fn(() => { this.readyState = 2; });
    constructor(url: string) {
      super();
      this.url = url;
      taskSources.instances.push(this);
    }
  }
  return { GuardianEventSource };
});

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
    realHook: false,
    onTaskCancelled: undefined as ((threadId: number, taskId: string) => void) | undefined,
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
  buildAuthenticatedFetchInit: (init: RequestInit = {}) => init,
  buildLlmCatalogPath: () => "/llm/catalog",
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getInFlightCompletionTurnId: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  hasRequestAuthCredential: vi.fn(() => true),
  updateThreadConfig: async (threadId: string | number, patch: Record<string, unknown>) => {
    const response = await apiSpies.patch(
      `/chat/threads/${threadId}/config`,
      patch
    );
    return response?.data ?? {};
  },
}));

vi.mock("@/lib/authState", () => ({
  useAuthState: () => ({
    ready: true,
    status: "authenticated",
    token: "test-token",
  }),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getRuntimeConfigHydrationState: () => "ready",
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
  default: ({ onCancelInference, onSwitchToFast, inferenceState }: {
    onCancelInference?: () => void;
    onSwitchToFast?: () => void;
    inferenceState?: { taskId?: string | null };
  }) => (
    <>
      <output data-testid="inference-task-id">{inferenceState?.taskId ?? ""}</output>
      <button type="button" data-testid="chat-cancel" onClick={() => onCancelInference?.()}>
        Cancel inference
      </button>
      <button type="button" data-testid="chat-fast" onClick={() => onSwitchToFast?.()}>
        Switch to fast
      </button>
    </>
  ),
}));

vi.mock("@/features/chat/components/GuardianThreadApprovalRail", () => ({
  default: () => <div data-testid="approval-rail-stub" />,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

vi.mock("@/features/chat/useChat", () => {
  const hookValue = {
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
  };
  return {
    default: () => hookValue,
  };
});

vi.mock("@/hooks/useLiveEvents", () => {
  const hookValue = {
    subscribe: liveEventsMock.subscribe,
  };
  return {
    useLiveEvents: () => hookValue,
  };
});

vi.mock("@/features/chat/hooks/useInferenceRequestState", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/features/chat/hooks/useInferenceRequestState")>();
  const hookValue = {
    state: inferenceMocks.state,
    startRequest: inferenceMocks.startRequest,
    attachTask: inferenceMocks.attachTask,
    markCompleted: inferenceMocks.markCompleted,
    markFailed: inferenceMocks.markFailed,
    markCancelled: inferenceMocks.markCancelled,
    requestCancel: inferenceMocks.requestCancel,
    reset: inferenceMocks.reset,
  };
  return {
    describeInferenceRequestState: (
      state: { phase?: string } | null | undefined
    ) => inferenceMocks.realHook && state
      ? actual.describeInferenceRequestState(state as any)
      : ({
        canonicalState: state?.phase ?? "idle",
        delayDetailText: null,
        isDelayed: false,
        timings: {},
      }),
    useInferenceRequestState: (options?: { onTaskCancelled?: (threadId: number, taskId: string) => void }) => {
      inferenceMocks.onTaskCancelled = options?.onTaskCancelled;
      return inferenceMocks.realHook ? actual.useInferenceRequestState(options) : hookValue;
    },
  };
});

vi.mock("@/features/chat/hooks/useLlmCatalog", () => ({
  isChatSelectableModel: (model: {
    supportsChat?: boolean;
    modelKind?: string;
  } | null | undefined) =>
    Boolean(
      model && model.supportsChat !== false && model.modelKind !== "utility"
    ),
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
  useLlmCatalog: (() => {
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
    const hookValue = {
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
    return () => hookValue;
  })(),
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
  const listeners = liveEventsMock.handlers.get(type);
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

  const onSendMessage = vi.fn().mockResolvedValue(undefined);
  const element = (
    <GuardianChat
      guardianName="Guardian"
      userName="tester"
      activeThread={{ id: "1", title: "Thread 1" } as any}
      onSendMessage={onSendMessage}
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

  const view = render(element);
  return {
    onSessionProviderChange,
    onSendMessage,
    unmount: view.unmount,
    rerenderChat: () => view.rerender(<GuardianChat {...element.props} />),
  };
}

describe("GuardianChat turn lock lifecycle", () => {
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    liveEventsMock.handlers.clear();
    taskSources.instances.length = 0;
    inferenceMocks.realHook = false;
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

  afterEach(() => {
    cleanup();
    expect(liveEventsMock.handlers.size).toBe(0);
    liveEventsMock.handlers.clear();
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
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
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
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
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

  const terminalEvents = [
    "task.completed",
    "task.failed",
    "task.cancelled",
    "completion.error",
  ];

  it.each(
    terminalEvents.flatMap((event) => [
      [event, 2, "foreign-task"],
      [event, 1, "stale-task"],
      [event, 2, "task-1"],
    ])
  )("ignores unrelated terminal %s from thread %s task %s", async (event, threadId, taskId) => {
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    emitLiveEvent(String(event), {
      thread_id: threadId,
      task_id: taskId,
      turn_id: "unrelated-turn",
      error: "Unrelated request failed",
    });

    expect(inferenceMocks.state.phase).toBe("streaming");
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    expect(chatMocks.endCompletion).not.toHaveBeenCalled();
    expect(chatMocks.finalizeCompletionSession).not.toHaveBeenCalled();
    expect(chatMocks.updateCompletionSessionTurnId).not.toHaveBeenCalled();
    expect(inferenceMocks.markCompleted).not.toHaveBeenCalled();
    expect(inferenceMocks.markFailed).not.toHaveBeenCalled();
    expect(inferenceMocks.markCancelled).not.toHaveBeenCalled();
  });

  it.each(
    terminalEvents.flatMap((event) => [[event, 1], [event, 2]])
  )("ignores prior completion %s while newer inference owns thread %s", async (event, threadId) => {
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    act(() => {
      inferenceMocks.startRequest({
        threadId: Number(threadId),
        providerId: "local",
        modelId: "local-model",
        mode: "default",
      });
      inferenceMocks.attachTask("newer-task");
    });
    emitLiveEvent(String(event), {
      thread_id: 1,
      task_id: "task-1",
      error: "Prior request failed",
    });

    expect(inferenceMocks.state.phase).toBe("streaming");
    expect(inferenceMocks.state.taskId).toBe("newer-task");
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    expect(chatMocks.finalizeCompletionSession).not.toHaveBeenCalled();
    expect(inferenceMocks.markCompleted).not.toHaveBeenCalled();
    expect(inferenceMocks.markFailed).not.toHaveBeenCalled();
    expect(inferenceMocks.markCancelled).not.toHaveBeenCalled();
  });

  it.each(terminalEvents)("accepts owned completion %s when inference is inactive", async (event) => {
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });
    act(() => { inferenceMocks.reset(); });
    emitLiveEvent(event, { thread_id: 1, task_id: "task-1" });
    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
    expect(chatMocks.finalizeCompletionSession).toHaveBeenCalledWith({
      taskId: "task-1",
      terminalState: event === "task.completed" ? "completed"
        : event === "task.cancelled" ? "cancelled"
          : event === "completion.error" ? "error" : "failed",
    });
  });

  it.each(terminalEvents)("accepts current task terminal %s", async (event) => {
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => {
      expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1");
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    });

    emitLiveEvent(event, {
      thread_id: 1,
      task_id: "task-1",
      error: "Current request failed",
    });

    await waitFor(() => {
      expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    });
    const expectedPhase =
      event === "task.completed"
        ? "completed"
        : event === "task.cancelled"
          ? "cancelled"
          : "failed";
    expect(inferenceMocks.state.phase).toBe(expectedPhase);
    expect(chatMocks.finalizeCompletionSession).toHaveBeenCalled();
  });

  function completeCalls() {
    return apiMock.post.mock.calls.filter(([url]) => url === "/chat/1/complete");
  }

  async function startThinkingTurn() {
    const view = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1"));
    inferenceMocks.state.mode = "think";
    return view;
  }

  async function allowRetryTimer() {
    await act(async () => { await new Promise((resolve) => window.setTimeout(resolve, 220)); });
  }

  it.each(["global", "stream"].flatMap((feed) => ["accepted", "pending", "late-failure"].map((post) => [feed, post] as const)))(
    "resumes one fast completion after owned %s cancellation with %s stop POST",
    async (feed, post) => {
      const view = await startThinkingTurn();
      let finishStop!: (accepted: boolean) => void;
      if (post !== "accepted") {
        inferenceMocks.requestCancel.mockReturnValueOnce(new Promise<boolean>((resolve) => { finishStop = resolve; }));
      }
      apiMock.post.mockImplementation(async (url: string) => (
        url === "/chat/1/complete" ? { data: { task_id: "task-fast" } } : { data: {} }
      ));
      fireEvent.click(screen.getByTestId("chat-fast"));
      await allowRetryTimer();
      expect(completeCalls()).toHaveLength(1);
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
      if (feed === "global") {
        emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
      } else {
        act(() => {
          inferenceMocks.onTaskCancelled?.(1, "task-1");
          inferenceMocks.markCancelled();
        });
        view.rerenderChat();
      }
      // Duplicate delivery from both observations must coalesce into one retry.
      emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
      act(() => inferenceMocks.onTaskCancelled?.(1, "task-1"));
      if (post === "late-failure") await act(async () => { finishStop(false); });
      await waitFor(() => expect(completeCalls()).toHaveLength(2));
      expect(completeCalls()[1][1]).toEqual(expect.objectContaining({
        provider: "local", model: "local-model", reasoning_mode: "no_think",
      }));
      expect(view.onSendMessage).toHaveBeenCalledOnce();
      expect(apiMock.post.mock.calls.some(([url]) => String(url).endsWith("/messages"))).toBe(false);
      expect(inferenceMocks.attachTask).toHaveBeenLastCalledWith("task-fast");
      expect(inferenceMocks.state.mode).toBe("no_think");
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
      if (post === "pending") await act(async () => { finishStop(true); });
      emitLiveEvent("task.completed", { thread_id: 1, task_id: "task-fast" });
      await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
      await allowRetryTimer();
      expect(completeCalls()).toHaveLength(2);
    }
  );

  it.each(["task.completed", "task.failed"])("does not fast-retry when %s wins the cancellation race", async (terminal) => {
    await startThinkingTurn();
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent(terminal, { thread_id: 1, task_id: "task-1", error: "Worker failure" });
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
    expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
  });

  it.each([{ thread_id: 1, task_id: "foreign-task" }, { thread_id: 2, task_id: "task-1" }])(
    "does not fast-retry after foreign cancellation %j", async (payload) => {
      await startThinkingTurn();
      fireEvent.click(screen.getByTestId("chat-fast"));
      emitLiveEvent("task.cancelled", payload);
      await allowRetryTimer();
      expect(completeCalls()).toHaveLength(1);
      expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    }
  );

  it("does not fast-retry when the stop POST fails before cancellation", async () => {
    await startThinkingTurn();
    inferenceMocks.requestCancel.mockResolvedValueOnce(false);
    fireEvent.click(screen.getByTestId("chat-fast"));
    await act(async () => { await Promise.resolve(); });
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it("invalidates scheduled fast retry when the user starts a newer turn", async () => {
    const view = await startThinkingTurn();
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(view.onSendMessage).toHaveBeenCalledTimes(2));
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(2);
    expect(completeCalls()[1][1].reasoning_mode).not.toBe("no_think");
  });

  it("keeps the existing bounded turn-lock backoff before admitting fast completion", async () => {
    await startThinkingTurn();
    let retries = 0;
    apiMock.post.mockImplementation(async (url: string) => {
      if (url !== "/chat/1/complete") return { data: {} };
      if (++retries === 1) throw Object.assign(new Error("Turn locked"), {
        response: { status: 429, data: { detail: "completion_turn_locked" } },
      });
      return { data: { task_id: "task-fast" } };
    });
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    await waitFor(() => expect(inferenceMocks.attachTask).toHaveBeenLastCalledWith("task-fast"), { timeout: 1800 });
    expect(completeCalls()).toHaveLength(3);
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
  });

  it("releases the synthetic lease after all four fast admissions remain locked", async () => {
    const view = await startThinkingTurn();
    apiMock.post.mockImplementation(async (url: string) => {
      if (url !== "/chat/1/complete") return { data: {} };
      throw Object.assign(new Error("Request failed with status code 429"), {
        response: { status: 429, data: { detail: { error: "turn_in_flight" } } },
      });
    });
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    await waitFor(() => expect(completeCalls()).toHaveLength(5), { timeout: 3000 });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(inferenceMocks.attachTask).toHaveBeenCalledTimes(1);
    expect(inferenceMocks.reset).toHaveBeenCalled();
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(5);
    expect(view.onSendMessage).toHaveBeenCalledOnce();
    apiMock.post.mockResolvedValue({ data: { task_id: "next-user-task" } });
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(view.onSendMessage).toHaveBeenCalledTimes(2));
    await waitFor(() => expect(inferenceMocks.attachTask).toHaveBeenLastCalledWith("next-user-task"));
  });

  it.each(["stop", "provider"])("a later %s supersedes a scheduled fast handoff", async (action) => {
    await startThinkingTurn();
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    fireEvent.click(screen.getByTestId(action === "stop" ? "chat-cancel" : "composer-provider-switch"));
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it("does not fast-retry from a legacy cancellation without task identity", async () => {
    await startThinkingTurn();
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1 });
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it("invalidates a scheduled fast handoff when the component unmounts", async () => {
    const view = await startThinkingTurn();
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    view.unmount();
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it("projects failed fast admission without another authored turn", async () => {
    const view = await startThinkingTurn();
    apiMock.post.mockImplementation(async (url: string) => {
      if (url === "/chat/1/complete") throw Object.assign(new Error("Queue unavailable"), {
        response: { status: 503, data: { detail: "queue_unavailable" } },
      });
      return { data: {} };
    });
    fireEvent.click(screen.getByTestId("chat-fast"));
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    await waitFor(() => expect(completeCalls()).toHaveLength(2));
    expect(inferenceMocks.state.phase).toBe("failed");
    expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked");
    expect(view.onSendMessage).toHaveBeenCalledOnce();
  });

  it.each(["accepted", "late-failure"])("uses the actual hook for stream cancellation and %s stop POST", async (post) => {
    inferenceMocks.realHook = true;
    const view = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-1"));
    expect(taskSources.instances).toHaveLength(1);
    let finishStop!: (response: unknown) => void;
    let rejectStop!: (error: Error) => void;
    apiMock.post.mockImplementation((url: string) => {
      if (url === "/chat/1/complete") return Promise.resolve({ data: { task_id: "task-fast" } });
      if (url === "/api/tasks/task-1/cancel") {
        return new Promise((resolve, reject) => { finishStop = resolve; rejectStop = reject; });
      }
      return Promise.resolve({ data: {} });
    });
    fireEvent.click(screen.getByTestId("chat-fast"));
    await waitFor(() => expect(apiMock.post).toHaveBeenCalledWith("/api/tasks/task-1/cancel"));
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
    const original = taskSources.instances[0];
    act(() => original.dispatchEvent(new MessageEvent("task.cancelled", {
      data: JSON.stringify({ thread_id: 1, task_id: "task-1" }),
    })));
    if (post === "late-failure") await act(async () => { rejectStop(new Error("Late stop error")); });
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-fast"));
    expect(taskSources.instances).toHaveLength(2);
    expect(original.close).toHaveBeenCalledOnce();
    expect(completeCalls()).toHaveLength(2);
    expect(completeCalls()[1][1]).toEqual(expect.objectContaining({ reasoning_mode: "no_think" }));
    expect(view.onSendMessage).toHaveBeenCalledOnce();
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    if (post === "accepted") await act(async () => { finishStop({ data: { cancel_requested: true } }); });
    const current = taskSources.instances[1];
    expect(current.close).not.toHaveBeenCalled();
    act(() => current.dispatchEvent(new MessageEvent("task.completed", {
      data: JSON.stringify({ thread_id: 1, task_id: "task-fast", message_id: 100 }),
    })));
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(current.close).toHaveBeenCalledOnce();
  });

  it("recovers the active orphan from a durable receipt without SSE and permits only an explicit new send", async () => {
    inferenceMocks.realHook = true;
    let accepted = 0;
    const orphan = {
      task_id: "task-1", request_id: "request-1", thread_id: 1, turn_id: "turn-1",
      completed_message_id: null, state: "terminal", event_type: "task.failed",
      reason: "durable_terminal_outcome_recorded", failure_code: "CHAT_ACCEPTED_TASK_ORPHANED",
    };
    apiMock.get.mockImplementation(async (url: string) => url === "/chat/threads/1/tasks"
      ? { data: { ok: true, thread_id: 1, tasks: accepted ? [orphan] : [], has_more: false } }
      : { data: {} });
    apiMock.post.mockImplementation(async (url: string) => url === "/chat/1/complete"
      ? { data: { task_id: `task-${++accepted}` } } : { data: {} });
    const view = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    await waitFor(() => expect(screen.getByTestId("chat-message-region")).toHaveAttribute("data-inference-state", "failed_retryable"));
    expect(taskSources.instances).toHaveLength(1);
    expect(taskSources.instances[0].close).toHaveBeenCalledOnce();
    expect(chatMocks.refreshSnapshot).toHaveBeenCalled();
    expect(completeCalls()).toHaveLength(1);
    expect(view.onSendMessage).toHaveBeenCalledOnce();
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-2"));
    await act(async () => { await Promise.resolve(); });
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    expect(taskSources.instances).toHaveLength(2);
    expect(taskSources.instances[1].close).not.toHaveBeenCalled();
    expect(completeCalls()).toHaveLength(2);
    expect(view.onSendMessage).toHaveBeenCalledTimes(2);
    act(() => taskSources.instances[1].dispatchEvent(new MessageEvent("task.completed", {
      data: JSON.stringify({ thread_id: 1, task_id: "task-2", message_id: 100 }),
    })));
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(taskSources.instances[1].close).toHaveBeenCalledOnce();
  });

  it.each(["task.completed", "task.cancelled"])("projects durable receipt %s without a terminal stream event", async (eventType) => {
    inferenceMocks.realHook = true;
    let accepted = false;
    apiMock.get.mockImplementation(async (url: string) => url === "/chat/threads/1/tasks"
      ? { data: { ok: true, thread_id: 1, tasks: accepted ? [{
          task_id: "task-1", request_id: "request-1", thread_id: 1, turn_id: "turn-1",
          completed_message_id: eventType === "task.completed" ? 100 : null,
          state: "terminal", event_type: eventType, reason: "durable_terminal_outcome_recorded", failure_code: null,
        }] : [], has_more: false } } : { data: {} });
    apiMock.post.mockImplementation(async (url: string) => {
      if (url === "/chat/1/complete") { accepted = true; return { data: { task_id: "task-1" } }; }
      return { data: {} };
    });
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(taskSources.instances).toHaveLength(1));
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(taskSources.instances[0].close).toHaveBeenCalledOnce();
    expect(screen.getByTestId("chat-message-region")).toHaveAttribute("data-inference-state", eventType === "task.completed" ? "completed" : "cancelled");
    expect(completeCalls()).toHaveLength(1);
  });

  it("projects a global canonical orphan distinctly without automatically retrying", async () => {
    inferenceMocks.realHook = true;
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-1"));
    emitLiveEvent("task.failed", { thread_id: 1, task_id: "task-1", failure_code: "CHAT_ACCEPTED_TASK_ORPHANED" });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(screen.getByTestId("chat-message-region")).toHaveAttribute("data-inference-state", "failed_retryable");
    expect(completeCalls()).toHaveLength(1);
    expect(taskSources.instances[0].close).toHaveBeenCalledOnce();
  });

  it.each(["task.failed", "completion.error"].flatMap((type) =>
    ["tool_command_failed", "tool_command_blocked"].map((reason) => [type, reason])
  ))("projects owned global command failure %s: %s through the actual hook", async (type, reason) => {
    inferenceMocks.realHook = true;
    const view = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-1"));
    emitLiveEvent(type, {
      thread_id: 1, task_id: "task-1", toolTurnState: "failed",
      loopStopReason: reason, error: reason,
      completed_at: "2026-04-05T00:00:01.000Z",
    });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(screen.getByTestId("chat-message-region")).toHaveAttribute("data-inference-state", "failed");
    expect(taskSources.instances[0].close).toHaveBeenCalledOnce();
    expect(view.onSendMessage).toHaveBeenCalledOnce();
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it.each(["task.failed", "completion.error"])("projects owned global deadline %s through the actual hook", async (type) => {
    inferenceMocks.realHook = true;
    const view = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(screen.getByTestId("inference-task-id")).toHaveTextContent("task-1"));
    emitLiveEvent(type, {
      thread_id: 1, task_id: "task-1",
      failure_code: "CHAT_ACCEPTED_TASK_DEADLINE_EXCEEDED",
      error: "Accepted chat task work deadline exceeded.",
      provider_request_started: false, first_output_observed: false,
      completed_at: "2026-04-05T00:00:01.000Z",
    });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(screen.getByTestId("chat-message-region")).toHaveAttribute("data-inference-state", "failed_retryable");
    expect(taskSources.instances[0].close).toHaveBeenCalledOnce();
    expect(view.onSendMessage).toHaveBeenCalledOnce();
    await allowRetryTimer();
    expect(completeCalls()).toHaveLength(1);
  });

  it.each(
    ["stop", "provider"].flatMap((action) =>
      [true, false].flatMap((accepted) =>
        ["task.completed", "task.cancelled", "task.failed"].map((terminal) => [action, accepted, terminal] as const)
      )
    )
  )("keeps ownership after %s POST acceptance %s until %s", async (action, accepted, terminal) => {
    const { onSessionProviderChange } = renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1"));
    const resetsBefore = inferenceMocks.reset.mock.calls.length;
    const endsBefore = chatMocks.endCompletion.mock.calls.length;
    inferenceMocks.requestCancel.mockResolvedValueOnce(accepted);
    fireEvent.click(screen.getByTestId(action === "stop" ? "chat-cancel" : "composer-provider-switch"));
    await waitFor(() => expect(inferenceMocks.requestCancel).toHaveBeenCalledOnce());
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    expect(inferenceMocks.reset).toHaveBeenCalledTimes(resetsBefore);
    expect(chatMocks.endCompletion).toHaveBeenCalledTimes(endsBefore);
    expect(inferenceMocks.state.taskId).toBe("task-1");
    expect(inferenceMocks.state.phase).toBe("streaming");
    if (action === "provider") expect(onSessionProviderChange).toHaveBeenCalledWith("remote");
    fireEvent.click(screen.getByTestId("composer-send"));
    expect(chatMocks.startCompletion).toHaveBeenCalledOnce();
    emitLiveEvent(terminal, { thread_id: 1, task_id: "task-1", error: "Actual task failure" });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    expect(inferenceMocks.state.phase).toBe(
      terminal === "task.completed" ? "completed" : terminal === "task.cancelled" ? "cancelled" : "failed"
    );
  });

  it.each(["stop", "provider"])("keeps the lease while %s POST is still pending", async (action) => {
    renderChat();
    await screen.findByTestId("composer-stub");
    fireEvent.click(screen.getByTestId("composer-send"));
    await waitFor(() => expect(inferenceMocks.attachTask).toHaveBeenCalledWith("task-1"));
    let resolveCancel!: (accepted: boolean) => void;
    inferenceMocks.requestCancel.mockReturnValueOnce(new Promise<boolean>((resolve) => { resolveCancel = resolve; }));
    const resetsBefore = inferenceMocks.reset.mock.calls.length;
    fireEvent.click(screen.getByTestId(action === "stop" ? "chat-cancel" : "composer-provider-switch"));
    expect(screen.getByTestId("lock-state")).toHaveTextContent("locked");
    expect(inferenceMocks.reset).toHaveBeenCalledTimes(resetsBefore);
    emitLiveEvent("task.cancelled", { thread_id: 1, task_id: "task-1" });
    await waitFor(() => expect(screen.getByTestId("lock-state")).toHaveTextContent("unlocked"));
    await act(async () => { resolveCancel(false); });
    expect(inferenceMocks.state.phase).toBe("cancelled");
  });
});
