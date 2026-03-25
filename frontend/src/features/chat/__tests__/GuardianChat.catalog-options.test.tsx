import { render, screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

function countGetCalls(url: string): number {
  return (api.get as any).mock.calls.filter((call: [string]) => call[0] === url).length;
}

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
  Composer: ({
    providerOptions,
    modelOptions,
  }: {
    providerOptions?: Array<{ label: string; description?: string; disabled?: boolean }>;
    modelOptions?: Array<{ label: string; description?: string }>;
  }) => (
    <div data-testid="composer-stub">
      <div data-testid="provider-options">
        {(providerOptions ?? []).map((option, index) => (
          <div key={`${option.label}-${option.description ?? "none"}-${index}`}>
            <span>{option.label}</span>
            {option.description ? <span>{option.description}</span> : null}
            {option.disabled ? <span>disabled</span> : null}
          </div>
        ))}
      </div>
      <div data-testid="model-options">
      {(modelOptions ?? []).map((option, index) => (
        <div key={`${option.label}-${option.description ?? "none"}-${index}`}>
          <span>{option.label}</span>
          {option.description ? <span>{option.description}</span> : null}
        </div>
      ))}
      </div>
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
    refreshSnapshot: vi.fn(),
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

describe("GuardianChat catalog-backed model options", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockImplementation(async (url: string) => {
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
                source: {
                  kind: "local",
                  baseUrl: "http://127.0.0.1:11434/v1",
                  label: "127.0.0.1:11434",
                },
                models: [
                  {
                    id: "library2/qwen3:4b",
                    canonical_id: "library2/qwen3:4b",
                    display_label: "Qwen 3 4B · library2",
                    alias: null,
                    namespace: "library2",
                    source: "library2",
                    runtime: {
                      reasoning: {
                        mode: "no_think",
                        instruction: "/no_think",
                        profile_reason: "pattern-matched local qwen profile",
                      },
                    },
                  },
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
            model: "library2/qwen3:4b",
            error: null,
          },
        };
      }
      return { data: {} };
    });
  });

  it("renders normalized model labels and keeps reasoning diagnostics out of picker copy", async () => {
    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "draft", title: "Draft" } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            title: "Tab 1",
            providerId: "local",
            modelId: "library2/qwen3:4b",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    expect(await screen.findByText("Qwen 3 4B · library2")).toBeInTheDocument();
    expect(screen.queryByText("library2/qwen3:4b")).not.toBeInTheDocument();
    expect(
      screen.queryByText("pattern-matched local qwen profile")
    ).not.toBeInTheDocument();
  });

  it("adds muted differentiators only when normalized model labels collide", async () => {
    (api.get as any).mockImplementation(async (url: string) => {
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
                source: {
                  kind: "local",
                  baseUrl: "http://127.0.0.1:11434/v1",
                  label: "127.0.0.1:11434",
                },
                models: [
                  {
                    id: "library2/qwen3:4b",
                    canonical_id: "library2/qwen3:4b",
                    display_label: "Qwen 3 4B",
                    namespace: "library2",
                    source: "library2",
                  },
                  {
                    id: "archive/qwen3:4b",
                    canonical_id: "archive/qwen3:4b",
                    display_label: "Qwen 3 4B",
                    namespace: "archive",
                    source: "archive",
                  },
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
            model: "library2/qwen3:4b",
            error: null,
          },
        };
      }
      return { data: {} };
    });

    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "draft", title: "Draft" } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            title: "Tab 1",
            providerId: "local",
            modelId: "library2/qwen3:4b",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    expect((await screen.findAllByText("Qwen 3 4B")).length).toBeGreaterThanOrEqual(2);
    expect(
      screen.getByText("Namespace library2 · Text-only chat")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Namespace archive · Text-only chat")
    ).toBeInTheDocument();
    expect(screen.queryByText("library2/qwen3:4b")).not.toBeInTheDocument();
    expect(screen.queryByText("archive/qwen3:4b")).not.toBeInTheDocument();
  });

  it("filters utility models while labeling vision-capable and text-only chat models", async () => {
    (api.get as any).mockImplementation(async (url: string) => {
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
                source: {
                  kind: "local",
                  baseUrl: "http://127.0.0.1:11434/v1",
                  label: "127.0.0.1:11434",
                },
                models: [
                  {
                    id: "text-chat",
                    canonical_id: "text-chat",
                    display_label: "Text Chat",
                    supports_chat: true,
                    supports_vision: false,
                    supports_text_input: true,
                    model_kind: "chat",
                  },
                  {
                    id: "vision-chat",
                    canonical_id: "vision-chat",
                    display_label: "Vision Chat",
                    supports_chat: true,
                    supports_vision: true,
                    supports_text_input: true,
                    model_kind: "vision_chat",
                  },
                  {
                    id: "text-embedding-3-small",
                    canonical_id: "text-embedding-3-small",
                    display_label: "Embedding",
                    supports_chat: false,
                    supports_vision: false,
                    supports_text_input: true,
                    model_kind: "utility",
                  },
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
            model: "text-chat",
            error: null,
          },
        };
      }
      return { data: {} };
    });

    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "draft", title: "Draft" } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            title: "Tab 1",
            providerId: "local",
            modelId: "text-chat",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    expect(await screen.findByText("Text Chat")).toBeInTheDocument();
    expect(screen.getByText("Text-only chat")).toBeInTheDocument();
    expect(screen.getByText("Vision-capable chat")).toBeInTheDocument();
    expect(screen.queryByText("Embedding")).not.toBeInTheDocument();
    expect(screen.getByText("2 chat models · Source 127.0.0.1:11434")).toBeInTheDocument();
  });

  it("fetches catalog, health, and profile data once on mount", async () => {
    (api.get as any).mockImplementation(async (url: string) => {
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
                source: {
                  kind: "local",
                  baseUrl: "http://127.0.0.1:11434/v1",
                  label: "127.0.0.1:11434",
                },
                models: [{ id: "library2/qwen3:4b", displayName: "Qwen 3 4B · library2" }],
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
            model: "library2/qwen3:4b",
            error: null,
          },
        };
      }
      if (url === "/chat/123/profile") {
        return {
          data: {
            profile: {
              id: "default",
              name: "Default",
              mode: "cloud",
            },
            profiles: [
              {
                id: "default",
                name: "Default",
                mode: "cloud",
              },
            ],
          },
        };
      }
      return { data: {} };
    });

    render(
      <GuardianChat
        guardianName="Guardian"
        userName="tester"
        activeThread={{ id: "123", title: "Persisted" } as any}
        onSendMessage={vi.fn().mockResolvedValue(undefined)}
        onNewChat={vi.fn()}
        sessionTabs={[
          {
            tabId: "tab-1",
            title: "Tab 1",
            providerId: "local",
            modelId: "library2/qwen3:4b",
            createdAt: "2026-03-06T00:00:00.000Z",
            updatedAt: "2026-03-06T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await waitFor(() => expect(api.get).toHaveBeenCalledWith("/chat/123/profile"));

    expect(countGetCalls("/llm/catalog")).toBe(1);
    expect(countGetCalls("/health/llm")).toBe(1);
    expect(countGetCalls("/chat/123/profile")).toBe(1);
  });
});
