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
import {
  COMMAND_CENTER_HEALTH_STATES,
  COMMAND_CENTER_RUN_STATUSES,
  COMMAND_CENTER_RUN_TERMINAL_OUTCOMES,
  describeCommandCenterHealthStatePresentation,
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
  {
    checkedAt: Date.parse("2026-04-01T15:59:02Z"),
    endpoint: "/health/deps",
    error: "HTTP 503",
    httpStatus: 503,
    key: "deps",
    label: "Deps",
    raw: '{"status":"fail"}',
    status: COMMAND_CENTER_HEALTH_STATES.DOWN,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:03Z"),
    endpoint: "/health/vector",
    error: null,
    httpStatus: 200,
    key: "vector",
    label: "Vector",
    raw: '{"ok":true}',
    status: COMMAND_CENTER_HEALTH_STATES.OK,
  },
  {
    checkedAt: Date.parse("2026-04-01T15:59:04Z"),
    endpoint: "/health/memory",
    error: null,
    httpStatus: 200,
    key: "memory",
    label: "Memory",
    raw: '{"status":"unknown"}',
    status: COMMAND_CENTER_HEALTH_STATES.UNKNOWN,
  },
];

const mockedRuns: CommandCenterRun[] = [
  {
    eventCount: 4,
    events: [
      {
        eventId: "evt-1",
        json: { type: "chat.completion", thread_id: 42 },
        kind: null,
        latestTurnMessageId: "501",
        raw: '{"type":"chat.completion","thread_id":42}',
        receivedAt: Date.parse("2026-04-01T15:58:00Z"),
        requestId: null,
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
      },
      {
        eventId: "evt-2",
        json: { thread_id: 42 },
        kind: null,
        latestTurnMessageId: "501",
        raw: '{"thread_id":42}',
        receivedAt: Date.parse("2026-04-01T15:58:10Z"),
        requestId: null,
        runId: "run-alpha",
        sseType: "task.running",
        state: "running",
        status: null,
        summary: "chat completion running",
        taskId: "task-alpha",
        taskType: null,
        terminalOutcome: null,
        threadId: 42,
        turnId: "turn-alpha",
        type: "task.running",
      },
      {
        eventId: "evt-3",
        json: { thread_id: 42 },
        kind: null,
        latestTurnMessageId: "501",
        raw: '{"thread_id":42}',
        receivedAt: Date.parse("2026-04-01T15:58:20Z"),
        requestId: null,
        runId: "run-alpha",
        sseType: "task.chunk",
        state: "chunk",
        status: null,
        summary: "chat completion chunk",
        taskId: "task-alpha",
        taskType: null,
        terminalOutcome: null,
        threadId: 42,
        turnId: "turn-alpha",
        type: "task.chunk",
      },
      {
        eventId: "evt-4",
        json: { thread_id: 42, message_id: 501 },
        kind: null,
        latestTurnMessageId: "501",
        raw: '{"thread_id":42,"message_id":501}',
        receivedAt: Date.parse("2026-04-01T15:58:30Z"),
        requestId: null,
        runId: "run-alpha",
        sseType: "task.completed",
        state: "completed",
        status: null,
        summary: "chat completion completed",
        taskId: "task-alpha",
        taskType: null,
        terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
        threadId: 42,
        turnId: "turn-alpha",
        type: "task.completed",
      },
    ],
    identityKind: "task",
    key: "task-alpha",
    lastEvent: {
      eventId: "evt-4",
      json: { thread_id: 42, message_id: 501 },
      kind: null,
      latestTurnMessageId: "501",
      raw: '{"thread_id":42,"message_id":501}',
      receivedAt: Date.parse("2026-04-01T15:58:30Z"),
      requestId: null,
      runId: "run-alpha",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-alpha",
      taskType: null,
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 42,
      turnId: "turn-alpha",
      type: "task.completed",
    },
    lastEventAt: Date.parse("2026-04-01T15:58:30Z"),
    lastKind: null,
    lastType: "task.completed",
    latestTurnMessageId: "501",
    requestId: null,
    runId: "run-alpha",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-alpha",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    traceEvidence: {
      documentCount: 4,
      graphCount: 1,
      latestTurnContentPresent: true,
      latestTurnMessageId: "501",
      latestTurnTracePresent: true,
      memoryCount: 2,
      retrievalQuery: "How does the cache behave?",
      retrievalQueryMatchesLatestTurn: true,
      retrievalQueryPresent: true,
      retrievalTarget: "search-index",
      sourceMode: "personal_knowledge",
      tracePresenceState: "latest_turn_trace_present",
      tracePresent: true,
      traceUrl: "/api/chat/debug/rag-trace/42/latest",
      widenReason: "explicit_personal_knowledge",
    },
    traceUrl: "/api/chat/debug/rag-trace/42/latest",
    threadId: 42,
    turnId: "turn-alpha",
  },
  {
    eventCount: 1,
    identityKind: "synthetic",
    key: "event-raw-bravo",
    lastEvent: {
      eventId: "evt-raw-1",
      json: { message: "No classification yet" },
      kind: null,
      latestTurnMessageId: null,
      raw: '{"message":"No classification yet"}',
      receivedAt: Date.parse("2026-04-01T15:57:30Z"),
      requestId: null,
      runId: null,
      sseType: "message",
      state: null,
      status: "unknown",
      summary: "No classification yet",
      taskId: null,
      taskType: null,
      terminalOutcome: null,
      threadId: null,
      turnId: null,
      type: null,
    },
    lastEventAt: Date.parse("2026-04-01T15:57:30Z"),
    lastKind: null,
    lastType: null,
    requestId: null,
    runId: null,
    runType: null,
    state: null,
    status: "unknown",
    summary: "unclassified event",
    taskId: null,
    terminalOutcome: null,
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
    run ? (
      <div data-testid="run-detail-drawer">
        Selected run: {run.key} · thread {run.threadId ?? "none"} · latest turn{" "}
        {run.latestTurnMessageId ?? "none"} · trace{" "}
        {run.traceEvidence?.tracePresent ? "present" : "none"}
      </div>
    ) : null,
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

    const healthSamples = [
      [COMMAND_CENTER_HEALTH_STATES.OK, { label: "OK", tone: "active", isFallback: false }],
      [
        COMMAND_CENTER_HEALTH_STATES.DEGRADED,
        { label: "Degraded", tone: "attention", isFallback: false },
      ],
      [COMMAND_CENTER_HEALTH_STATES.DOWN, { label: "Down", tone: "danger", isFallback: false }],
      [COMMAND_CENTER_HEALTH_STATES.UNKNOWN, { label: "Unknown", tone: "subtle", isFallback: false }],
    ] as const;

    for (const [status, expected] of healthSamples) {
      expect(describeCommandCenterHealthStatePresentation(status)).toMatchObject(expected);
    }
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
      within(screen.getByTestId("command-center-health-llm")).getByText("Degraded")
    ).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-health-deps")).getByText("Down")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-health-memory")).getByText("Unknown")).toBeInTheDocument();
    expect(within(healthStrip).getAllByText("Inspect raw details").length).toBeGreaterThan(0);

    const runsFeed = screen.getByTestId("command-center-runs-feed");
    expect(within(runsFeed).getByText("chat completion")).toBeInTheDocument();
    expect(within(runsFeed).getByText("Unknown run")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getAllByText("Completed").length).toBeGreaterThan(1);
    expect(within(screen.getByTestId("command-center-run-event-raw-bravo")).getByText("Unknown")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getByText("Events: 4")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getByText("Task: task-alpha")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getByText("Thread: 42")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getByText("Latest turn message: 501")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-task-alpha")).getByText("Turn: turn-alpha")).toBeInTheDocument();
    expect(
      within(runsFeed).getByRole("button", { name: /open details for chat completion/i })
    ).toBeInTheDocument();
    expect(
      within(runsFeed).getByRole("button", { name: /open details for unknown run/i })
    ).toBeInTheDocument();
    expect(within(runsFeed).getAllByText("Inspect raw events").length).toBeGreaterThan(0);
    expect(screen.getByText("attention")).toBeInTheDocument();
    expect(screen.getByText("mystery signal")).toBeInTheDocument();
    expect(within(runsFeed).getByText("Unknown")).toBeInTheDocument();

    fireEvent.click(
      within(runsFeed).getByRole("button", { name: /open details for chat completion/i })
    );
    expect(screen.getByTestId("run-detail-drawer")).toHaveTextContent("task-alpha");
    expect(screen.getByTestId("run-detail-drawer")).toHaveTextContent("thread 42");
    expect(screen.getByTestId("run-detail-drawer")).toHaveTextContent("latest turn 501");
    expect(screen.getByTestId("run-detail-drawer")).toHaveTextContent("trace present");

    expect(screen.getByText("Approvals")).toBeInTheDocument();
    expect(screen.getByText("attention")).toBeInTheDocument();
    expect(screen.queryByText(/composer/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/message thread/i)).not.toBeInTheDocument();
  });
});
