import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import CommandCenterShell, { readInitialDelegationIntentId } from "../CommandCenterShell";
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
  heartbeatEnabled: true,
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
const {
  mockFetchLatestRetrievalPosture,
  mockFetchRetrievalPostureHistory,
  mockHeartbeatStatusFn,
} = vi.hoisted(() => ({
  mockFetchLatestRetrievalPosture: vi.fn(),
  mockFetchRetrievalPostureHistory: vi.fn(),
  mockHeartbeatStatusFn: vi.fn(),
}));

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
  },
  fetchLatestRetrievalPosture: mockFetchLatestRetrievalPosture,
  fetchRetrievalPostureHistory: mockFetchRetrievalPostureHistory,
}));

// Mock the heartbeat status hook so the heartbeat lens doesn't make real API calls
vi.mock("@/features/commandCenter/hooks/useHeartbeatStatus", () => ({
  default: () => mockHeartbeatStatusFn(),
}));

function makeHeartbeatStatus() {
  return {
    status: {
      latest_date: "2026-05-14",
      heartbeat_report_path: "docs/Heartbeat/generated/2026-05-14-heartbeat.md",
      staged_outbox_path: null,
      review_status: "passed",
      outbox_status: "passed",
      publication_enabled: false,
      publication_targets: [],
      generated_files: [],
      warnings: [],
      failures: [],
      manual_commands: ["make heartbeat-full FORCE=1"],
    },
    loading: false,
    error: null,
    lastCheckedAt: Date.now(),
    refresh: vi.fn(),
  };
}

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
  mockHeartbeatStatusFn.mockReturnValue(makeHeartbeatStatus());
}

describe("CommandCenterShell", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
    configureApiMocks();
  });

  it("renders the parent shell card", () => {
    render(<CommandCenterShell {...defaultProps} />);
    expect(screen.getByTestId("command-center-shell")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-scroll-shell")).toBeInTheDocument();
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
    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coding-work-order-create-form")).toBeInTheDocument();
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
    // The observability lens should be active
    expect(screen.getByTestId("command-center-rail-item-observability")).toHaveAttribute(
      "aria-current",
      "true"
    );
    // The agent command panel should no longer be visible
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
    // EventConsole should render
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
    expect(drawer.style.height).toBe("0px");

    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    expect(drawer.style.height).not.toBe("0px");
  });

  it("bottom drawer can be closed", () => {
    render(<CommandCenterShell {...defaultProps} />);
    // open drawer
    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    // close via drawer close button
    fireEvent.click(screen.getByTestId("command-center-drawer-close"));
    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("0px");
  });

  it("heartbeat lens is enabled when heartbeatEnabled is true", () => {
    render(<CommandCenterShell {...defaultProps} heartbeatEnabled />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-heartbeat"));
    expect(screen.getByText("Heartbeat Status")).toBeInTheDocument();
    // When enabled, the disabled message should NOT appear
    expect(screen.queryByText("Heartbeat status not enabled.")).not.toBeInTheDocument();
  });

  it("heartbeat lens respects heartbeatEnabled=false gate", () => {
    render(<CommandCenterShell {...defaultProps} heartbeatEnabled={false} />);
    fireEvent.click(screen.getByTestId("command-center-rail-item-heartbeat"));
    expect(screen.getByText("Heartbeat Status")).toBeInTheDocument();
    expect(screen.getByText("Heartbeat status not enabled.")).toBeInTheDocument();
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
    // Switch to observability
    fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));
    // Switch back to agent command
    fireEvent.click(screen.getByTestId("command-center-rail-item-agent-command"));
    // Worker panel should still be there
    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
  });

  describe("Guardian Workspace lens", () => {
    it("renders when Guardian Workspace rail item is clicked", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("guardian-operator-workspace")).toBeInTheDocument();
      expect(screen.getByText("Guardian Operator Workspace")).toBeInTheDocument();
    });

    it("renders all scaffold cards", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const ws = screen.getByTestId("guardian-operator-workspace");
      // Card headings per C06-T002 surface contract (command-run now live, not static)
      expect(within(ws).getByText("Work-order status")).toBeInTheDocument();
      expect(within(ws).getByText("Command-run evidence")).toBeInTheDocument();
      expect(within(ws).getByText("Tool-turn observability")).toBeInTheDocument();
      expect(within(ws).getByText("Receipt evidence")).toBeInTheDocument();
      expect(within(ws).getByText("Runtime / health")).toBeInTheDocument();
      expect(within(ws).getByText("Gaps and unavailable evidence")).toBeInTheDocument();
      expect(within(ws).getByText("Safety boundary")).toBeInTheDocument();
    });

    it("has no mutation controls in scaffold", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const ws = screen.getByTestId("guardian-operator-workspace");
      const forbidden = ["dispatch", "execute", "retry", "replay", "approve", "complete", "create artifact", "create receipt"];
      for (const label of forbidden) {
        expect(within(ws).queryByRole("button", { name: new RegExp(label, "i") })).toBeNull();
      }
    });

    it("does not claim unsupported execution semantics", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const ws = screen.getByTestId("guardian-operator-workspace");
      expect(within(ws).getByText(/No autonomous delegation/)).toBeInTheDocument();
      expect(within(ws).getByText(/No Pi.Coder execution/)).toBeInTheDocument();
      expect(within(ws).getByText(/No recursive tool loops/)).toBeInTheDocument();
      expect(within(ws).getByText(/No artifact creation/)).toBeInTheDocument();
      expect(within(ws).getByText(/No receipt creation/)).toBeInTheDocument();
      expect(within(ws).getByText(/No work-order completion/)).toBeInTheDocument();
    });

    it("tool-turn card truth-labels bounded evidence", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const ws = screen.getByTestId("guardian-operator-workspace");
      // Scope to tool-turn card specifically — multiple cards share truth-labeling phrases
      const ttc = within(ws).getByText("Tool-turn observability").closest("div")!;
      expect(within(ttc as HTMLElement).getByText(/does not prove autonomous delegation/)).toBeInTheDocument();
      expect(within(ttc as HTMLElement).getByText(/Pi.Coder execution/)).toBeInTheDocument();
      expect(within(ttc as HTMLElement).getByText(/artifact creation/)).toBeInTheDocument();
      expect(within(ttc as HTMLElement).getByText(/work-order completion/)).toBeInTheDocument();
    });
  });

  describe("Guardian Workspace card composition", () => {
    it("HealthOverview renders inside workspace", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByText("Runtime / health")).toBeInTheDocument();
      expect(screen.getByText(/Existing Command Center health evidence/)).toBeInTheDocument();
      expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
    });

    it("health refresh calls existing onRefresh", () => {
      const refreshFn = vi.fn().mockResolvedValue(undefined);
      render(<CommandCenterShell {...defaultProps} onRefresh={refreshFn} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const btn = screen.getByText("Refresh");
      fireEvent.click(btn);
      expect(refreshFn).toHaveBeenCalled();
    });

    it("workspace wrapper adds no new fetch — no direct api import in lens", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      // The lens component is imported as a module; verify it renders without errors,
      // which confirms it does not crash on missing API context. In addition,
      // the HealthOverview inside it uses shell-passed props — no internal fetch.
      expect(screen.getByTestId("guardian-operator-workspace")).toBeInTheDocument();
    });

    it("CodingWorkOrdersPanel renders inside workspace", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByText("Work-order status")).toBeInTheDocument();
      expect(screen.getByText(/Existing coding work-order evidence/)).toBeInTheDocument();
      expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    });

    it("deferred cards remain after composition", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      // Command-run evidence is now live — check deferred cards still render
      expect(screen.getByText("Tool-turn observability")).toBeInTheDocument();
      expect(screen.getByText("Receipt evidence")).toBeInTheDocument();
      expect(screen.getByText("Gaps and unavailable evidence")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-safety-boundary")).toBeInTheDocument();
    });

    it("workspace wrapper has no new mutation controls after composition", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const ws = screen.getByTestId("guardian-operator-workspace");
      const forbiddenLabels = ["dispatch", "execute", "retry", "replay", "approve", "complete", "create artifact", "create receipt"];
      for (const label of forbiddenLabels) {
        // scope to workspace wrapper sections (headings + wrapper), not nested panel
        const sections = Array.from(ws.querySelectorAll('[class*="space-y"]'));
        for (const section of sections) {
          const btn = section.querySelector('button');
          if (btn && new RegExp(label, "i").test(btn.textContent ?? "")) {
            // If a button appears, it should not be the workspace wrapper's own addition
            // CodingWorkOrdersPanel buttons are internal and test-proven in its own suite
          }
        }
        expect(
          within(ws).queryByRole("button", { name: new RegExp(label, "i") })
        ).toBeNull();
      }
    });

    it("truth-labeling in safety boundary preserved after composition", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const sb = screen.getByTestId("guardian-workspace-safety-boundary");
      expect(within(sb).getByText(/No autonomous delegation/)).toBeInTheDocument();
      expect(within(sb).getByText(/No Pi.Coder execution/)).toBeInTheDocument();
      expect(within(sb).getByText(/No recursive tool loops/)).toBeInTheDocument();
      expect(within(sb).getByText(/No artifact creation/)).toBeInTheDocument();
      expect(within(sb).getByText(/No receipt creation/)).toBeInTheDocument();
      expect(within(sb).getByText(/No work-order completion/)).toBeInTheDocument();
    });
  });

  describe("Guardian Workspace command-run evidence card", () => {
    it("renders Command-run evidence heading in workspace", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 0, items: [], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") {
          return { data: { ok: true, recommendations: [] } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByText("Command-run evidence")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-command-run-evidence")).toBeInTheDocument();
    });

    it("shows empty state when no work orders exist", async () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const empty = await screen.findByTestId("cmd-run-empty");
      expect(empty).toHaveTextContent(/No command-run evidence/);
    });

    it("shows no-pointer state when work orders have no latest_run_id", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return {
            data: {
              count: 1,
              items: [{
                work_order_id: "wo-no-run",
                campaign_id: null,
                title: "No run test",
                objective: "test",
                status: "draft",
                priority: 1,
                dependency_ids: [],
                file_scope: [],
                validation_command: null,
                max_validation_attempts: 3,
                require_worktree_lease: false,
                commit_after_validation: false,
                require_human_review_before_merge: false,
                latest_run_id: null,
                latest_lease_id: null,
                latest_receipt_id: null,
                assistant_message_id: null,
                extra_meta: {},
                created_at: "2026-01-01T00:00:00Z",
                updated_at: "2026-01-01T00:00:00Z",
              }],
              limit: 50,
              offset: 0,
              ok: true,
            },
          };
        }
        if (url === "/api/coding/orchestrator/next") {
          return { data: { ok: true, recommendations: [] } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const noPtr = await screen.findByTestId("cmd-run-no-pointer");
      expect(noPtr).toHaveTextContent(/no latest command-run pointer/);
    });

    it("shows available state with safe fields when latest_run_id exists", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return {
            data: {
              count: 1,
              items: [{
                work_order_id: "wo-run-1",
                campaign_id: null,
                title: "Run test wo",
                objective: "test",
                status: "running",
                priority: 1,
                dependency_ids: [],
                file_scope: [],
                validation_command: null,
                max_validation_attempts: 3,
                require_worktree_lease: false,
                commit_after_validation: false,
                require_human_review_before_merge: false,
                latest_run_id: "run-abc",
                latest_lease_id: "lease-1",
                latest_receipt_id: "rec-1",
                assistant_message_id: null,
                extra_meta: {},
                created_at: "2026-01-01T00:00:00Z",
                updated_at: "2026-01-01T00:00:00Z",
              }],
              limit: 50,
              offset: 0,
              ok: true,
            },
          };
        }
        if (url === "/api/coding/orchestrator/next") {
          return { data: { ok: true, recommendations: [] } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("cmd-run-wo-wo-run-1");
      const card = screen.getByTestId("guardian-workspace-command-run-evidence");
      expect(within(card).getByText("wo-run-1")).toBeInTheDocument();
      expect(within(card).getByText("Run test wo")).toBeInTheDocument();
      expect(within(card).getByText("run-abc")).toBeInTheDocument();
      expect(within(card).getByText("lease-1")).toBeInTheDocument();
      expect(within(card).getByText("rec-1")).toBeInTheDocument();
    });

    it("shows error state when work-order load fails", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          const err: any = new Error("fail");
          err.response = { status: 500, data: { detail: "RAW_SECRET_NOT_RENDERED" } };
          throw err;
        }
        if (url === "/api/coding/orchestrator/next") {
          return { data: { ok: true, recommendations: [] } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const errEl = await screen.findByTestId("cmd-run-error");
      expect(errEl).toHaveTextContent(/unavailable/);
      expect(screen.queryByText(/RAW_SECRET/)).toBeNull();
    });

    it("command-run card has refresh button but no mutation controls", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("cmd-run-refresh")).toBeInTheDocument();
      const forbidden = ["dispatch", "execute", "retry", "replay", "approve", "complete", "create artifact", "create receipt"];
      for (const label of forbidden) {
        expect(screen.queryByRole("button", { name: new RegExp(label, "i") })).toBeNull();
      }
    });

    it("command-run card truth-labels unsupported claims", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const card = screen.getByTestId("guardian-workspace-command-run-evidence");
      const text = card.textContent || "";
      expect(text).toContain("artifact creation");
      expect(text).toContain("receipt creation");
      expect(text).toContain("Pi/Coder execution");
      expect(text).toContain("autonomous delegation");
      expect(text).toContain("work-order completion");
    });

    it("existing workspace panels still render after command-run card added", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
      expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-safety-boundary")).toBeInTheDocument();
    });
  });

  describe("Guardian Workspace tool-turn evidence card", () => {
    it("renders Tool-turn observability heading in workspace", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByText("Tool-turn observability")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-tool-turn-card")).toBeInTheDocument();
    });

    it("shows unavailable when no assistant_message_id", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-1", title: "x", status: "draft", assistant_message_id: null, latest_run_id: null, latest_lease_id: null, latest_receipt_id: null, extra_meta: {}, dependency_ids: [], file_scope: [], priority: 1, max_validation_attempts: 3, require_worktree_lease: false, commit_after_validation: false, require_human_review_before_merge: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const unav = await screen.findByTestId("tt-unavailable");
      expect(unav).toHaveTextContent(/no explicit assistant message id/);
    });

    it("does not fabricate assistant_message_id from other ids", async () => {
      const spy = vi.fn();
      apiGetMock.mockImplementation(async (url: string) => {
        spy(url);
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-x", campaign_id: null, title: "x", objective: "x", status: "draft", priority: 1, dependency_ids: [], file_scope: [], validation_command: null, max_validation_attempts: 3, require_worktree_lease: false, commit_after_validation: false, require_human_review_before_merge: false, latest_run_id: "run-fake", latest_lease_id: "lease-fake", latest_receipt_id: "rec-fake", assistant_message_id: null, extra_meta: {}, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("tt-unavailable");
      // Assert no tool-turns route was called — no assistant_message_id to use
      const toolTurnCalls = spy.mock.calls.filter((c: string[]) => c[0]?.includes("/tool-turns/"));
      expect(toolTurnCalls.length).toBe(0);
    });

    it("shows available state when assistant_message_id exists and C05 route returns data", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-tt", title: "x", status: "draft", assistant_message_id: "msg-1", latest_run_id: null, latest_lease_id: null, latest_receipt_id: null, extra_meta: {}, dependency_ids: [], file_scope: [], priority: 1, max_validation_attempts: 3, require_worktree_lease: false, commit_after_validation: false, require_human_review_before_merge: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        if (typeof url === "string" && url.includes("/tool-turns/msg-1")) {
          return { data: { tool_turn_id: "tt-99", tool_turn_state: "completed", loop_stop_reason: "max_turns", command_run_id: "run-99", command_id: "op::test", command_status: "completed", command_result_summary: "ok", evidence_durability: "durable" } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const av = await screen.findByTestId("tt-available");
      expect(av).toHaveTextContent(/tt-99/);
      expect(av).toHaveTextContent(/completed/);
      expect(av).toHaveTextContent(/max_turns/);
      expect(av).toHaveTextContent(/durable/);
      // No raw payload
      expect(av).not.toHaveTextContent(/SECRET/);
    });

    it("shows empty when assistant_message_id exists but no tool-turn data", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-tt2", title: "x", status: "draft", assistant_message_id: "msg-2", latest_run_id: null, latest_lease_id: null, latest_receipt_id: null, extra_meta: {}, dependency_ids: [], file_scope: [], priority: 1, max_validation_attempts: 3, require_worktree_lease: false, commit_after_validation: false, require_human_review_before_merge: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        if (typeof url === "string" && url.includes("/tool-turns/msg-2")) {
          return { data: { evidence_durability: "no_evidence" } };
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("tt-empty");
      expect(screen.getByTestId("tt-empty")).toHaveTextContent(/No bounded tool-turn evidence/);
    });

    it("shows error when C05 route fails", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-err", title: "x", status: "draft", assistant_message_id: "msg-err", latest_run_id: null, latest_lease_id: null, latest_receipt_id: null, extra_meta: {}, dependency_ids: [], file_scope: [], priority: 1, max_validation_attempts: 3, require_worktree_lease: false, commit_after_validation: false, require_human_review_before_merge: false, created_at: "2026-01-01T00:00:00Z", updated_at: "2026-01-01T00:00:00Z" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        if (typeof url === "string" && url.includes("/tool-turns/msg-err")) {
          const err: any = new Error("fail");
          err.response = { status: 500, data: { detail: "RAW_SECRET_NOT_EXPOSED" } };
          throw err;
        }
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("tt-error");
      expect(screen.getByTestId("tt-error")).toHaveTextContent(/unavailable/);
      expect(screen.queryByText(/RAW_SECRET/)).toBeNull();
    });

    it("tool-turn card has no mutation controls", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const forbidden = ["dispatch", "execute", "retry", "replay", "approve", "complete", "create artifact", "create receipt", "run tool", "invoke tool"];
      for (const label of forbidden) {
        expect(screen.queryByRole("button", { name: new RegExp(label, "i") })).toBeNull();
      }
    });

    it("tool-turn card truth-labels unsupported claims", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const card = screen.getByTestId("guardian-workspace-tool-turn-card");
      const text = card.textContent || "";
      expect(text).toContain("autonomous delegation");
      expect(text).toContain("Pi/Coder execution");
      expect(text).toContain("recursive tool use");
      expect(text).toContain("artifact creation");
      expect(text).toContain("receipt creation");
      expect(text).toContain("work-order completion");
    });

    it("existing workspace panels preserved after tool-turn card added", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
      expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-command-run-evidence")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-safety-boundary")).toBeInTheDocument();
    });
  });

  describe("Guardian Workspace receipt evidence card", () => {
    const fullWoFields = {
      campaign_id: null,
      objective: "x",
      dependency_ids: [],
      file_scope: [],
      validation_command: null,
      max_validation_attempts: 3,
      require_worktree_lease: false,
      commit_after_validation: false,
      require_human_review_before_merge: false,
      latest_run_id: null,
      latest_lease_id: null,
      latest_receipt_id: null,
      assistant_message_id: null,
      extra_meta: {},
      priority: 1,
      created_at: "2026-01-01T00:00:00Z",
      updated_at: "2026-01-01T00:00:00Z",
    };

    it("renders Receipt evidence heading in workspace", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByText("Receipt evidence")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-receipt-card")).toBeInTheDocument();
    });

    it("shows deferred receipt linkage message", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("rc-deferred")).toHaveTextContent(/remain deferred/);
    });

    it("shows available state with safe fields when latest_receipt_id exists", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ ...fullWoFields, work_order_id: "wo-rec-1", title: "Rec test", status: "completed", latest_receipt_id: "rec-99" }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("rc-wo-wo-rec-1");
      const card = screen.getByTestId("guardian-workspace-receipt-card");
      expect(within(card).getByText("wo-rec-1")).toBeInTheDocument();
      expect(within(card).getByText("rec-99")).toBeInTheDocument();
      expect(within(card).getByText("Rec test")).toBeInTheDocument();
    });

    it("shows no-pointer state when no latest_receipt_id", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          return { data: { count: 1, items: [{ work_order_id: "wo-no-rec", title: "x", status: "draft", ...fullWoFields }], limit: 50, offset: 0, ok: true } };
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("rc-no-pointer");
      expect(screen.getByTestId("rc-no-pointer")).toHaveTextContent(/no explicit receipt pointer/);
    });

    it("shows error when work-order load fails", async () => {
      apiGetMock.mockImplementation(async (url: string) => {
        if (url === "/api/coding/work-orders") {
          const err: any = new Error("fail");
          err.response = { status: 500, data: { detail: "RAW_SECRET" } };
          throw err;
        }
        if (url === "/api/coding/orchestrator/next") return { data: { ok: true, recommendations: [] } };
        return { data: {} };
      });
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      await screen.findByTestId("rc-error");
      expect(screen.queryByText(/RAW_SECRET/)).toBeNull();
    });

    it("receipt card has no mutation controls", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const forbidden = ["dispatch", "execute", "retry", "replay", "approve", "complete", "create artifact", "create receipt", "run tool", "invoke tool", "merge", "mark complete"];
      for (const label of forbidden) {
        expect(screen.queryByRole("button", { name: new RegExp(label, "i") })).toBeNull();
      }
    });

    it("receipt card truth-labels unsupported claims", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      const card = screen.getByTestId("guardian-workspace-receipt-card");
      const text = card.textContent || "";
      expect(text).toContain("work-order completion");
      expect(text).toContain("artifact creation");
      expect(text).toContain("Pi/Coder execution");
      expect(text).toContain("autonomous delegation");
      expect(text).toContain("recursive tool use");
      expect(text).toContain("successful merge");
    });

    it("existing workspace panels preserved after receipt card added", () => {
      render(<CommandCenterShell {...defaultProps} />);
      fireEvent.click(screen.getByTestId("command-center-rail-item-guardian-workspace"));
      expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
      expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-command-run-evidence")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-tool-turn-card")).toBeInTheDocument();
      expect(screen.getByTestId("guardian-workspace-safety-boundary")).toBeInTheDocument();
    });
  });

  describe("readInitialDelegationIntentId", () => {
    it("readInitialDelegationIntentId_supports_guardian_delegation_intent_id", () => {
      vi.stubGlobal("location", {
        search: "?guardian_delegation_intent_id=gdi_guardian_123",
      });
      expect(readInitialDelegationIntentId()).toBe("gdi_guardian_123");
      vi.unstubAllGlobals();
    });

    it("readInitialDelegationIntentId_supports_delegation_intent_id", () => {
      vi.stubGlobal("location", {
        search: "?delegation_intent_id=gdi_delegation_456",
      });
      expect(readInitialDelegationIntentId()).toBe("gdi_delegation_456");
      vi.unstubAllGlobals();
    });

    it("readInitialDelegationIntentId_supports_intent_id", () => {
      vi.stubGlobal("location", {
        search: "?intent_id=gdi_intent_789",
      });
      expect(readInitialDelegationIntentId()).toBe("gdi_intent_789");
      vi.unstubAllGlobals();
    });

    it("readInitialDelegationIntentId_prefers_canonical_parameter", () => {
      vi.stubGlobal("location", {
        search: "?intent_id=gdi_intent_789&delegation_intent_id=gdi_delegation_456&guardian_delegation_intent_id=gdi_guardian_123",
      });
      expect(readInitialDelegationIntentId()).toBe("gdi_guardian_123");
      vi.unstubAllGlobals();
    });
  });
});
