import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

const apiSpies = vi.hoisted(() => ({
  get: vi.fn(),
  post: vi.fn(),
  patch: vi.fn(),
  delete: vi.fn(),
}));

const eventSources = vi.hoisted(() => ({
  instances: [] as MockGuardianEventSource[],
}));
const chatState = vi.hoisted(() => ({
  messages: [] as any[],
  loading: false,
  error: null as string | null,
  hasMore: false,
}));
const composerState = vi.hoisted(() => ({
  slashIntent: null as
    | {
        commandId: string;
        rawToken: string;
        queryText: string;
        intentKind: string;
        retrievalHint: string;
        rawInput: string;
      }
    | null,
}));

type MockGuardianEventSource = EventTarget & {
  url: string;
  options: Record<string, unknown>;
  readyState: number;
  onopen: ((event: Event) => void) | null;
  onmessage: ((event: MessageEvent<string>) => void) | null;
  onerror: ((event: Event) => void) | null;
  close: ReturnType<typeof vi.fn>;
  emit: (type: string, data: Record<string, unknown>) => void;
  emitError: () => void;
};

vi.mock("@/lib/api", () => ({
  default: apiSpies,
  buildChatCompletePath: (threadId: string | number) => `/chat/${threadId}/complete`,
  clearInFlightCompletionTurnId: vi.fn(),
  getAuthToken: vi.fn(() => null),
  getBackendOutageRemainingMs: vi.fn(() => 0),
  getDevApiKey: vi.fn(() => null),
  getInFlightCompletionTurnId: vi.fn(() => null),
  readRuntimeApiKey: vi.fn(() => null),
  invokeCommandBus: async (payload: Record<string, unknown>) => {
    const response = await apiSpies.post(
      "/api/guardian/commands/invoke",
      payload,
      {
        headers: {
          "X-User-Id": String((payload as any)?.actor?.id ?? ""),
        },
      }
    );
    return response?.data ?? {};
  },
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

vi.mock("@/lib/guardianEventSource", () => {
  class MockGuardianEventSource extends EventTarget {
    static readonly CONNECTING = 0;
    static readonly OPEN = 1;
    static readonly CLOSED = 2;

    readonly url: string;
    readonly options: Record<string, unknown>;
    readyState = MockGuardianEventSource.OPEN;
    onopen: ((event: Event) => void) | null = null;
    onmessage: ((event: MessageEvent<string>) => void) | null = null;
    onerror: ((event: Event) => void) | null = null;
    close = vi.fn(() => {
      this.readyState = MockGuardianEventSource.CLOSED;
    });

    constructor(url: string, options: Record<string, unknown> = {}) {
      super();
      this.url = url;
      this.options = options;
      eventSources.instances.push(this as unknown as MockGuardianEventSource);
    }

    emit(type: string, data: Record<string, unknown>): void {
      const event = new MessageEvent(type, {
        data: JSON.stringify(data),
      });
      this.dispatchEvent(event);
      if (type === "message") {
        this.onmessage?.(event);
      }
    }

    emitError(): void {
      const event = new Event("error");
      this.onerror?.(event);
    }
  }

  return { GuardianEventSource: MockGuardianEventSource };
});

vi.mock("@/hooks/useLiveEvents", () => ({
  useLiveEvents: () => ({
    subscribe: () => () => {},
  }),
}));

vi.mock("@/features/chat/useChat", () => ({
  default: () => ({
    messages: chatState.messages,
    loading: chatState.loading,
    error: chatState.error,
    hasMore: chatState.hasMore,
    activateThread: vi.fn().mockResolvedValue([]),
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
    reassociateCompletionSession: vi.fn(),
    updateCompletionSessionTurnId: vi.fn(),
    finalizeCompletionSession: vi.fn(),
    handleIncomingAssistantMessage: vi.fn(() => false),
    isCompletionInFlight: vi.fn(() => false),
    setCompletionInFlight: vi.fn(),
    streamingDraft: null,
  }),
}));

vi.mock("@/features/chat/hooks/useLlmCatalog", () => {
  const providers = [
    {
      id: "local",
      displayName: "Local",
      enabled: true,
      authorized: true,
      available: true,
      models: [
        {
          id: "local-model",
          canonicalId: "local-model",
          modelKind: "chat",
          supportsChat: true,
        },
      ],
    },
  ];

  return {
    describeModelCapability: () => "Chat model",
    isChatSelectableModel: (model: { supportsChat?: boolean; modelKind?: string } | null | undefined) =>
      Boolean(model && model.supportsChat !== false && model.modelKind !== "utility"),
    useLlmCatalog: () => ({
      providers,
      getProviderById: (providerId: string | null | undefined) =>
        providers.find((provider) => provider.id === providerId) ?? null,
      getModelById: (modelId: string | null | undefined) =>
        providers.flatMap((provider) => provider.models).find((model) => model.id === modelId) ?? null,
      findProviderForModel: (modelId: string | null | undefined) =>
        providers.find((provider) =>
          provider.models.some((model) => model.id === modelId)
        ) ?? null,
    }),
  };
});

vi.mock("@/lib/devFlags", () => ({
  isRagTraceUIEnabled: () => false,
}));

vi.mock("@/state/contextTrace", () => ({
  setTrace: vi.fn(),
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

vi.mock("@/lib/runtimeRouteCapabilities", () => ({
  markRuntimeRouteUnavailableIfNotFound: vi.fn(() => false),
  useRuntimeRouteCapability: () => ({
    ready: true,
    state: "available",
    mounted: [],
    declared: {},
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
    onProviderChange,
  }: {
    onSend: (text: string, options?: { slashIntent?: Record<string, unknown> }) => Promise<void>;
    onProviderChange?: (providerId: string) => void;
  }) => (
    <div data-testid="composer-stub">
      <button
        type="button"
        data-testid="composer-send"
        onClick={() =>
          void onSend(
            "hello",
            composerState.slashIntent
              ? { slashIntent: composerState.slashIntent }
              : undefined
          )
        }
      >
        Send
      </button>
      <button
        type="button"
        data-testid="composer-provider-switch"
        onClick={() => onProviderChange?.("local")}
      >
        Switch provider
      </button>
    </div>
  ),
}));

vi.mock("@/features/chat/components/GuardianThreadApprovalRail", () => ({
  default: () => <div data-testid="approval-rail-stub" />,
}));

vi.mock("@/features/chat/components/PromptCostIndicator", () => ({
  default: () => <div data-testid="prompt-cost-indicator" />,
}));

vi.mock("@/components/SessionRail/SessionRail", () => ({
  default: () => <div data-testid="session-rail-stub" />,
}));

vi.mock("@/features/chat/panels/RAGTracePanel", () => ({
  default: () => <div data-testid="rag-trace-panel-stub" />,
}));

vi.mock("@/components/surface/FrameCard", () => ({
  default: ({ children }: any) => <div>{children}</div>,
}));

function buildThread(threadId: string) {
  return {
    id: threadId,
    title: `Thread ${threadId}`,
  } as any;
}

function buildSessionTabs(threadId: string) {
  return [
    {
      tabId: "tab-1",
      threadId,
      title: `Thread ${threadId}`,
      providerId: "local",
      modelId: "local-model",
      createdAt: "2026-03-06T00:00:00.000Z",
      updatedAt: "2026-03-06T00:00:00.000Z",
      inferenceMode: "default",
    } as any,
  ];
}

function buildUserMessage(id: number, content: string) {
  return {
    id,
    role: "user",
    content,
    created_at: "2026-04-05T00:00:00.000Z",
  } as any;
}

function renderChat(
  threadId = "1",
  overrides: {
    guardianName?: string;
    userName?: string;
    userProfession?: string;
  } = {}
) {
  const onSendMessage = vi.fn().mockResolvedValue(undefined);
  const utils = render(
    <GuardianChat
      guardianName={overrides.guardianName ?? "Guardian"}
      userName={overrides.userName ?? "tester"}
      userProfession={overrides.userProfession ?? ""}
      activeThread={buildThread(threadId)}
      onSendMessage={onSendMessage}
      onNewChat={vi.fn()}
      sessionTabs={buildSessionTabs(threadId)}
      activeSessionTabId={"tab-1" as any}
      activeProviderId="local"
      activeModelId="local-model"
    />
  );

  return {
    ...utils,
    onSendMessage,
  };
}

async function advanceTimers(ms: number) {
  await act(async () => {
    vi.advanceTimersByTime(ms);
    await Promise.resolve();
  });
}

function emitTaskEvent(
  source: MockGuardianEventSource,
  type: string,
  data: Record<string, unknown>
) {
  act(() => {
    source.emit(type, data);
  });
}

describe("GuardianChat inference rail", () => {
  const apiMock = api as unknown as {
    get: ReturnType<typeof vi.fn>;
    post: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
    delete: ReturnType<typeof vi.fn>;
  };

  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date("2026-04-05T00:00:00.000Z"));
    vi.clearAllMocks();
    composerState.slashIntent = null;
    chatState.messages = [];
    chatState.loading = false;
    chatState.error = null;
    chatState.hasMore = false;
    eventSources.instances.length = 0;
    Object.defineProperty(HTMLElement.prototype, "scrollIntoView", {
      configurable: true,
      value: vi.fn(),
    });
    apiMock.get.mockImplementation(async (url: string) => {
      if (url === "/voice/capabilities") {
        return {
          data: {
            read_aloud_enabled: true,
            turn_based_enabled: true,
            supported_input_mime: ["audio/wav"],
            limits: {
              max_upload_bytes: 1024,
              max_duration_s: 10,
            },
          },
        };
      }
      if (url === "/health/llm") {
        return {
          data: {
            ok: true,
            status: "online",
            provider: "local",
            model: "local-model",
          },
        };
      }
      if (/^\/chat\/\d+\/profile$/.test(url)) {
        return {
          data: {
            profile: {
              id: "default",
              name: "Default",
              mode: "cloud",
            },
            profiles: [
              { id: "default", name: "Default", mode: "cloud" },
              { id: "local_mode", name: "Local Mode", mode: "local" },
            ],
          },
        };
      }
      return { data: {} };
    });
    apiMock.post.mockImplementation(async (url: string) => {
      if (url === "/chat/1/complete") {
        return { data: { task_id: "task-1" } };
      }
      return { data: {} };
    });
    apiMock.patch.mockResolvedValue({ data: {} });
    apiMock.delete.mockResolvedValue({ data: {} });
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  async function startTrackedRequest() {
    fireEvent.click(screen.getByTestId("composer-send"));
    await screen.findByText("Queued…");
    await advanceTimers(100);
    expect(eventSources.instances).toHaveLength(1);
    return eventSources.instances[0];
  }

  it("keeps the rail visible while delayed and clears it at terminal proof", async () => {
    renderChat("1");
    const source = await startTrackedRequest();

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
    });
    await screen.findByText("Warming model…");

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_FIRST_TOKEN",
      awaiting_first_token_at: "2026-04-05T00:00:02.000Z",
    });
    await screen.findByText("Waiting for first token…");

    await advanceTimers(15_001);
    await waitFor(() => {
      expect(screen.getByTestId("chat-message-region")).toHaveAttribute(
        "data-inference-delayed",
        "true"
      );
      expect(screen.getByTestId("chat-message-region")).toHaveAttribute(
        "data-inference-state",
        "awaiting_first_token"
      );
      expect(
        screen.getByText(/still waiting for the first token/i)
      ).toBeInTheDocument();
    });

    emitTaskEvent(source, "task.completed", {
      thread_id: 1,
      task_id: "task-1",
      message_id: 77,
    });

    await waitFor(() => {
      expect(screen.queryByTestId("chat-completing-indicator")).not.toBeInTheDocument();
    });
  });

  it("renders a degraded transport state instead of a frozen failure", async () => {
    renderChat("1");
    const source = await startTrackedRequest();

    emitTaskEvent(source, "task.state", {
      thread_id: 1,
      task_id: "task-1",
      state: "AWAITING_MODEL",
    });
    await screen.findByText("Warming model…");

    act(() => {
      source.emitError();
    });

    expect(screen.getByTestId("chat-message-region")).toHaveAttribute(
      "data-inference-state",
      "degraded"
    );
    expect(screen.getByText("Provider degraded…")).toBeInTheDocument();
    expect(
      screen.getByText(/still waiting for a terminal task event/i)
    ).toBeInTheDocument();
    expect(screen.queryByText("Reply failed")).not.toBeInTheDocument();
  });

  it("keeps the sidebar summon and dismissal affordance explicit", () => {
    const onSidebarToggle = vi.fn();
    const commonProps = {
      guardianName: "Guardian",
      userName: "tester",
      activeThread: buildThread("1"),
      onSendMessage: vi.fn().mockResolvedValue(undefined),
      onNewChat: vi.fn(),
      sessionTabs: buildSessionTabs("1"),
      activeSessionTabId: "tab-1" as any,
      activeProviderId: "local",
      activeModelId: "local-model",
      onSidebarToggle,
      isSidebarVisible: true,
    };

    const { rerender } = render(<GuardianChat {...commonProps} />);

    expect(
      screen.getByRole("button", { name: "Hide sidebar" })
    ).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Hide sidebar" }));
    expect(onSidebarToggle).toHaveBeenCalled();

    rerender(<GuardianChat {...commonProps} isSidebarVisible={false} />);

    expect(
      screen.getByRole("button", { name: "Show sidebar" })
    ).toBeInTheDocument();
  });

  it("attaches slashIntent to the completion request payload", async () => {
    composerState.slashIntent = {
      commandId: "project",
      rawToken: "/repo",
      queryText: "scope planning",
      intentKind: "workspace",
      retrievalHint: "project",
      rawInput: "/repo scope planning",
    };

    renderChat("1");
    await startTrackedRequest();

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalledWith(
        "/chat/1/complete",
        expect.objectContaining({
          slashIntent: expect.objectContaining({
            commandId: "project",
            rawInput: "/repo scope planning",
            intentKind: "workspace",
            retrievalHint: "project",
          }),
        })
      );
    });
  });

  it("attaches identity fields to the completion request payload when configured", async () => {
    renderChat("1", {
      guardianName: "Aurelia",
      userName: "Harbor",
      userProfession: "Engineer",
    });
    await startTrackedRequest();

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalledWith(
        "/chat/1/complete",
        expect.objectContaining({
          preferred_name: "Harbor",
          profession: "Engineer",
          guardian_name: "Aurelia",
        })
      );
    });
  });

  it("switches profiles through the command bus invoke surface instead of the legacy tools shim", async () => {
    const promptSpy = vi.spyOn(window, "prompt").mockReturnValue("local_mode");
    renderChat("1");

    apiMock.post.mockImplementation(async (url: string, body?: any) => {
      if (url === "/api/guardian/commands/invoke") {
        expect(body).toEqual(
          expect.objectContaining({
            invoke_version: "1.0",
            command_id: "op::guardian.profile.switch",
            actor: { kind: "human", id: "local" },
            arguments: expect.objectContaining({
              path_params: { thread_id: 1 },
              body: { profile_id: "local_mode" },
            }),
          })
        );
        return {
          data: {
            run_id: "run-profile-switch-1",
            status: "completed",
            inline_result: {
              ok: true,
              thread_id: 1,
              active_profile_id: "local_mode",
              provider_override: "local",
              model_override: "local-model",
            },
          },
        };
      }
      if (url === "/chat/1/profile") {
        return {
          data: {
            ok: true,
            thread_id: 1,
            profile: {
              profile_id: "local_mode",
              active_profile_id: "local_mode",
              provider_override: "local",
              model_override: "local-model",
            },
            profiles: [],
          },
        };
      }
      return { data: {} };
    });

    await act(async () => {
      fireEvent.click(screen.getByText("Switch profile…"));
    });

    await waitFor(() => {
      expect(apiMock.post).toHaveBeenCalledWith(
        "/api/guardian/commands/invoke",
        expect.objectContaining({
          command_id: "op::guardian.profile.switch",
        }),
        expect.objectContaining({
          headers: { "X-User-Id": "local" },
        })
      );
    });
    expect(
      apiMock.post.mock.calls.some(([url]) => url === "/tools/execute")
    ).toBe(false);
    promptSpy.mockRestore();
  });

  it("collapses oversized user messages by default and keeps the chat scroll container intact", async () => {
    const collapsedCode = Array.from({ length: 24 }, (_, index) => `const line${index} = ${index};`).join(
      "\n"
    );
    chatState.messages = [buildUserMessage(91, collapsedCode)];

    renderChat("1");

    const message = screen.getByTestId("chat-message");
    const content = within(message).getByTestId("guardian-user-message-content");

    expect(within(message).getByRole("button", { name: "See more" })).toBeInTheDocument();
    expect(content).toHaveStyle({ maxHeight: "224px", overflowY: "hidden" });
    expect(screen.getByTestId("chat-container")).toHaveClass("overflow-y-auto");
  });

  it("shows the expansion affordance only after the oversized threshold and expands the selected message locally", async () => {
    const shortMessage = buildUserMessage(92, "Short note.\nStill short.");
    const oversizedMessage = buildUserMessage(
      93,
      Array.from({ length: 22 }, (_, index) => `const entry${index} = "${index}";`).join("\n")
    );
    chatState.messages = [shortMessage, oversizedMessage];

    renderChat("1");

    const messageCards = screen.getAllByTestId("chat-message");
    const shortCard = messageCards[0];
    const longCard = messageCards[1];
    const longContent = within(longCard).getByTestId("guardian-user-message-content");

    expect(within(shortCard).queryByRole("button", { name: "See more" })).not.toBeInTheDocument();
    expect(within(longCard).getByRole("button", { name: "See more" })).toBeInTheDocument();
    expect(longContent).toHaveStyle({ maxHeight: "224px", overflowY: "hidden" });

    await act(async () => {
      fireEvent.click(within(longCard).getByRole("button", { name: "See more" }));
    });

    expect(within(longCard).getByRole("button", { name: "Show less" })).toBeInTheDocument();
    expect(longContent).toHaveStyle({ maxHeight: "360px", overflowY: "auto" });
    expect(within(shortCard).queryByRole("button", { name: "Show less" })).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-container")).toHaveClass("overflow-y-auto");
  });
});
