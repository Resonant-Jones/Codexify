import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, within } from "@testing-library/react";

import CommandCenterPage from "../CommandCenterPage";
import { describeRuntimeStatusPresentation } from "@/contracts/runtimeTokens";

import type {
  CommandCenterEvent,
  CommandCenterHealthItem,
  CommandCenterRagTracePayload,
  CommandCenterRetrievalPosture,
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

const mockedTracePayload: CommandCenterRagTracePayload = {
  memory: [
    {
      depthUsed: "project",
      id: "memory-1",
      origin: "memory",
      raw: { id: "memory-1" },
      score: 0.71,
      silo: "memory",
      source: "memory note",
      text: "Cached project memory for the task.",
      threadId: "42",
      timestamp: "2026-04-01T15:58:12Z",
    },
  ],
  resolvedThreadId: 42,
  semantic: [
    {
      depthUsed: "project",
      id: "semantic-1",
      origin: "semantic",
      raw: { id: "semantic-1" },
      score: 0.92,
      silo: "semantic",
      source: "knowledge.md",
      text: "The cache keeps the latest entry for each key.",
      threadId: "42",
      timestamp: "2026-04-01T15:58:08Z",
    },
  ],
  // graph is accessed in buildOutcomeRows but not present in the type;
  // include it as an empty array so the optional chain doesn't throw.
  graph: [],
};

const mockedRawTrace = {
  attempted_model: "gpt-5-mini",
  attempted_provider: "openai",
  depth_mode: "project",
  final_model: "gpt-5",
  final_provider: "openai",
  fallback_reason: "model_capability",
  fallback_triggered: true,
  payload_summary: {
    final_model: "gpt-5",
    final_provider: "openai",
    graph_count: 1,
    linked_document_count: 3,
    message_count: 5,
    memory_count: 2,
    payload_char_count: 1234,
    payload_estimated_tokens: 321,
    persona_or_imprint_present: true,
    retrieval_injected: true,
    resolved_model: "gpt-5",
    resolved_provider: "openai",
    semantic_count: 4,
  },
  project_id: 7,
  provider_override: "openai",
  retrieval_mode: "project",
  retrieval_plan: {
    allow_global_fallback: false,
    escalation_order: ["graph", "memory", "semantic"],
    graph_allowance: "enabled",
    intent: "answer_question",
    primary_scope: "knowledge_base",
    reasons: ["project request"],
    retrieval_needed: true,
    resolved_depth: "project",
    time_mode: "recent",
    user_depth: "project",
  },
  retrieval_target: "search-index",
  selection_source: "runtime_policy",
  source_mode: "personal_knowledge",
  thread_id: 42,
  trace_url: "/api/chat/debug/rag-trace/42/latest",
  widen_reason: "explicit_personal_knowledge",
} as const;

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
    attemptedModel: "gpt-5-mini",
    attemptedProvider: "openai",
    eventId: "evt-2",
    finalModel: "gpt-5",
    finalProvider: "openai",
    fallbackReason: "model_capability",
    fallbackTriggered: true,
    json: {
      thread_id: 42,
      message_id: "msg-4",
      retrieval_query: "How does the cache behave?",
      retrieval_query_matches_latest_turn: true,
      retrieval_target: "search-index",
    },
    kind: null,
    persistenceOutcome: "persisted",
    raw: '{"thread_id":42,"message_id":"msg-4"}',
    receivedAt: Date.parse("2026-04-01T15:58:30Z"),
    retrievalDepth: "project",
    retrievalIntent: "answer_question",
    retrievalQuery: "How does the cache behave?",
    retrievalQueryMatchesLatestTurn: true,
    retrievalTarget: "search-index",
    runId: "run-alpha",
    selectionSource: "runtime_policy",
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
  makeEvent({
    eventId: "evt-3",
    json: { message: "No classification yet" },
    kind: null,
    raw: '{"message":"No classification yet"}',
    receivedAt: Date.parse("2026-04-01T15:57:30Z"),
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
  }),
];

const mockedRuns: CommandCenterRun[] = [
  {
    attemptedModel: "gpt-5-mini",
    attemptedProvider: "openai",
    eventCount: 2,
    events: [mockedEvents[0], mockedEvents[1]],
    fallbackReason: "model_capability",
    fallbackTriggered: true,
    finalModel: "gpt-5",
    finalProvider: "openai",
    identityKind: "task",
    key: "task-alpha",
    lastEvent: mockedEvents[1],
    lastEventAt: Date.parse("2026-04-01T15:58:30Z"),
    lastKind: null,
    lastType: "task.completed",
    latestTurnMessageId: "msg-4",
    persistenceOutcome: "persisted",
    requestId: null,
    retrievalDepth: "project",
    retrievalIntent: "answer_question",
    runId: "run-alpha",
    runKind: "chat_completion",
    runType: "chat completion",
    selectionSource: "runtime_policy",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-alpha",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 42,
    traceEvidence: {
      documentCount: 4,
      graphCount: 1,
      latestTurnContentPresent: true,
      latestTurnMessageId: "msg-4",
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
    turnId: "turn-alpha",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-bravo",
    lastEvent: makeEvent({
      eventId: "evt-4",
      json: { thread_id: 84, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":84,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:58:45Z"),
      runId: "run-bravo",
      sseType: "task.state",
      state: "waiting_for_ack",
      status: "blocked",
      summary: "chat completion awaiting approval",
      taskId: "task-bravo",
      taskType: "chat.completion",
      terminalOutcome: null,
      threadId: 84,
      turnId: "turn-bravo",
      type: "task.state",
    }),
    lastEventAt: Date.parse("2026-04-01T15:58:45Z"),
    lastKind: null,
    lastType: "task.state",
    requestId: null,
    runId: "run-bravo",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "waiting for ack",
    status: COMMAND_CENTER_RUN_STATUSES.NEEDS_ATTENTION,
    summary: "chat completion · needs attention",
    taskId: "task-bravo",
    terminalOutcome: null,
    threadId: 84,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-bravo",
  },
];

vi.mock("../hooks/useCommandCenterEvents", () => ({
  default: () => ({
    connectionDetail: "Listening to /api/events",
    connectionState: "open",
    events: mockedEvents,
    lastEventAt: Date.parse("2026-04-01T15:58:45Z"),
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

vi.mock("../hooks/useRagTrace", () => ({
  default: (run: CommandCenterRun | null) => {
    if (run?.key === "task-alpha") {
      return {
        error: null,
        loading: false,
        rawTrace: mockedRawTrace,
        resolvedThreadId: 42,
        trace: mockedTracePayload,
        unavailable: false,
        unavailableReason: null,
      };
    }

    if (run?.key === "task-bravo") {
      return {
        error: null,
        loading: false,
        rawTrace: null,
        resolvedThreadId: 84,
        trace: null,
        unavailable: true,
        unavailableReason: "no_trace",
      };
    }

    return {
      error: null,
      loading: false,
      rawTrace: null,
      resolvedThreadId: null,
      trace: null,
      unavailable: true,
      unavailableReason: "no_run",
    };
  },
}));

const mockedRetrievalPosture: CommandCenterRetrievalPosture = {
  source_mode: "conversation",
  boundary_label: "active_conversation_only",
  retrieval_override_mode: "conversation",
  widen_reason: "none",
  conversation_only: true,
};

vi.mock("../hooks/useRetrievalPosture", () => ({
  default: (threadId: number | null) => {
    if (threadId === 42) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedRetrievalPosture,
        status: "ok",
      };
    }
    if (threadId === 84) {
      return {
        error: null,
        loading: false,
        retrievalPosture: null,
        status: "empty",
      };
    }
    return {
      error: null,
      loading: false,
      retrievalPosture: null,
      status: null,
    };
  },
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

  it("renders the dashboard surface with bounded diagnostics and raw telemetry", () => {
    render(<CommandCenterPage enabled />);

    expect(
      screen.getByRole("heading", { name: /agent command center/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Runtime summary")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-trace-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-event-console")).toBeInTheDocument();

    expect(screen.getAllByLabelText(/transport state open/i)).toHaveLength(2);
    expect(screen.getAllByText(/last event: .*2026/i)).toHaveLength(2);
    expect(screen.getByLabelText(/unknown items 2/i)).toBeInTheDocument();

    const healthOverview = screen.getByTestId("command-center-health-overview");
    expect(within(healthOverview).getByText("Core")).toBeInTheDocument();
    expect(within(healthOverview).getByText("LLM")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Deps")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Vector")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Memory")).toBeInTheDocument();

    fireEvent.click(within(healthOverview).getByRole("button", { name: /core/i }));
    expect(screen.getByText("Health detail: Core")).toBeInTheDocument();
    expect(screen.getByText("Parsed health detail")).toBeInTheDocument();
    expect(screen.getByText("Raw response")).toBeInTheDocument();

    const workbench = screen.getByTestId("command-center-trace-workbench");
    expect(within(workbench).getByText("RAG trace workbench")).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /report/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /raw trace/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /payload summary/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /task-alpha/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /task-bravo/i })).toBeInTheDocument();

    expect(within(workbench).getAllByText("Verdict")).toHaveLength(2);
    expect(within(workbench).getByText("Request")).toBeInTheDocument();
    expect(within(workbench).getByText("Retrieval Plan")).toBeInTheDocument();
    expect(within(workbench).getByText("Retrieval Outcome")).toBeInTheDocument();
    expect(within(workbench).getByText("Execution")).toBeInTheDocument();
    expect(
      within(workbench).getByRole("heading", { name: "Payload Summary" })
    ).toBeInTheDocument();
    expect(within(workbench).getByText("Notes / Warnings")).toBeInTheDocument();

    fireEvent.click(within(workbench).getByRole("button", { name: /raw trace/i }));
    expect(
      within(workbench).queryByRole("heading", { name: "Verdict" })
    ).not.toBeInTheDocument();

    fireEvent.click(within(workbench).getByRole("button", { name: /payload summary/i }));
    expect(within(workbench).getByText("Selection source")).toBeInTheDocument();
    expect(within(workbench).getByText("Persistence outcome")).toBeInTheDocument();
    expect(within(workbench).getByText("Attempted provider")).toBeInTheDocument();
    expect(within(workbench).getByText("Attempted model")).toBeInTheDocument();

    fireEvent.click(within(workbench).getByRole("button", { name: /task-bravo/i }));
    expect(within(workbench).getByText("Selected: task-bravo")).toBeInTheDocument();
    expect(within(workbench).getByText(/trace: unavailable/i)).toBeInTheDocument();

    const console = screen.getByTestId("command-center-event-console");
    expect(within(console).getByText("Event console")).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /pause/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /clear/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /wrap/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /auto-scroll/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /copy visible/i })).toBeInTheDocument();
    expect(within(console).getByText("No classification yet")).toBeInTheDocument();
  });

  it("renders retrieval posture section for active thread with status ok", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Ensure task-alpha is selected (click it if not already selected)
    const taskAlphaButton = within(workbench).queryByRole("button", { name: /task-alpha/i });
    if (taskAlphaButton) {
      fireEvent.click(taskAlphaButton);
    }

    // Retrieval posture section should be present for threadId 42
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/boundary: active_conversation_only/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/override: conversation/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/widen: none/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/conversation-only/i)).toBeInTheDocument();
  });

  it("renders empty state for retrieval posture when status is empty", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Select task-bravo (threadId 84) which returns status=empty
    fireEvent.click(within(workbench).getByRole("button", { name: /task-bravo/i }));
    expect(within(workbench).getByText("Selected: task-bravo")).toBeInTheDocument();

    // Retrieval posture section should show empty state
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/no retrieval posture evidence/i)).toBeInTheDocument();
  });
});
