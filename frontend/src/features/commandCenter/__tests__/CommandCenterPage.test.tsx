import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import CommandCenterPage from "../CommandCenterPage";
import { describeRuntimeStatusPresentation } from "@/contracts/runtimeTokens";

import type {
  CommandCenterApproval,
  CommandCenterHealthItem,
  CommandCenterRun,
} from "@/features/commandCenter/types";

const mockRefresh = vi.fn();

const mockedHealthItems: CommandCenterHealthItem[] = [
  {
    checkedAt: Date.parse("2026-04-01T15:59:00Z"),
    endpoint: "/health",
    error: null,
    httpStatus: 200,
    key: "core",
    label: "Core",
    raw: '{"ok":true}',
    status: "OK",
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:01Z"),
    endpoint: "/health/llm",
    error: null,
    httpStatus: 200,
    key: "llm",
    label: "LLM",
    raw: '{"status":"degraded"}',
    status: "UNKNOWN",
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:02Z"),
    endpoint: "/health/deps",
    error: "HTTP 503",
    httpStatus: 503,
    key: "deps",
    label: "Deps",
    raw: '{"status":"fail"}',
    status: "FAIL",
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:03Z"),
    endpoint: "/health/vector",
    error: null,
    httpStatus: 200,
    key: "vector",
    label: "Vector",
    raw: '{"ok":true}',
    status: "OK",
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:04Z"),
    endpoint: "/health/memory",
    error: null,
    httpStatus: 200,
    key: "memory",
    label: "Memory",
    raw: '{"ok":true}',
    status: "OK",
  },
];

const mockedRuns: CommandCenterRun[] = [
  {
    eventCount: 4,
    key: "run-alpha",
    lastEvent: {
      eventId: "evt-1",
      json: { message: "Processing alpha" },
      kind: "task.started",
      raw: '{"message":"Processing alpha"}',
      receivedAt: Date.parse("2026-04-01T15:58:30Z"),
      runId: "run-alpha",
      sseType: "message",
      status: "running",
      summary: "Processing alpha",
      taskId: "task-alpha",
      type: "task.started",
    },
    lastEventAt: Date.parse("2026-04-01T15:58:30Z"),
    lastKind: "task.started",
    lastType: "task.started",
    runId: "run-alpha",
    status: "running",
    summary: "Processing alpha",
    taskId: "task-alpha",
  },
  {
    eventCount: 2,
    key: "run-bravo",
    lastEvent: {
      eventId: "evt-2",
      json: { message: "No classification yet" },
      kind: "task.updated",
      raw: '{"message":"No classification yet"}',
      receivedAt: Date.parse("2026-04-01T15:57:30Z"),
      runId: "run-bravo",
      sseType: "message",
      status: "unknown",
      summary: "No classification yet",
      taskId: "task-bravo",
      type: "task.updated",
    },
    lastEventAt: Date.parse("2026-04-01T15:57:30Z"),
    lastKind: "task.updated",
    lastType: "task.updated",
    runId: "run-bravo",
    status: "unknown",
    summary: "No classification yet",
    taskId: "task-bravo",
  },
];

const mockedApprovals: CommandCenterApproval[] = [
  {
    event: {
      eventId: "approval-evt-1",
      json: { message: "Need clarification" },
      kind: "approval.requested",
      raw: '{"message":"Need clarification"}',
      receivedAt: Date.parse("2026-04-01T15:57:00Z"),
      runId: "run-bravo",
      sseType: "message",
      status: "attention",
      summary: "Need clarification",
      taskId: "task-bravo",
      type: "approval.requested",
    },
    key: "approval-1",
    label: "Need clarification",
    receivedAt: Date.parse("2026-04-01T15:57:00Z"),
    runId: "run-bravo",
    runKey: "run-bravo",
    status: "attention",
    summary: "Need clarification",
    taskId: "task-bravo",
  },
  {
    event: {
      eventId: "approval-evt-2",
      json: { message: "Escalation pending" },
      kind: "approval.requested",
      raw: '{"message":"Escalation pending"}',
      receivedAt: Date.parse("2026-04-01T15:56:30Z"),
      runId: "run-alpha",
      sseType: "message",
      status: "mystery_signal",
      summary: "Escalation pending",
      taskId: "task-alpha",
      type: "approval.requested",
    },
    key: "approval-2",
    label: "Escalation pending",
    receivedAt: Date.parse("2026-04-01T15:56:30Z"),
    runId: "run-alpha",
    runKey: "run-alpha",
    status: "mystery_signal",
    summary: "Escalation pending",
    taskId: "task-alpha",
  },
];

vi.mock("../hooks/useCommandCenterEvents", () => ({
  default: () => ({
    approvals: mockedApprovals,
    connectionDetail: "Listening to /api/events",
    connectionState: "open",
    events: [],
    lastEventAt: Date.parse("2026-04-01T15:58:30Z"),
    runs: mockedRuns,
    unauthorized: false,
  }),
}));

vi.mock("../hooks/useHealthSummary", () => ({
  default: () => ({
    healthItems: mockedHealthItems,
    lastCheckedAt: Date.parse("2026-04-01T15:59:04Z"),
    loading: false,
    refresh: mockRefresh,
  }),
}));

vi.mock("../components/RunDetailDrawer", () => ({
  default: ({ run }: { run: CommandCenterRun | null }) =>
    run ? <div data-testid="run-detail-drawer">Selected run: {run.key}</div> : null,
}));

beforeEach(() => {
  mockRefresh.mockClear();
});

describe("CommandCenterPage", () => {
  it("uses the canonical runtime status presentation map", () => {
    const samples = [
      ["healthy", { label: "healthy", tone: "active", isFallback: false }],
      ["degraded", { label: "degraded", tone: "attention", isFallback: false }],
      ["unknown", { label: "unknown", tone: "subtle", isFallback: false }],
      ["active", { label: "active", tone: "active", isFallback: false }],
      ["stale", { label: "stale", tone: "attention", isFallback: false }],
      ["offline", { label: "offline", tone: "danger", isFallback: false }],
      ["online", { label: "online", tone: "active", isFallback: false }],
      ["running", { label: "running", tone: "info", isFallback: false }],
      ["queued", { label: "queued", tone: "neutral", isFallback: false }],
      ["OK", { label: "OK", tone: "active", isFallback: false }],
      ["FAIL", { label: "FAIL", tone: "danger", isFallback: false }],
      ["UNKNOWN", { label: "UNKNOWN", tone: "subtle", isFallback: false }],
    ] as const;

    for (const [status, expected] of samples) {
      expect(describeRuntimeStatusPresentation(status)).toMatchObject(expected);
    }

    expect(describeRuntimeStatusPresentation("mystery_signal")).toMatchObject({
      label: "mystery signal",
      tone: "subtle",
      isFallback: true,
    });
  });

  it("renders a signal-first hierarchy for operators", () => {
    render(<CommandCenterPage enabled />);

    expect(
      screen.getByRole("heading", { name: /agent command center/i })
    ).toBeInTheDocument();

    const summaryStrip = screen.getByTestId("command-center-summary-strip");
    expect(summaryStrip).toBeInTheDocument();
    expect(screen.getByTestId("command-center-health-strip")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-runs-feed")).toBeInTheDocument();

    expect(within(summaryStrip).getByLabelText("Service status open")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-summary-last-event-value")).toHaveTextContent(
      /2026/i
    );
    expect(screen.getByTestId("command-center-summary-health-count")).toHaveTextContent("5");
    expect(screen.getByTestId("command-center-summary-run-count")).toHaveTextContent("2");
    expect(within(summaryStrip).getByLabelText(/unknown items 2/i)).toBeInTheDocument();

    const healthStrip = screen.getByTestId("command-center-health-strip");
    expect(within(healthStrip).getByText("Core")).toBeInTheDocument();
    expect(within(healthStrip).getByText("LLM")).toBeInTheDocument();
    expect(within(healthStrip).getByText("Deps")).toBeInTheDocument();
    expect(within(healthStrip).getByText("Vector")).toBeInTheDocument();
    expect(within(healthStrip).getByText("Memory")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-health-core")).getByText("OK")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("command-center-health-llm")).getByText("UNKNOWN")
    ).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-health-deps")).getByText("FAIL")).toBeInTheDocument();
    expect(within(healthStrip).getAllByText("Inspect raw details").length).toBeGreaterThan(0);

    const runsFeed = screen.getByTestId("command-center-runs-feed");
    expect(within(runsFeed).getByText("Processing alpha")).toBeInTheDocument();
    expect(within(runsFeed).getByText("No classification yet")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-run-alpha")).getByText("running")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-run-bravo")).getByText("unknown")).toBeInTheDocument();
    expect(
      within(runsFeed).getByRole("button", { name: /open details for processing alpha/i })
    ).toBeInTheDocument();
    expect(
      within(runsFeed).getByRole("button", { name: /open details for no classification yet/i })
    ).toBeInTheDocument();
    expect(within(runsFeed).getAllByText("Inspect event details").length).toBeGreaterThan(0);
    expect(screen.getByText("attention")).toBeInTheDocument();
    expect(screen.getByText("mystery signal")).toBeInTheDocument();

    fireEvent.click(
      within(runsFeed).getByRole("button", { name: /open details for processing alpha/i })
    );
    expect(screen.getByTestId("run-detail-drawer")).toHaveTextContent("run-alpha");

    expect(screen.getByText("Approvals")).toBeInTheDocument();
    expect(screen.getByText("attention")).toBeInTheDocument();
    expect(screen.queryByText(/composer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/message thread/i)).not.toBeInTheDocument();
  });
});
