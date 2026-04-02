import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useState } from "react";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";
import type { ComposerInferenceMode } from "@/types/inference";
import type { Thread, ThreadConfig } from "@/types/ui";

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
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
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

vi.mock("@/features/chat/components", () => ({
  Composer: ({
    activeProviderId,
    activeModelId,
    activeInferenceMode,
    sourceMode,
    onProviderChange,
    onModelChange,
    onInferenceModeChange,
    onSourceModeChange,
  }: {
    activeProviderId?: string | null;
    activeModelId?: string;
    activeInferenceMode?: ComposerInferenceMode;
    sourceMode?: "project" | "personal_knowledge";
    onProviderChange?: (providerId: string) => void;
    onModelChange?: (modelId: string) => void;
    onInferenceModeChange?: (mode: ComposerInferenceMode) => void;
    onSourceModeChange?: (mode: "project" | "personal_knowledge") => void;
  }) => (
    <div data-testid="composer-stub">
      <div data-testid="provider-value">{String(activeProviderId ?? "none")}</div>
      <div data-testid="model-value">{String(activeModelId ?? "none")}</div>
      <div data-testid="mode-value">{String(activeInferenceMode ?? "default")}</div>
      <div data-testid="source-value">{String(sourceMode ?? "project")}</div>
      <button type="button" data-testid="set-provider-local" onClick={() => onProviderChange?.("local")}>
        Local provider
      </button>
      <button type="button" data-testid="set-provider-remote" onClick={() => onProviderChange?.("remote")}>
        Remote provider
      </button>
      <button type="button" data-testid="set-model-b" onClick={() => onModelChange?.("qwen3.5:0.8b")}>
        Model B
      </button>
      <button type="button" data-testid="set-think" onClick={() => onInferenceModeChange?.("think")}>
        Think
      </button>
      <button
        type="button"
        data-testid="set-personal-knowledge"
        onClick={() => onSourceModeChange?.("personal_knowledge")}
      >
        Personal knowledge
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
        models: [
          {
            id: "qwen3.5:14b",
            canonicalId: "qwen3.5:14b",
            runtime: { reasoning: { mode: "no_think" } },
          },
          {
            id: "qwen3.5:0.8b",
            canonicalId: "qwen3.5:0.8b",
            runtime: { reasoning: { mode: "no_think" } },
          },
        ],
      },
      {
        id: "remote",
        displayName: "Remote",
        enabled: true,
        authorized: true,
        available: true,
        models: [
          { id: "remote-model-a", canonicalId: "remote-model-a" },
          { id: "remote-model-b", canonicalId: "remote-model-b" },
        ],
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

function normalizeModeForUi(value: string): ComposerInferenceMode {
  return value === "think"
    ? "think"
    : value === "no_think" || value === "fast"
      ? "no_think"
      : "default";
}

function getComposerState() {
  return {
    provider: screen.getByTestId("provider-value").textContent,
    model: screen.getByTestId("model-value").textContent,
    mode: screen.getByTestId("mode-value").textContent,
    source: screen.getByTestId("source-value").textContent,
  };
}

function buildActiveThread(
  id: string,
  threadConfig?: ThreadConfig | null
): Thread {
  return {
    id,
    title: id === "draft" ? "Draft Thread" : `Thread ${id}`,
    lastMessage: "",
    unread: 0,
    participants: [
      { id: "me", name: "tester" },
      { id: "bot", name: "Guardian" },
    ],
    messages: [],
    threadConfig: threadConfig ?? null,
  };
}

function renderChatThread(options: {
  thread: Thread;
  initialProviderId?: string | null;
  initialModelId?: string;
  initialInferenceMode?: ComposerInferenceMode;
  sessionTabId?: string;
}): {
  rerenderWithThread: (thread: Thread) => void;
} {
  function Harness({
    thread,
    initialProviderId = "local",
    initialModelId = "qwen3.5:14b",
    initialInferenceMode = "default",
    sessionTabId = "tab-1",
  }: {
    thread: Thread;
    initialProviderId?: string | null;
    initialModelId?: string;
    initialInferenceMode?: ComposerInferenceMode;
    sessionTabId?: string;
  }) {
    const [activeProviderId, setActiveProviderId] = useState<string | null>(initialProviderId);
    const [activeModelId, setActiveModelId] = useState(initialModelId);
    const [activeInferenceMode, setActiveInferenceMode] =
      useState<ComposerInferenceMode>(initialInferenceMode);

    return (
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={thread as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: sessionTabId,
            threadId: thread.id,
            title: thread.title,
            providerId: activeProviderId ?? undefined,
            modelId: activeModelId,
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
            inferenceMode: activeInferenceMode,
          } as any,
        ]}
        activeSessionTabId={sessionTabId as any}
        activeProviderId={activeProviderId}
        activeModelId={activeModelId}
        activeInferenceMode={activeInferenceMode}
        onSessionProviderChange={setActiveProviderId}
        onSessionModelChange={setActiveModelId}
        onSessionInferenceModeChange={setActiveInferenceMode}
      />
    );
  }

  const result = render(<Harness thread={options.thread} />);

  return {
    rerenderWithThread: (thread: Thread) => result.rerender(<Harness thread={thread} />),
  };
}

describe("GuardianChat thread config selectors", () => {
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.clearAllMocks();
    liveEventHandlers.clear();
    window.localStorage.clear();

    apiMock.get.mockImplementation(async (url: string) => {
      if (url === "/llm/catalog") {
        return {
          data: {
            providers: [
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
                  {
                    id: "qwen3.5:0.8b",
                    canonicalId: "qwen3.5:0.8b",
                    runtime: { reasoning: { mode: "no_think" } },
                  },
                ],
              },
              {
                id: "remote",
                displayName: "Remote",
                enabled: true,
                authorized: true,
                available: true,
                models: [
                  { id: "remote-model-a", canonicalId: "remote-model-a" },
                  { id: "remote-model-b", canonicalId: "remote-model-b" },
                ],
              },
            ],
          },
        };
      }
      if (url === "/health/llm") {
        return {
          data: {
            ok: true,
            status: "online",
            provider: "local",
            model: "qwen3.5:14b",
            error: null,
          },
        };
      }
      if (url.endsWith("/profile")) {
        return {
          data: {
            profile: {
              id: "default",
              name: "Default",
              mode: "cloud",
            },
            profiles: [],
          },
        };
      }
      if (url === "/voice/capabilities") {
        return {
          data: {
            read_aloud_enabled: false,
            turn_based_enabled: false,
            supported_input_mime: ["audio/wav"],
            limits: null,
          },
        };
      }
      return { data: {} };
    });

    apiMock.post.mockResolvedValue({ data: {} });
    apiMock.patch.mockResolvedValue({ data: {} });
    apiMock.delete.mockResolvedValue({ data: {} });
  });

  it("hydrates an existing thread from persisted thread_config instead of ambient defaults", async () => {
    window.localStorage.setItem("cfy.chat.source.tab:tab-1", "personal_knowledge");
    window.localStorage.setItem("cfy.chat.source.thread:42", "personal_knowledge");

    const persisted = createThreadConfig({
      providerId: "local",
      modelId: "qwen3.5:14b",
      inferenceMode: "fast",
      retrievalSource: "project",
    });

    renderChatThread({
      thread: buildActiveThread("42", persisted),
      initialProviderId: "remote",
      initialModelId: "remote-model-a",
      initialInferenceMode: "default",
    });

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:14b",
        mode: normalizeModeForUi("fast"),
        source: "project",
      });
    });
  });

  it("persists provider changes through the thread-config API and applies the saved response", async () => {
    const user = userEvent.setup();
    const persisted = createThreadConfig({
      providerId: "local",
      modelId: "qwen3.5:14b",
      inferenceMode: "fast",
      retrievalSource: "project",
    });

    renderChatThread({
      thread: buildActiveThread("42", persisted),
      initialProviderId: "local",
      initialModelId: "qwen3.5:14b",
      initialInferenceMode: "default",
    });

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:14b",
        mode: "no_think",
        source: "project",
      });
    });

    let configState = persisted;
    apiMock.patch.mockImplementation(async (_url: string, patch: Partial<ThreadConfig>) => {
      configState = {
        ...configState,
        ...patch,
        personaId: configState.personaId ?? null,
      } as ThreadConfig;
      return {
        data: {
          thread_config: configState,
        },
      };
    });

    await user.click(screen.getByTestId("set-provider-remote"));

    await waitFor(() => {
      expect(apiMock.patch).toHaveBeenCalledWith(
        "/chat/threads/42/config",
        expect.objectContaining({
          providerId: "remote",
          modelId: "remote-model-a",
          inferenceMode: "fast",
          retrievalSource: "project",
        })
      );
      expect(getComposerState()).toEqual({
        provider: "remote",
        model: "remote-model-a",
        mode: "default",
        source: "project",
      });
    });
  });

  it("persists model, inference, and source changes through the thread-config API", async () => {
    const user = userEvent.setup();
    const persisted = createThreadConfig({
      providerId: "local",
      modelId: "qwen3.5:14b",
      inferenceMode: "fast",
      retrievalSource: "project",
    });

    renderChatThread({
      thread: buildActiveThread("42", persisted),
      initialProviderId: "local",
      initialModelId: "qwen3.5:14b",
      initialInferenceMode: "default",
    });

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:14b",
        mode: "no_think",
        source: "project",
      });
    });

    let configState = persisted;
    apiMock.patch.mockImplementation(async (_url: string, patch: Partial<ThreadConfig>) => {
      configState = {
        ...configState,
        ...patch,
        personaId: configState.personaId ?? null,
      } as ThreadConfig;
      return {
        data: {
          thread_config: configState,
        },
      };
    });

    await user.click(screen.getByTestId("set-model-b"));

    await waitFor(() => {
      expect(apiMock.patch).toHaveBeenCalledWith(
        "/chat/threads/42/config",
        expect.objectContaining({
          providerId: "local",
          modelId: "qwen3.5:0.8b",
          inferenceMode: "fast",
          retrievalSource: "project",
        })
      );
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:0.8b",
        mode: "no_think",
        source: "project",
      });
    });

    await user.click(screen.getByTestId("set-think"));

    await waitFor(() => {
      expect(apiMock.patch).toHaveBeenCalledWith(
        "/chat/threads/42/config",
        expect.objectContaining({
          providerId: "local",
          modelId: "qwen3.5:0.8b",
          inferenceMode: "think",
          retrievalSource: "project",
        })
      );
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:0.8b",
        mode: "think",
        source: "project",
      });
    });

    await user.click(screen.getByTestId("set-personal-knowledge"));

    await waitFor(() => {
      expect(apiMock.patch).toHaveBeenCalledWith(
        "/chat/threads/42/config",
        expect.objectContaining({
          providerId: "local",
          modelId: "qwen3.5:0.8b",
          inferenceMode: "think",
          retrievalSource: "personal_knowledge",
        })
      );
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:0.8b",
        mode: "think",
        source: "personal_knowledge",
      });
    });
  });

  it("keeps local preview state for a draft thread and reconciles when the persisted thread appears", async () => {
    const user = userEvent.setup();
    const draftThread = buildActiveThread("draft", null);
    const persisted = buildActiveThread(
      "42",
      createThreadConfig({
        providerId: "remote",
        modelId: "remote-model-b",
        inferenceMode: "fast",
        retrievalSource: "project",
      })
    );

    const { rerenderWithThread } = renderChatThread({
      thread: draftThread,
      initialProviderId: "local",
      initialModelId: "qwen3.5:14b",
      initialInferenceMode: "default",
    });

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:14b",
        mode: "default",
        source: "project",
      });
    });

    await user.click(screen.getByTestId("set-think"));
    await user.click(screen.getByTestId("set-personal-knowledge"));

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "local",
        model: "qwen3.5:14b",
        mode: "think",
        source: "personal_knowledge",
      });
    });
    expect(apiMock.patch).not.toHaveBeenCalled();

    rerenderWithThread(persisted);

    await waitFor(() => {
      expect(getComposerState()).toEqual({
        provider: "remote",
        model: "remote-model-b",
        mode: "default",
        source: "project",
      });
    });
  });
});
