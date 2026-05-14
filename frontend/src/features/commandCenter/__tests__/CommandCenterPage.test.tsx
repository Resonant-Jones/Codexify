import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import CommandCenterPage from "../CommandCenterPage";
import {
  classifyRetrievalPostureTrend,
  RetrievalPosturePanel,
  RetrievalPostureSummaryRow,
  type PinnedRetrievalPostureState,
  type RetrievalPostureHistoryFilter,
  type RetrievalPostureHistoryWindowSize,
} from "../components/TraceWorkbench";
import { describeRuntimeStatusPresentation } from "@/contracts/runtimeTokens";

import type {
  CommandCenterEvent,
  CommandCenterHealthItem,
  CommandCenterRagTracePayload,
  CommandCenterRetrievalPostureHistoryItem,
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
const mockClipboardWriteText = vi.fn();

function expectedConversationAuditNote(): string {
  return [
    "Retrieval posture",
    "- source_mode: conversation",
    "- boundary_label: active_conversation_only",
    "- retrieval_override_mode: conversation",
    "- widen_reason: none",
    "- conversation_only: true",
    "",
    "Summary",
    "- This run stayed inside the active conversation.",
    "- Evidence was constrained to the active conversation.",
    "- No widening occurred.",
  ].join("\n");
}

function expectedConversationPostureJson(): string {
  return JSON.stringify(
    {
      source_mode: "conversation",
      boundary_label: "active_conversation_only",
      retrieval_override_mode: "conversation",
      widen_reason: "none",
      conversation_only: true,
    },
    null,
    2
  );
}

function expectedConversationPostureBundle(): string {
  return [
    "Retrieval posture JSON",
    expectedConversationPostureJson(),
    "",
    "Audit note",
    expectedConversationAuditNote(),
  ].join("\n");
}

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
  graph: [],
};
let mockedTracePayloadForTaskAlpha: CommandCenterRagTracePayload | null =
  mockedTracePayload;

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
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-charlie",
    lastEvent: makeEvent({
      eventId: "evt-5",
      json: { thread_id: 100, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":100,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:00Z"),
      runId: "run-charlie",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-charlie",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 100,
      turnId: "turn-charlie",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:00Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-charlie",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-charlie",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 100,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-charlie",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-delta",
    lastEvent: makeEvent({
      eventId: "evt-6",
      json: { thread_id: 200, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":200,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:05Z"),
      runId: "run-delta",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-delta",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 200,
      turnId: "turn-delta",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:05Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-delta",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-delta",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 200,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-delta",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-echo",
    lastEvent: makeEvent({
      eventId: "evt-7",
      json: { thread_id: 300, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":300,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:10Z"),
      runId: "run-echo",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-echo",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 300,
      turnId: "turn-echo",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:10Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-echo",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-echo",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 300,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-echo",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-foxtrot",
    lastEvent: makeEvent({
      eventId: "evt-8",
      json: { thread_id: 400, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":400,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:15Z"),
      runId: "run-foxtrot",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-foxtrot",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 400,
      turnId: "turn-foxtrot",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:15Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-foxtrot",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-foxtrot",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 400,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-foxtrot",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-golf",
    lastEvent: makeEvent({
      eventId: "evt-9",
      json: { thread_id: 500, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":500,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:20Z"),
      runId: "run-golf",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-golf",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 500,
      turnId: "turn-golf",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:20Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-golf",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-golf",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 500,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-golf",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-hotel",
    lastEvent: makeEvent({
      eventId: "evt-10",
      json: { thread_id: 600, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":600,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:25Z"),
      runId: "run-hotel",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-hotel",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 600,
      turnId: "turn-hotel",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:25Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-hotel",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-hotel",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 600,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-hotel",
  },
  {
    eventCount: 1,
    identityKind: "task",
    key: "task-india",
    lastEvent: makeEvent({
      eventId: "evt-11",
      json: { thread_id: 700, type: "chat.completion" },
      kind: null,
      raw: '{"thread_id":700,"type":"chat.completion"}',
      receivedAt: Date.parse("2026-04-01T15:59:30Z"),
      runId: "run-india",
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: "task-india",
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId: 700,
      turnId: "turn-india",
      type: "task.completed",
    }),
    lastEventAt: Date.parse("2026-04-01T15:59:30Z"),
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: "run-india",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: "task-india",
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId: 700,
    traceEvidence: null,
    traceUrl: null,
    turnId: "turn-india",
  },
];

const mockedComparisonRuns: CommandCenterRun[] = [
  makeComparisonRun({
    eventId: "evt-12",
    key: "task-source-mode",
    receivedAt: "2026-04-01T15:57:00Z",
    threadId: 800,
  }),
  makeComparisonRun({
    eventId: "evt-13",
    key: "task-boundary-label",
    receivedAt: "2026-04-01T15:56:50Z",
    threadId: 810,
  }),
  makeComparisonRun({
    eventId: "evt-14",
    key: "task-override-mode",
    receivedAt: "2026-04-01T15:56:40Z",
    threadId: 820,
  }),
  makeComparisonRun({
    eventId: "evt-15",
    key: "task-widen-reason",
    receivedAt: "2026-04-01T15:56:30Z",
    threadId: 830,
  }),
  makeComparisonRun({
    eventId: "evt-16",
    key: "task-conversation-only",
    receivedAt: "2026-04-01T15:56:20Z",
    threadId: 840,
  }),
  makeComparisonRun({
    eventId: "evt-17",
    key: "task-multi-change",
    receivedAt: "2026-04-01T15:56:10Z",
    threadId: 850,
  }),
  makeComparisonRun({
    eventId: "evt-18",
    key: "task-unsupported-change",
    receivedAt: "2026-04-01T15:56:00Z",
    threadId: 860,
  }),
  makeComparisonRun({
    eventId: "evt-19",
    key: "task-unchanged",
    receivedAt: "2026-04-01T15:55:50Z",
    threadId: 870,
  }),
];

const allMockedRuns = [...mockedRuns, ...mockedComparisonRuns];

vi.mock("../hooks/useCommandCenterEvents", () => ({
  default: () => ({
    connectionDetail: "Listening to /api/events",
    connectionState: "open",
    events: mockedEvents,
    lastEventAt: Date.parse("2026-04-01T15:58:45Z"),
    runs: allMockedRuns,
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
        trace: mockedTracePayloadForTaskAlpha,
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

const mockedProjectPosture: CommandCenterRetrievalPosture = {
  source_mode: "project",
  boundary_label: "same_user_same_project",
  retrieval_override_mode: null,
  widen_reason: "insufficient_thread_hits",
  conversation_only: false,
};

const mockedPersonalKnowledgePosture: CommandCenterRetrievalPosture = {
  source_mode: "personal_knowledge",
  boundary_label: "same_user_only",
  retrieval_override_mode: null,
  widen_reason: "explicit_personal_knowledge",
  conversation_only: false,
};

const mockedUnknownPosture: CommandCenterRetrievalPosture = {
  source_mode: "unknown_mode",
  boundary_label: "unknown_boundary",
  retrieval_override_mode: null,
  widen_reason: "unknown_reason",
  conversation_only: false,
};

const mockedPartialPosture = {
  source_mode: "conversation",
  retrieval_override_mode: null,
  widen_reason: "none",
  conversation_only: true,
} as unknown as CommandCenterRetrievalPosture;

type RetrievalPostureHistoryHookState = {
  error: string | null;
  items: CommandCenterRetrievalPostureHistoryItem[];
  loading: boolean;
  status: "ok" | "empty" | "error" | null;
};

function makeHistoryItem(
  taskId: string,
  createdAt: string,
  retrievalPosture: CommandCenterRetrievalPosture
): CommandCenterRetrievalPostureHistoryItem {
  return {
    created_at: createdAt,
    retrieval_posture: retrievalPosture,
    task_id: taskId,
  };
}

const defaultThread42HistoryItems: CommandCenterRetrievalPostureHistoryItem[] = [
  makeHistoryItem("task-alpha", "2026-04-01T15:58:45Z", mockedRetrievalPosture),
  makeHistoryItem("task-bravo", "2026-04-01T15:58:30Z", mockedProjectPosture),
  makeHistoryItem("task-charlie", "2026-04-01T15:58:15Z", mockedPersonalKnowledgePosture),
];

let thread42HistoryItems = [...defaultThread42HistoryItems];

const mockedRetrievalPostureHistoryStateByThreadId: Record<
  number,
  RetrievalPostureHistoryHookState
> = {
  84: {
    error: null,
    items: [],
    loading: false,
    status: "empty",
  },
  500: {
    error: null,
    items: [],
    loading: true,
    status: null,
  },
  600: {
    error: "Retrieval posture history unavailable",
    items: [],
    loading: false,
    status: "error",
  },
  700: {
    error: null,
    items: [],
    loading: false,
    status: "empty",
  },
};

function setThread42HistoryItems(items: CommandCenterRetrievalPostureHistoryItem[]): void {
  thread42HistoryItems = items.slice();
}

/**
 * Renders CommandCenterPage and navigates to the Observability lens,
 * then selects the task-alpha run.
 */
function renderObservabilityLensWithTaskAlpha(): {
  workbench: HTMLElement;
  threadPanel: HTMLElement;
  historyPanel: HTMLElement;
} {
  render(<CommandCenterPage enabled />);

  // Navigate to Observability lens
  fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));

  const workbench = screen.getByTestId("command-center-trace-workbench");
  fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

  const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
  const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");

  return { workbench, threadPanel, historyPanel };
}

function resolveMockedRetrievalPostureHistory(
  threadId: number | null
): RetrievalPostureHistoryHookState {
  if (threadId === null) {
    return {
      error: null,
      items: [],
      loading: false,
      status: null,
    };
  }

  if (threadId === 42) {
    return {
      error: null,
      items: thread42HistoryItems,
      loading: false,
      status: "ok",
    };
  }

  return mockedRetrievalPostureHistoryStateByThreadId[threadId] ?? {
    error: null,
    items: [],
    loading: false,
    status: null,
  };
}

function RetrievalPostureHistoryHarness({
  threadId,
}: {
  threadId: number | null;
}) {
  const [historyFilter, setHistoryFilter] =
    React.useState<RetrievalPostureHistoryFilter>("all");
  const [historyWindowSize, setHistoryWindowSize] =
    React.useState<RetrievalPostureHistoryWindowSize>(5);

  return (
    <RetrievalPosturePanel
      compact
      historyFilter={historyFilter}
      historyWindowSize={historyWindowSize}
      onHistoryFilterChange={setHistoryFilter}
      onHistoryWindowSizeChange={setHistoryWindowSize}
      showComparisonStrip
      showHistorySection
      showTrendBadge
      testId="trend-panel"
      threadId={threadId}
      title="Thread retrieval posture"
    />
  );
}

async function switchHistoryThread(
  rerender: (ui: React.ReactElement) => void,
  threadId: number,
  expectedText: RegExp
): Promise<void> {
  rerender(<RetrievalPostureHistoryHarness threadId={threadId} />);
  const threadPanel = screen.getByTestId("trend-panel");
  await waitFor(() =>
    expect(within(threadPanel).getByText(expectedText)).toBeInTheDocument()
  );
}

const mockedRetrievalPostureSequences = new Map<
  number,
  CommandCenterRetrievalPosture[]
>();
const mockedRetrievalPostureNextIndices = new Map<number, number>();
const mockedRetrievalPostureCurrentIndices = new Map<number, number>();
let mockedRetrievalPostureLastThreadId: number | null = null;

function setRetrievalPostureSequence(
  threadId: number,
  sequence: CommandCenterRetrievalPosture[]
): void {
  mockedRetrievalPostureSequences.set(threadId, sequence);
  mockedRetrievalPostureNextIndices.delete(threadId);
  mockedRetrievalPostureCurrentIndices.delete(threadId);
  mockedRetrievalPostureLastThreadId = null;
}

function clearRetrievalPostureSequences(): void {
  mockedRetrievalPostureSequences.clear();
  mockedRetrievalPostureNextIndices.clear();
  mockedRetrievalPostureCurrentIndices.clear();
  mockedRetrievalPostureLastThreadId = null;
}

function resolveMockedRetrievalPosture(
  threadId: number | null
): CommandCenterRetrievalPosture | null {
  if (threadId === null) return null;

  const previousThreadId = mockedRetrievalPostureLastThreadId;
  mockedRetrievalPostureLastThreadId = threadId;

  const sequence = mockedRetrievalPostureSequences.get(threadId);
  if (!sequence || sequence.length === 0) {
    if (threadId === 42) return mockedRetrievalPosture;
    return null;
  }

  if (threadId !== previousThreadId) {
    const nextIndex = mockedRetrievalPostureNextIndices.get(threadId) ?? 0;
    const boundedIndex = Math.min(nextIndex, sequence.length - 1);
    mockedRetrievalPostureCurrentIndices.set(threadId, boundedIndex);
    mockedRetrievalPostureNextIndices.set(threadId, boundedIndex + 1);
  }

  const currentIndex = mockedRetrievalPostureCurrentIndices.get(threadId) ?? 0;
  return sequence[Math.min(currentIndex, sequence.length - 1)] ?? null;
}

function makeComparisonRun({
  eventId,
  key,
  receivedAt,
  threadId,
}: {
  eventId: string;
  key: string;
  receivedAt: string;
  threadId: number;
}): CommandCenterRun {
  const timestamp = Date.parse(receivedAt);

  return {
    eventCount: 1,
    identityKind: "task",
    key,
    lastEvent: makeEvent({
      eventId,
      json: { thread_id: threadId, type: "chat.completion" },
      kind: null,
      raw: `{"thread_id":${threadId},"type":"chat.completion"}`,
      receivedAt: timestamp,
      runId: `run-${key}`,
      sseType: "task.completed",
      state: "completed",
      status: null,
      summary: "chat completion completed",
      taskId: key,
      taskType: "chat.completion",
      terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
      threadId,
      turnId: `turn-${key}`,
      type: "task.completed",
    }),
    lastEventAt: timestamp,
    lastKind: null,
    lastType: "task.completed",
    requestId: null,
    runId: `run-${key}`,
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: COMMAND_CENTER_RUN_STATUSES.COMPLETED,
    summary: "chat completion · completed",
    taskId: key,
    terminalOutcome: COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED,
    threadId,
    traceEvidence: null,
    traceUrl: null,
    turnId: `turn-${key}`,
  };
}

vi.mock("../hooks/useRetrievalPosture", () => ({
  default: (threadId: number | null) => {
    const sequencePosture = resolveMockedRetrievalPosture(threadId);
    if (sequencePosture) {
      return {
        error: null,
        loading: false,
        retrievalPosture: sequencePosture,
        status: "ok",
      };
    }

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
    if (threadId === 100) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedProjectPosture,
        status: "ok",
      };
    }
    if (threadId === 200) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedPersonalKnowledgePosture,
        status: "ok",
      };
    }
    if (threadId === 300) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedUnknownPosture,
        status: "ok",
      };
    }
    if (threadId === 400) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedPartialPosture,
        status: "ok",
      };
    }
    if (threadId === 500) {
      return {
        error: null,
        loading: true,
        retrievalPosture: null,
        status: null,
      };
    }
    if (threadId === 600) {
      return {
        error: "Retrieval posture unavailable",
        loading: false,
        retrievalPosture: null,
        status: null,
      };
    }
    if (threadId === 700) {
      return {
        error: null,
        loading: false,
        retrievalPosture: null,
        status: "empty",
      };
    }
    if (threadId === 800) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "project",
          boundary_label: "active_conversation_only",
          retrieval_override_mode: "conversation",
          widen_reason: "none",
          conversation_only: true,
        },
        status: "ok",
      };
    }
    if (threadId === 810) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "conversation",
          boundary_label: "same_user_same_project",
          retrieval_override_mode: "conversation",
          widen_reason: "none",
          conversation_only: true,
        },
        status: "ok",
      };
    }
    if (threadId === 820) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "conversation",
          boundary_label: "active_conversation_only",
          retrieval_override_mode: null,
          widen_reason: "none",
          conversation_only: true,
        },
        status: "ok",
      };
    }
    if (threadId === 830) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "conversation",
          boundary_label: "active_conversation_only",
          retrieval_override_mode: "conversation",
          widen_reason: "insufficient_thread_hits",
          conversation_only: true,
        },
        status: "ok",
      };
    }
    if (threadId === 840) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "conversation",
          boundary_label: "active_conversation_only",
          retrieval_override_mode: "conversation",
          widen_reason: "none",
          conversation_only: false,
        },
        status: "ok",
      };
    }
    if (threadId === 850) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "project",
          boundary_label: "active_conversation_only",
          retrieval_override_mode: "conversation",
          widen_reason: "insufficient_thread_hits",
          conversation_only: true,
        },
        status: "ok",
      };
    }
    if (threadId === 860) {
      return {
        error: null,
        loading: false,
        retrievalPosture: {
          source_mode: "project",
          boundary_label: "same_user_same_project",
          retrieval_override_mode: null,
          widen_reason: "insufficient_thread_hits",
          conversation_only: false,
        },
        status: "ok",
      };
    }
    if (threadId === 870) {
      return {
        error: null,
        loading: false,
        retrievalPosture: mockedRetrievalPosture,
        status: "ok",
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

vi.mock("../hooks/useRetrievalPostureHistory", () => ({
  default: (threadId: number | null) => {
    return resolveMockedRetrievalPostureHistory(threadId);
  },
}));

beforeEach(() => {
  mockRefresh.mockClear();
  clearRetrievalPostureSequences();
  mockedTracePayloadForTaskAlpha = mockedTracePayload;
  mockClipboardWriteText.mockReset();
  setThread42HistoryItems(defaultThread42HistoryItems);
  Object.defineProperty(navigator, "clipboard", {
    configurable: true,
    value: {
      writeText: mockClipboardWriteText,
    },
  });
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

  it("renders the shell with Agent Command as default lens", () => {
    render(<CommandCenterPage enabled />);

    const scrollShell = screen.getByTestId("command-center-scroll-shell");
    expect(scrollShell).toHaveClass("min-h-screen", "overflow-y-auto");

    expect(screen.getByTestId("command-center-shell")).toBeInTheDocument();

    const agentBtn = screen.getByTestId("command-center-rail-item-agent-command");
    expect(agentBtn).toHaveAttribute("aria-current", "true");

    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coding-work-order-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("coding-orchestrator-recommendations")).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Automated Worker Control Plane" })
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        /Dispatch, lease allocation, merge automation, and worker launch are not enabled/i
      )
    ).toBeInTheDocument();
  }, 15000);

  it("renders retrieval posture history rows without runtime formatter errors", () => {
    render(
      <RetrievalPostureSummaryRow
        createdAt="2026-04-01T15:58:45Z"
        posture={mockedRetrievalPosture}
        taskId="task-alpha"
      />
    );

    const row = screen.getByTestId("command-center-retrieval-posture-history-item");
    expect(row).toBeInTheDocument();
    expect(within(row).getByText("Task: task-alpha")).toBeInTheDocument();
  });

  it("keeps worker-control panel visible in Agent Command lens", () => {
    render(<CommandCenterPage enabled />);

    expect(screen.getByTestId("coding-work-orders-panel")).toBeInTheDocument();
    expect(screen.getByTestId("coding-work-order-create-form")).toBeInTheDocument();
    expect(
      screen.getByTestId("coding-orchestrator-recommendations")
    ).toBeInTheDocument();
    expect(screen.queryByTestId("command-center-trace-workbench")).not.toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /dispatch/i })
    ).not.toBeInTheDocument();
  });

  it("switching to Observability displays trace workbench", () => {
    render(<CommandCenterPage enabled />);

    fireEvent.click(screen.getByTestId("command-center-rail-item-observability"));

    expect(screen.getByTestId("command-center-trace-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-thread-posture-panel")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-retrieval-posture-history-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("coding-work-orders-panel")).not.toBeInTheDocument();
  });

  it("switching to Runtime Health displays health overview", () => {
    render(<CommandCenterPage enabled />);

    fireEvent.click(screen.getByTestId("command-center-rail-item-runtime-health"));

    expect(screen.getByText("Core")).toBeInTheDocument();
    expect(screen.getByText("LLM")).toBeInTheDocument();
  });

  it("Deep Settings displays placeholder copy", () => {
    render(<CommandCenterPage enabled />);

    fireEvent.click(screen.getByTestId("command-center-rail-item-deep-settings"));

    expect(screen.getByText("Deep Settings")).toBeInTheDocument();
    expect(
      screen.getByText(/No backend configuration behavior is implemented through this panel/)
    ).toBeInTheDocument();
  });

  it("Extensions displays placeholder copy", () => {
    render(<CommandCenterPage enabled />);

    fireEvent.click(screen.getByTestId("command-center-rail-item-extensions"));

    expect(screen.getByText("Extensions")).toBeInTheDocument();
    expect(
      screen.getByText(/This lens is a future\/governed placeholder/)
    ).toBeInTheDocument();
  });

  it("bottom drawer opens and closes", () => {
    render(<CommandCenterPage enabled />);

    const drawer = screen.getByTestId("command-center-bottom-drawer");
    expect(drawer.style.height).toBe("0px");

    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));
    expect(drawer.style.height).not.toBe("0px");

    fireEvent.click(screen.getByTestId("command-center-drawer-close"));
    expect(drawer.style.height).toBe("0px");
  });

  it("Terminal drawer tab is non-executable", () => {
    render(<CommandCenterPage enabled />);

    fireEvent.click(screen.getByTestId("command-center-rail-drawer-toggle"));

    expect(
      screen.getByText(/Terminal execution is not enabled in this Command Center build/)
    ).toBeInTheDocument();
    expect(
      screen.getByText(/input disabled — terminal is non-executable/)
    ).toBeInTheDocument();
  });

  it("no dispatch button exists", () => {
    render(<CommandCenterPage enabled />);

    expect(
      screen.queryByRole("button", { name: /dispatch/i })
    ).not.toBeInTheDocument();
  });

  // Retrieval posture history + explainer tests — go through Observability lens
  it("shows a generic fallback when the newest two history items differ in an unsupported combination", () => {
    setThread42HistoryItems([
      makeHistoryItem("task-newest", "2026-04-01T15:59:30Z", mockedRetrievalPosture),
      makeHistoryItem("task-previous", "2026-04-01T15:58:30Z", mockedProjectPosture),
    ]);

    const { historyPanel } = renderObservabilityLensWithTaskAlpha();

    expect(within(historyPanel).getByText("Posture changed since previous run")).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(
        /Changed: source_mode, boundary_label, retrieval_override_mode, widen_reason, conversation_only/i
      )
    ).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(
        /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
      )
    ).toBeInTheDocument();

    const historyItems = within(historyPanel).getAllByTestId(
      "command-center-retrieval-posture-history-item"
    );
    expect(historyItems).toHaveLength(2);
    expect(historyItems[0]).toHaveTextContent(/task-newest/i);
    expect(historyItems[1]).toHaveTextContent(/task-previous/i);
  });

  it.each([
    [
      "source_mode",
      { source_mode: "project" as const },
      "The retrieval scope changed.",
    ],
    [
      "boundary_label",
      { boundary_label: "same_user_same_project" as const },
      "The retrieval boundary changed.",
    ],
    [
      "retrieval_override_mode",
      { retrieval_override_mode: null as const },
      "An explicit retrieval override changed the posture.",
    ],
    [
      "widen_reason",
      { widen_reason: "insufficient_thread_hits" as const },
      "The reason for widening changed.",
    ],
    [
      "conversation_only",
      { conversation_only: false as const },
      "Conversation-only retrieval changed.",
    ],
  ] as const)(
    "shows a bounded explanation when %s changes",
    (field, patch, expectedLine) => {
      setThread42HistoryItems([
        makeHistoryItem(
          "task-newest",
          "2026-04-01T15:59:30Z",
          {
            ...mockedRetrievalPosture,
            ...patch,
          } as CommandCenterRetrievalPosture
        ),
        makeHistoryItem("task-previous", "2026-04-01T15:58:30Z", mockedRetrievalPosture),
      ]);

      const { historyPanel } = renderObservabilityLensWithTaskAlpha();

      expect(within(historyPanel).getByText("Posture changed since previous run")).toBeInTheDocument();
      expect(within(historyPanel).getByText(`Changed: ${field}`)).toBeInTheDocument();
      expect(within(historyPanel).getByText(expectedLine)).toBeInTheDocument();
      expect(
        within(historyPanel).queryByText(
          /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
        )
      ).not.toBeInTheDocument();
    }
  );

  it("shows multiple bounded explanation lines when multiple fields change", () => {
    setThread42HistoryItems([
      makeHistoryItem(
        "task-newest",
        "2026-04-01T15:59:30Z",
        {
          ...mockedRetrievalPosture,
          source_mode: "project",
          widen_reason: "insufficient_thread_hits",
        } as CommandCenterRetrievalPosture
      ),
      makeHistoryItem("task-previous", "2026-04-01T15:58:30Z", mockedRetrievalPosture),
    ]);

    const { historyPanel } = renderObservabilityLensWithTaskAlpha();

    expect(within(historyPanel).getByText("Posture changed since previous run")).toBeInTheDocument();
    expect(within(historyPanel).getByText("Changed: source_mode, widen_reason")).toBeInTheDocument();
    expect(within(historyPanel).getByText("The retrieval scope changed.")).toBeInTheDocument();
    expect(within(historyPanel).getByText("The reason for widening changed.")).toBeInTheDocument();
    expect(
      within(historyPanel).queryByText(
        /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
      )
    ).not.toBeInTheDocument();
  });

  it("shows that retrieval posture is unchanged when the newest two history items match", () => {
    setThread42HistoryItems([
      makeHistoryItem("task-newest", "2026-04-01T15:59:30Z", mockedRetrievalPosture),
      makeHistoryItem("task-previous", "2026-04-01T15:58:30Z", mockedRetrievalPosture),
      makeHistoryItem("task-older", "2026-04-01T15:57:30Z", mockedProjectPosture),
    ]);

    const { historyPanel } = renderObservabilityLensWithTaskAlpha();
    expect(within(historyPanel).getByText("Posture unchanged since previous run")).toBeInTheDocument();
    expect(
      within(historyPanel).queryByText(/^Changed:/i)
    ).not.toBeInTheDocument();
    expect(
      within(historyPanel).queryByText(
        /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
      )
    ).not.toBeInTheDocument();
    expect(within(historyPanel).queryByText("The retrieval scope changed.")).not.toBeInTheDocument();

    const historyItems = within(historyPanel).getAllByTestId(
      "command-center-retrieval-posture-history-item"
    );
    expect(historyItems).toHaveLength(3);
    expect(historyItems[0]).toHaveTextContent(/task-newest/i);
    expect(historyItems[1]).toHaveTextContent(/task-previous/i);
    expect(historyItems[2]).toHaveTextContent(/task-older/i);
  });

  it("classifies a flapping posture trend when recent items alternate repeatedly", () => {
    expect(
      classifyRetrievalPostureTrend([
        { retrieval_posture: mockedRetrievalPosture },
        { retrieval_posture: mockedProjectPosture },
        { retrieval_posture: mockedRetrievalPosture },
        { retrieval_posture: mockedProjectPosture },
      ])
    ).toBe("flapping");
  });
});
