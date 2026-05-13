import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import CommandCenterShell from "../CommandCenterShell";
import type {
  CommandCenterRetrievalPosture,
  CommandCenterRetrievalPostureHistoryItem,
  CommandCenterRun,
  CommandCenterTraceFilters,
} from "@/features/commandCenter/types";
import { COMMAND_CENTER_RUN_STATUSES, COMMAND_CENTER_RUN_TERMINAL_OUTCOMES } from "@/features/commandCenter/types";
import type { CommandCenterHealthItem } from "@/features/commandCenter/types";
import type { CommandCenterEvent } from "@/features/commandCenter/types";
import { COMMAND_CENTER_HEALTH_STATES } from "@/features/commandCenter/types";
import type {
  PinnedRetrievalPostureState,
  RetrievalPostureHistoryFilter,
  RetrievalPostureHistoryWindowSize,
} from "../TraceWorkbench";

function makeEvent(
  overrides: Partial<CommandCenterEvent> & {
    eventId: string;
    raw: string;
    receivedAt: number;
    summary: string;
  }
): CommandCenterEvent {
  return {
    attemptedModel: null,
    attemptedProvider: null,
    completedAt: null,
    durationMs: null,
    eventId: overrides.eventId,
    fallbackReason: null,
    fallbackTriggered: null,
    finalModel: null,
    finalProvider: null,
    firstOutputAt: null,
    firstTokenAt: null,
    graphCount: null,
    json: overrides.json ?? {},
    kind: overrides.kind ?? null,
    latestTurnContent: null,
    memoryCount: null,
    persistenceOutcome: null,
    queuedAt: null,
    raw: overrides.raw,
    receivedAt: overrides.receivedAt,
    requestId: overrides.requestId ?? null,
    runId: overrides.runId ?? null,
    runKind: overrides.runKind ?? null,
    selectionSource: null,
    sourceMode: overrides.sourceMode ?? null,
    retrievalDepth: overrides.retrievalDepth ?? null,
    retrievalIntent: overrides.retrievalIntent ?? null,
    retrievalQuery: overrides.retrievalQuery ?? null,
    retrievalQueryMatchesLatestTurn: overrides.retrievalQueryMatchesLatestTurn ?? null,
    retrievalTarget: overrides.retrievalTarget ?? null,
    sseType: overrides.sseType ?? "message",
    state: overrides.state ?? null,
    status: overrides.status ?? null,
    summary: overrides.summary,
    taskId: overrides.taskId ?? null,
    taskType: overrides.taskType ?? null,
    terminalOutcome: overrides.terminalOutcome ?? null,
    threadId: overrides.threadId ?? null,
    turnId: overrides.turnId ?? null,
    type: overrides.type ?? null,
    warmupAt: null,
    ...overrides,
  } as CommandCenterEvent;
}

const mockedEvents: CommandCenterEvent[] = [
  makeEvent({
    eventId: "evt-1",
    json: { thread_id: 42, type: "chat.completion" },
    kind: null,
    raw: '{"thread_id":42,"type":"chat.completion"}',
    receivedAt: Date.parse("2026-04-01T15:58:00Z"),
    runId: "run-alpha",
    sseType: "task.created",
    state: "created",
    status: null,
    summary: "chat completion created",
    taskId: "task-alpha",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    turnId: "turn-alpha",
    type: "task.created",
  }),
  makeEvent({
    eventId: "evt-2",
    json: { thread_id: 42 },
    kind: null,
    raw: '{"thread_id":42}',
    receivedAt: Date.parse("2026-04-01T15:58:30Z"),
    runId: "run-alpha",
    sseType: "task.completed",
    state: "completed",
    status: null,
    summary: "chat completion completed",
    taskId: "task-alpha",
    taskType: "chat.completion",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 42,
    turnId: "turn-alpha",
    type: "task.completed",
  }),
];

const mockedRuns: CommandCenterRun[] = [
  {
    eventCount: 2,
    identityKind: "task",
    key: "task-alpha",
    lastEvent: mockedEvents[1],
    lastEventAt: Date.parse("2026-04-01T15:58:30Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-alpha",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-alpha",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 42,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-alpha",
  },
];

const mockedHealthItems: CommandCenterHealthItem[] = [
  {
    checkedAt: Date.parse("2026-04-01T15:59:00Z"),
    endpoint: "/health",
    error: null,
    httpStatus: 200,
    key: "core",
    label: "Core",
    raw: '{"ok":true}',
    status: COMMAND_CENTER_HEALTH_STATES.OK,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:01Z"),
    endpoint: "/health/llm",
    error: null,
    httpStatus: 200,
    key: "llm",
    label: "LLM",
    raw: '{"status":"degraded"}',
    status: COMMAND_CENTER_HEALTH_STATES.DEGRADED,
  },
];

const defaultProps = {
  connectionDetail: "Listening to /api/events",
  connectionState: "open",
  consoleRows: [
    { key: "row-1", raw: '{"type":"test"}', receivedAt: Date.now(), summary: "Test event" },
  ],
  healthItems: mockedHealthItems,
  lastCheckedAt: Date.now(),
  lastEventAt: Date.now(),
  loading: false,
  onRefresh: vi.fn(),
  onPinCurrentRetrievalPosture: vi.fn(),
  onPinHistoryRetrievalPosture: vi.fn(),
  pinnedRetrievalPosture: null as PinnedRetrievalPostureState,
  retrievalPostureHistoryFilter: "all" as RetrievalPostureHistoryFilter,
  retrievalPostureHistoryWindowSize: 5 as RetrievalPostureHistoryWindowSize,
  onClearPinnedPosture: vi.fn(),
  onHistoryFilterChange: vi.fn(),
  onHistoryWindowSizeChange: vi.fn(),
  onSelectRun: vi.fn(),
  onFiltersChange: vi.fn(),
  runs: mockedRuns,
  selectedRun: null,
  selectedRunKey: null,
  traceFilters: {
    model: "",
    provider: "",
    retrieval: "",
    status: "all",
    threadId: "",
    warningsOnly: false,
  } as CommandCenterTraceFilters,
  visibleRuns: mockedRuns,
  activeThreadId: 42,
};

// Mock the hooks used by CodingWorkOrdersPanel
const { mockFetchLatestRetrievalPosture, mockFetchRetrievalPostureHistory } = vi.hoisted(() => ({
  mockFetchLatestRetrievalPosture: vi.fn(),
  mockFetchRetrievalPostureHistory: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
  fetchLatestRetrievalPosture: mockFetchLatestRetrievalPosture,
  fetchRetrievalPostureHistory: mockFetchRetrievalPostureHistory,
}));

import api from "@/lib/api";
const apiGetMock = vi.mocked(api.get);
const apiPostMock = vi.mocked(api.post);

function configureApiMocks() {
  apiGetMock.mockImplementation(async (url: string) => {
    if (url === "/api/coding/work-orders") {
      return {
        data: {
          count: 0,
          items: [],
          limit: 50,
          offset: 0,
          ok: true,
        },
      };
    }
    if (url === "/api/coding/orchestrator/next") {
      return {
        data: {
          campaign_id: null,
          decision_reasons: [],
          generated_at: "2026-05-10T08:00:00+00:00",
          limit: 5,
          ok: true,
          recommendations: [],
          skipped: [],
        },
      };
    }
    throw new Error(`Unexpected GET ${url}`);
  });
  apiPostMock.mockResolvedValue({ data: { ok: true } });
  mockFetchLatestRetrievalPosture.mockResolvedValue(null);
  mockFetchRetrievalPostureHistory.mockResolvedValue({ items: [], status: "empty" });
}

describe("CommandCenterShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    configureApiMocks();
  });

  it("renders the parent shell card", () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.getByTestId("command-center-workspace-card")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-shell")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-scroll-shell")).toBeInTheDocument();
  });

  it("uses viewport-locked scroll containment", () => {
    render(<CommandCenterShell {...defaultProps} />);
    const scrollShell = screen.getByTestId("command-center-scroll-shell");
    expect(scrollShell).toHaveClass("h-screen");
    expect(scrollShell).toHaveClass("overflow-hidden");
    const lensZone = screen.getByTestId("command-center-lens-zone");
    expect(lensZone).toBeInTheDocument();
  });

  it("renders the utility rail", () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.getByTestId("command-center-utility-rail-container")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-utility-rail")).toBeInTheDocument();
  });

  it("renders the bottom drawer", () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.getByTestId("command-center-bottom-drawer")).toBeInTheDocument();
  });

  it("Agent Command lens is the default active lens", async () => {
    render(<CommandCenterShell {...defaultProps} />);
    const agentBtn = screen.getByTestId("command-center-rail-item-agent-command");
    expect(agentBtn).toHaveAttribute("aria-current", "true");
  });

  it("Worker Control panel is visible in the Agent Command lens", async () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.getByTestId("command-center-agent-lens-header")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-agent-lens-title")).toHaveTextContent(
      "Agent Command Center"
    );
    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coding-work-order-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-worker-control-card")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-work-order-summary-cards")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Dispatch, lease allocation, merge automation, and worker launch are not enabled/i
      )
    ).toBeInTheDocument();
  });

  it("no dispatch button exists", async () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.queryByRole("button", { name: /dispatch/i })).not.toBeInTheDocument();
  });

  it("switching to Observability lens shows trace content", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));
    expect(screen.getByTestId("command-center-rail-item-observability")).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.queryByTestId("coding-work-orders-panel")).not.toBeInTheDocument();
  });

  it("switching to Runtime Health lens shows health content", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-runtime-health"));
    expect(screen.getByTestId("command-center-rail-item-runtime-health")).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.getByText("Core")).toBeInTheDocument();
    expect(screen.getByText("LLM")).toBeInTheDocument();
  });

  it("switching to Event Console lens shows event console content", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-event-console"));
    expect(screen.getByTestId("command-center-rail-item-event-console")).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.getByText("Event console")).toBeInTheDocument();
  });

  it("Deep Settings lens displays placeholder copy", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-deep-settings"));
    expect(screen.getByTestId("command-center-rail-item-deep-settings")).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.getByText("Deep Settings")).toBeInTheDocument();
    expect(
      screen.getByText(/Configuration surfaces for full-app, plugin, and MCP settings/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/No backend configuration behavior is implemented through this panel/)
    ).toBeInTheDocument();
  });

  it("Extensions lens displays placeholder copy", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-extensions"));
    expect(screen.getByTestId("command-center-rail-item-extensions")).toHaveAttribute(
      "aria-current",
      "true"
    );
    expect(screen.getByText("Extensions")).toBeInTheDocument();
    expect(
      screen.getByText(/Plugin and overlay runtime is governed by the Self-Extending Agent/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/This lens is a future\/governed placeholder/)
    ).toBeInTheDocument();
  });

  it("bottom drawer opens when toggled from rail", () => {
    render(<CommandCenterShell {...defaultProps} />);
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("44px");
    expect(screen.getByTestId("command-center-drawer-collapsed-affordance")).toBeInTheDocument();

    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    expect(drawer.style.height).toBe("280px");
  });

  it("bottom drawer can be closed", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    fireEvent.click(screen.getByTestId("command-center-drawer-close"));
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("44px");
  });

  it("Terminal tab in drawer is non-executable", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    expect(
      screen.getByText(/Terminal execution is not enabled in this Command Center build/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/input disabled — terminal is non-executable/)
    ).toBeInTheDocument();
  });

  it("lens switching does not mutate worker state", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));
    fireEvent.click(screen.getByTestId("command-center-rail-item-agent-command"));
    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
  });

  it("rail side toggle switches layout from left to right", () => {
    localStorage.setItem("codexify-command-center-rail-side", "left");
    render(<CommandCenterShell {...defaultProps} />);

    const shell = screen.getByTestId("command-center-shell");
    // Initially, no flex-row-reverse — rail is on left (default)
    expect(shell.className).not.toContain("flex-row-reverse");

    // Click side toggle in the rail
    const sideBtn = screen.getByTestId("command-center-rail-side-toggle");
    fireEvent.click(sideBtn);

    // Shell should now have flex-row-reverse — rail moved to right
    expect(shell.className).toContain("flex-row-reverse");

    // localStorage should be updated
    expect(localStorage.getItem("codexify-command-center-rail-side")).toBe("right");
  });

  it("rail side preference persists across remount", () => {
    localStorage.setItem("codexify-command-center-rail-side", "right");
    const { unmount } = render(<CommandCenterShell {...defaultProps} />);

    const shell = screen.getByTestId("command-center-shell");
    expect(shell.className).toContain("flex-row-reverse");

    unmount();
    render(<CommandCenterShell {...defaultProps} />);

    const shellAfterRemount = screen.getByTestId("command-center-shell");
    expect(shellAfterRemount.className).toContain("flex-row-reverse");
  });

  it("Observability lens has scrollable lens region", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));

    const lensZone = screen.getByTestId("command-center-lens-zone");
    expect(lensZone).toBeInTheDocument();
    expect(lensZone.className).toContain("overflow-y-auto");
  });

  it("Runtime Health lens has scrollable lens region", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-runtime-health"));

    const lensZone = screen.getByTestId("command-center-lens-zone");
    expect(lensZone).toBeInTheDocument();
    expect(lensZone.className).toContain("overflow-y-auto");
  });

  it("Event Console lens has scrollable lens region", () => {
    render(<CommandCenterShell {...defaultProps} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-event-console"));

    const lensZone = screen.getByTestId("command-center-lens-zone");
    expect(lensZone).toBeInTheDocument();
    expect(lensZone.className).toContain("overflow-y-auto");
  });
});
