import { fireEvent, render, screen } from "@testing-library/react";
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
    completionState: { isCompleting: false, activeThreadId: null },
    startCompletion: vi.fn(),
    endCompletion: vi.fn(),
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
  default: ({
    providerMenuOpenSignal,
    providerPickerOpenSignal,
  }: {
    providerMenuOpenSignal?: number;
    providerPickerOpenSignal?: number;
  }) => (
    <div data-testid="provider-open-signal">
      {String(providerPickerOpenSignal ?? providerMenuOpenSignal ?? 0)}
    </div>
  ),
}));

vi.mock("@/imprint/api", () => ({
  fetchSystemPromptSummary: vi.fn().mockResolvedValue(null),
}));

describe("GuardianChat offline provider reroute", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    (api.get as any).mockImplementation(async (url: string) => {
      if (url === "/health/llm") {
        return {
          data: {
            ok: false,
            status: "offline",
            provider: "local",
            model: "llama3",
            error: "ConnectTimeout",
          },
        };
      }
      return { data: {} };
    });
  });

  it("renders Switch provider in offline banner and triggers provider selector open signal", async () => {
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
            modelId: "default",
            createdAt: "2026-02-16T00:00:00.000Z",
            updatedAt: "2026-02-16T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    await screen.findByText("LLM backend offline");
    const switchButton = screen.getByRole("button", { name: "Switch provider" });
    expect(switchButton).toBeInTheDocument();
    expect(screen.getByTestId("provider-open-signal")).toHaveTextContent("0");

    fireEvent.click(switchButton);
    expect(screen.getByTestId("provider-open-signal")).toHaveTextContent("1");
  });

  it("opens provider controls from the lightning popover provider section", async () => {
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
            modelId: "default",
            createdAt: "2026-02-16T00:00:00.000Z",
            updatedAt: "2026-02-16T00:00:00.000Z",
          } as any,
        ]}
        activeSessionTabId={"tab-1" as any}
      />
    );

    const promptCostTrigger = await screen.findByTestId(
      "prompt-cost-trigger"
    );
    expect(screen.getByTestId("provider-open-signal")).toHaveTextContent("0");

    fireEvent.click(promptCostTrigger);
    expect(screen.getByTestId("prompt-cost-popover")).toBeInTheDocument();

    const providersTab = screen.getByRole("button", { name: "Providers" });
    fireEvent.click(providersTab);
    expect(
      screen.getByTestId("prompt-cost-providers-panel")
    ).toBeInTheDocument();

    const openProvider = screen.getByRole("button", {
      name: "Open provider picker",
    });
    fireEvent.click(openProvider);
    expect(screen.getByTestId("provider-open-signal")).toHaveTextContent("1");
  });
});
