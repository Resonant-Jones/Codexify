import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import GuardianChat from "@/features/chat/GuardianChat";
import api from "@/lib/api";

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
  Composer: ({ modelOptions }: { modelOptions?: Array<{ label: string; description?: string }> }) => (
    <div data-testid="composer-stub">
      {(modelOptions ?? []).map((option, index) => (
        <div key={`${option.label}-${option.description ?? "none"}-${index}`}>
          <span>{option.label}</span>
          {option.description ? <span>{option.description}</span> : null}
        </div>
      ))}
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
    completionState: { isCompleting: false, activeThreadId: null },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
    updateCompletionTaskId: vi.fn(),
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
    expect(screen.getByText("Namespace library2")).toBeInTheDocument();
    expect(screen.getByText("Namespace archive")).toBeInTheDocument();
    expect(screen.queryByText("library2/qwen3:4b")).not.toBeInTheDocument();
    expect(screen.queryByText("archive/qwen3:4b")).not.toBeInTheDocument();
  });
});
