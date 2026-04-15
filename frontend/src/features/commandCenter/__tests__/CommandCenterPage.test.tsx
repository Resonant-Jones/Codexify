import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

import CommandCenterPage from "../CommandCenterPage";
import {
  classifyRetrievalPostureTrend,
  RetrievalPosturePanel,
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

function renderActiveThreadHistoryPanel(): HTMLElement {
  render(<CommandCenterPage enabled />);

  const workbench = screen.getByTestId("command-center-trace-workbench");
  fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

  return screen.getByTestId("command-center-retrieval-posture-history-panel");
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

  it("renders the dashboard surface with bounded diagnostics and raw telemetry", () => {
    render(<CommandCenterPage enabled />);

    const root = screen.getByTestId("command-center-root");
    expect(root).toHaveClass("flex", "min-h-0", "flex-1", "flex-col", "overflow-hidden");

    expect(
      screen.getByRole("heading", { name: /agent command center/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Runtime summary")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-health-overview")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-trace-workbench")).toBeInTheDocument();
    expect(screen.getByTestId("command-center-event-console")).toBeInTheDocument();
    expect(
      screen.getByTestId("command-center-retrieval-posture-history-panel")
    ).toBeInTheDocument();

    expect(screen.getAllByLabelText(/transport state open/i)).toHaveLength(2);
    expect(screen.getAllByText(/last event: .*2026/i)).toHaveLength(2);
    expect(screen.getByLabelText(/unknown items 2/i)).toBeInTheDocument();

    const healthOverview = screen.getByTestId("command-center-health-overview");
    expect(within(healthOverview).getByText("Core")).toBeInTheDocument();
    expect(within(healthOverview).getByText("LLM")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Deps")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Vector")).toBeInTheDocument();
    expect(within(healthOverview).getByText("Memory")).toBeInTheDocument();

    const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");
    expect(within(historyPanel).getByText("Recent retrieval posture")).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(
        /Newest-first thread history from completed debug evidence only\./i
      )
    ).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(
        /no recent retrieval posture history for this thread/i
      )
    ).toBeInTheDocument();

    fireEvent.click(within(healthOverview).getByRole("button", { name: /core/i }));
    expect(screen.getByText("Health detail: Core")).toBeInTheDocument();
    expect(screen.getByText("Parsed health detail")).toBeInTheDocument();
    expect(screen.getByText("Raw response")).toBeInTheDocument();

    const workbench = screen.getByTestId("command-center-trace-workbench");
    expect(workbench).toHaveClass("flex", "h-full", "min-h-0", "flex-col", "overflow-hidden");
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

    const listPane = within(workbench).getByTestId("command-center-trace-list-pane");
    const listScroll = within(workbench).getByTestId("command-center-trace-list-scroll");
    const viewerPane = within(workbench).getByTestId("command-center-trace-viewer-pane");
    const viewerScroll = within(workbench).getByTestId("command-center-trace-viewer-scroll");
    expect(listPane).toHaveClass("overflow-hidden", "min-h-0", "flex", "flex-col");
    expect(listScroll).toHaveClass("overflow-auto", "min-h-0", "flex-1");
    expect(viewerPane).toHaveClass("overflow-hidden", "min-h-0", "flex", "flex-col");
    expect(viewerScroll).toHaveClass("overflow-auto", "min-h-0", "flex-1");

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
    expect(
      within(historyPanel).getByText(/no recent retrieval posture history for this thread/i)
    ).toBeInTheDocument();

    const console = screen.getByTestId("command-center-event-console");
    expect(within(console).getByText("Event console")).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /pause/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /clear/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /wrap/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /auto-scroll/i })).toBeInTheDocument();
    expect(within(console).getByRole("button", { name: /copy visible/i })).toBeInTheDocument();
    expect(within(console).getByText("No classification yet")).toBeInTheDocument();
  });

  it("shows a generic fallback when the newest two history items differ in an unsupported combination", () => {
    setThread42HistoryItems([
      makeHistoryItem("task-newest", "2026-04-01T15:59:30Z", mockedRetrievalPosture),
      makeHistoryItem("task-previous", "2026-04-01T15:58:30Z", mockedProjectPosture),
    ]);

    const historyPanel = renderActiveThreadHistoryPanel();

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
    (
      field,
      patch,
      expectedLine
    ) => {
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

      const historyPanel = renderActiveThreadHistoryPanel();

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

    const historyPanel = renderActiveThreadHistoryPanel();

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

    const historyPanel = renderActiveThreadHistoryPanel();
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

  it("shows that no previous comparison is available when only one history item exists", () => {
    setThread42HistoryItems([
      makeHistoryItem("task-newest", "2026-04-01T15:59:30Z", mockedRetrievalPosture),
    ]);

    const historyPanel = renderActiveThreadHistoryPanel();
    expect(within(historyPanel).getByText("No previous posture to compare")).toBeInTheDocument();
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
    expect(historyItems).toHaveLength(1);
    expect(historyItems[0]).toHaveTextContent(/task-newest/i);
  });

  it("renders the standalone thread posture panel and updates with the selected thread", async () => {
    render(<CommandCenterPage enabled />);

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/no retrieval posture evidence for this thread/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /^copy posture$/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture bundle/i })
    ).not.toBeInTheDocument();

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");
    const historyItems = within(historyPanel).getAllByTestId(
      "command-center-retrieval-posture-history-item"
    );
    expect(historyItems).toHaveLength(3);
    expect(historyItems[0]).toHaveTextContent(/task-alpha/i);
    expect(historyItems[0]).toHaveTextContent(/source: conversation/i);
    expect(historyItems[0]).toHaveTextContent(/boundary: active_conversation_only/i);
    expect(historyItems[0]).toHaveTextContent(/widen: none/i);
    expect(historyItems[0]).toHaveTextContent(/This run stayed inside the active conversation\./i);
    expect(historyItems[1]).toHaveTextContent(/task-bravo/i);
    expect(historyItems[1]).toHaveTextContent(/source: project/i);
    expect(historyItems[1]).toHaveTextContent(/widen: insufficient_thread_hits/i);
    expect(historyItems[2]).toHaveTextContent(/task-charlie/i);
    expect(historyItems[2]).toHaveTextContent(/source: personal_knowledge/i);
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

    expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/boundary: active_conversation_only/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/override: conversation/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/widen: none/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/^conversation-only$/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/This run stayed inside the active conversation\./i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/No widening occurred\./i)).toBeInTheDocument();
    expect(within(threadPanel).getByText("What these fields mean")).toBeInTheDocument();
    expect(within(threadPanel).getByText("source_mode")).toBeInTheDocument();
    expect(
      within(threadPanel).getByText(/Retrieval began inside the active conversation\./i)
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText("boundary_label")).toBeInTheDocument();
    expect(
      within(threadPanel).getByText(/Retrieval stayed inside the active conversation\./i)
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText("retrieval_override_mode")).toBeInTheDocument();
    expect(
      within(threadPanel).getByText(/Explicit command intent kept retrieval in conversation scope\./i)
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText("widen_reason")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/Retrieval did not widen\./i)).toBeInTheDocument();
    expect(within(threadPanel).getByText("Posture trend: Insufficient history")).toBeInTheDocument();
    expect(
      within(threadPanel).getByText(/Not enough completed posture history is available yet\./i)
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText("What these fields mean")).toBeInTheDocument();
    expect(within(threadPanel).getByRole("button", { name: /^copy posture$/i })).toBeInTheDocument();
    expect(within(threadPanel).getByRole("button", { name: /copy audit note/i })).toBeInTheDocument();
    expect(within(threadPanel).getByRole("button", { name: /copy posture bundle/i })).toBeInTheDocument();

    fireEvent.click(within(threadPanel).getByRole("button", { name: /^copy posture$/i }));

    expect(mockClipboardWriteText).toHaveBeenCalledWith(expectedConversationPostureJson());
    await waitFor(() => {
      expect(within(threadPanel).getByText(/^copied posture$/i)).toBeInTheDocument();
    });
  });

  it("pins the current posture locally and clears it with the pinned-panel action", async () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByRole("button", { name: /pin current posture/i })).toBeInTheDocument();

    fireEvent.click(within(threadPanel).getByRole("button", { name: /pin current posture/i }));

    const pinnedPanel = screen.getByTestId("command-center-pinned-retrieval-posture-panel");
    expect(pinnedPanel).toHaveClass("border-dashed");
    expect(within(pinnedPanel).getByText("Pinned posture")).toBeInTheDocument();
    expect(within(pinnedPanel).getByText("Pinned snapshot")).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/boundary: active_conversation_only/i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/override: conversation/i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/widen: none/i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/^conversation-only$/i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/This run stayed inside the active conversation\./i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByText(/No widening occurred\./i)).toBeInTheDocument();
    expect(within(pinnedPanel).getByRole("button", { name: /clear pin/i })).toBeInTheDocument();
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByRole("button", { name: /pin current posture/i })).toBeInTheDocument();

    fireEvent.click(within(pinnedPanel).getByRole("button", { name: /clear pin/i }));

    await waitFor(() => {
      expect(screen.queryByTestId("command-center-pinned-retrieval-posture-panel")).not.toBeInTheDocument();
    });
  });

  it("clears a pinned posture when the active thread changes", async () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /pin current posture/i }));

    expect(screen.getByTestId("command-center-pinned-retrieval-posture-panel")).toBeInTheDocument();

    fireEvent.click(within(workbench).getByRole("button", { name: /task-charlie/i }));

    await waitFor(() => {
      expect(screen.queryByTestId("command-center-pinned-retrieval-posture-panel")).not.toBeInTheDocument();
    });
  });
  it("copies a retrieval posture audit note", async () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /copy audit note/i }));

    expect(mockClipboardWriteText).toHaveBeenCalledWith(expectedConversationAuditNote());

    await waitFor(() => {
      expect(within(threadPanel).getByText(/copied audit note/i)).toBeInTheDocument();
    });
  });

  it("copies a retrieval posture bundle", async () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /^copy posture bundle$/i }));

    expect(mockClipboardWriteText).toHaveBeenCalledWith(expectedConversationPostureBundle());

    await waitFor(() => {
      expect(within(threadPanel).getByText(/copied posture bundle/i)).toBeInTheDocument();
    });
  });

  it("shows copy failure feedback when the clipboard write is rejected", async () => {
    mockClipboardWriteText.mockRejectedValueOnce(new Error("clipboard denied"));

    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /^copy posture$/i }));

    await waitFor(() => {
      expect(within(threadPanel).getByText(/^copy failed$/i)).toBeInTheDocument();
    });
  });

  it("shows audit note copy failure feedback when the clipboard write is rejected", async () => {
    mockClipboardWriteText.mockRejectedValueOnce(new Error("clipboard denied"));

    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /copy audit note/i }));

    await waitFor(() => {
      expect(within(threadPanel).getByText(/audit note copy failed/i)).toBeInTheDocument();
    });
  });

  it("shows posture bundle copy failure feedback when the clipboard write is rejected", async () => {
    mockClipboardWriteText.mockRejectedValueOnce(new Error("clipboard denied"));

    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /^copy posture bundle$/i }));

    await waitFor(() => {
      expect(within(threadPanel).getByText(/posture bundle copy failed/i)).toBeInTheDocument();
    });
  });

  it.each([
    [
      "source_mode",
      {
        boundary_label: "active_conversation_only",
        conversation_only: true,
        retrieval_override_mode: "conversation",
        source_mode: "project",
        widen_reason: "none",
      },
      "The retrieval scope changed.",
    ],
    [
      "boundary_label",
      {
        boundary_label: "same_user_same_project",
        conversation_only: true,
        retrieval_override_mode: "conversation",
        source_mode: "conversation",
        widen_reason: "none",
      },
      "The retrieval boundary changed.",
    ],
    [
      "retrieval_override_mode",
      {
        boundary_label: "active_conversation_only",
        conversation_only: true,
        retrieval_override_mode: null,
        source_mode: "conversation",
        widen_reason: "none",
      },
      "An explicit retrieval override changed the posture.",
    ],
    [
      "widen_reason",
      {
        boundary_label: "active_conversation_only",
        conversation_only: true,
        retrieval_override_mode: "conversation",
        source_mode: "conversation",
        widen_reason: "insufficient_thread_hits",
      },
      "The reason for widening changed.",
    ],
    [
      "conversation_only",
      {
        boundary_label: "active_conversation_only",
        conversation_only: false,
        retrieval_override_mode: "conversation",
        source_mode: "conversation",
        widen_reason: "none",
      },
      "Conversation-only retrieval changed.",
    ],
  ] as const)(
    "renders a bounded explanation when %s changes",
    async (field, nextPosture, expectedLine) => {
      setRetrievalPostureSequence(42, [mockedRetrievalPosture, nextPosture]);

      const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
      const threadPanel = screen.getByTestId("trend-panel");

      await waitFor(() =>
        expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
      );
      expect(within(threadPanel).getByText("No previous posture to compare")).toBeInTheDocument();

      await switchHistoryThread(rerender, 100, /source: project/i);
      await switchHistoryThread(
        rerender,
        42,
        field === "source_mode" ? /source: project/i : /source: conversation/i
      );

      await waitFor(() =>
        expect(within(threadPanel).getByText("Posture changed since previous run")).toBeInTheDocument()
      );

      expect(within(threadPanel).getByText(`Changed: ${field}`)).toBeInTheDocument();
      expect(within(threadPanel).getByText(expectedLine)).toBeInTheDocument();
      expect(
        within(threadPanel).queryByText(
          /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
        )
      ).not.toBeInTheDocument();
    }
  );

  it("renders multiple bounded explanation lines when multiple fields change", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      {
        ...mockedRetrievalPosture,
        source_mode: "project",
        widen_reason: "insufficient_thread_hits",
      },
    ]);

    const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
    const threadPanel = screen.getByTestId("trend-panel");

    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    expect(within(threadPanel).getByText("No previous posture to compare")).toBeInTheDocument();

    await switchHistoryThread(rerender, 100, /source: project/i);
    await switchHistoryThread(rerender, 42, /source: project/i);

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture changed since previous run")).toBeInTheDocument()
    );

    expect(within(threadPanel).getByText("Changed: source_mode, widen_reason")).toBeInTheDocument();
    expect(within(threadPanel).getByText("The retrieval scope changed.")).toBeInTheDocument();
    expect(within(threadPanel).getByText("The reason for widening changed.")).toBeInTheDocument();
    expect(
      within(threadPanel).queryByText(
        /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
      )
    ).not.toBeInTheDocument();
  });

  it("falls back when the changed-field combination is unsupported", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      {
        ...mockedRetrievalPosture,
        boundary_label: "same_user_same_project",
        source_mode: "project",
        widen_reason: "insufficient_thread_hits",
      },
    ]);

    const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
    const threadPanel = screen.getByTestId("trend-panel");

    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    expect(within(threadPanel).getByText("No previous posture to compare")).toBeInTheDocument();

    await switchHistoryThread(rerender, 100, /source: project/i);
    await switchHistoryThread(rerender, 42, /source: project/i);

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture changed since previous run")).toBeInTheDocument()
    );

    expect(
      within(threadPanel).getByText(
        "Changed: source_mode, boundary_label, widen_reason"
      )
    ).toBeInTheDocument();
    expect(
      within(threadPanel).getByText(
        /Retrieval posture changed, but this combination does not yet have a tailored explanation\./i
      )
    ).toBeInTheDocument();
    expect(within(threadPanel).queryByText("The retrieval scope changed.")).not.toBeInTheDocument();
    expect(within(threadPanel).queryByText("The retrieval boundary changed.")).not.toBeInTheDocument();
  });

  it("does not render the explainer for unchanged and no-previous states", async () => {
    setRetrievalPostureSequence(42, [mockedRetrievalPosture, mockedRetrievalPosture]);

    const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
    const threadPanel = screen.getByTestId("trend-panel");

    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    expect(within(threadPanel).getByText("No previous posture to compare")).toBeInTheDocument();
    expect(within(threadPanel).queryByText("Posture changed since previous run")).not.toBeInTheDocument();
    expect(within(threadPanel).queryByText(/^Changed:/i)).not.toBeInTheDocument();

    await switchHistoryThread(rerender, 100, /source: project/i);
    await switchHistoryThread(rerender, 42, /source: conversation/i);

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture unchanged since previous run")).toBeInTheDocument()
    );
    expect(within(threadPanel).queryByText(/^Changed:/i)).not.toBeInTheDocument();
    expect(within(threadPanel).queryByText("The retrieval scope changed.")).not.toBeInTheDocument();
  });

  it("renders a stable posture trend when the recent window repeats the same posture", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      mockedRetrievalPosture,
      mockedRetrievalPosture,
    ]);

    const { rerender } = render(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );

    const threadPanel = screen.getByTestId("trend-panel");
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={100}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={100}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture trend: Stable")).toBeInTheDocument()
    );
    expect(
      within(threadPanel).getByText(/Recent runs used the same retrieval posture\./i)
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument();
  });

  it("renders a stabilizing posture trend when the newest posture matches the previous run", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      mockedProjectPosture,
      mockedProjectPosture,
    ]);

    const { rerender } = render(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );

    const threadPanel = screen.getByTestId("trend-panel");
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={100}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={100}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );
    rerender(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument()
    );

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture trend: Stabilizing")).toBeInTheDocument()
    );
    expect(
      within(threadPanel).getByText(
        /The newest posture matches the previous run, but differs from older recent runs\./i
      )
    ).toBeInTheDocument();
    expect(within(threadPanel).getByText(/source: project/i)).toBeInTheDocument();
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

  it("renders an insufficient-history trend when fewer than two posture items are available", async () => {
    render(
      <RetrievalPosturePanel
        compact
        showComparisonStrip
        showTrendBadge
        testId="trend-panel"
        threadId={42}
        title="Thread retrieval posture"
      />
    );

    const threadPanel = screen.getByTestId("trend-panel");
    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture trend: Insufficient history")).toBeInTheDocument()
    );
    expect(
      within(threadPanel).getByText(/Not enough completed posture history is available yet\./i)
    ).toBeInTheDocument();
  });

  it("defaults to a five-entry window and preserves newest-first order when shrinking or expanding", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      mockedProjectPosture,
      mockedRetrievalPosture,
      mockedProjectPosture,
      mockedRetrievalPosture,
      mockedProjectPosture,
    ]);

    const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
    const threadPanel = screen.getByTestId("trend-panel");

    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );

    for (const expectedText of [
      /source: project/i,
      /source: conversation/i,
      /source: project/i,
      /source: conversation/i,
      /source: project/i,
    ] as const) {
      await switchHistoryThread(rerender, 100, /source: project/i);
      await switchHistoryThread(rerender, 42, expectedText);
    }

    expect(within(threadPanel).getByRole("button", { name: "5" })).toBeInTheDocument();
    expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(5);

    fireEvent.click(within(threadPanel).getByRole("button", { name: "3" }));

    await waitFor(() => expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(3));
    const threeItems = within(threadPanel).getAllByRole("listitem");
    expect(threeItems[0]).toHaveTextContent(/scope project/i);
    expect(threeItems[1]).toHaveTextContent(/scope conversation/i);
    expect(threeItems[2]).toHaveTextContent(/scope project/i);

    fireEvent.click(within(threadPanel).getByRole("button", { name: "10" }));

    await waitFor(() => expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(6));
  });

  it("keeps Changed only aligned with the bounded window and updates trend within the selected window", async () => {
    setRetrievalPostureSequence(42, [
      mockedRetrievalPosture,
      mockedProjectPosture,
      mockedProjectPosture,
      mockedProjectPosture,
      mockedRetrievalPosture,
    ]);

    const { rerender } = render(<RetrievalPostureHistoryHarness threadId={42} />);
    const threadPanel = screen.getByTestId("trend-panel");

    await waitFor(() =>
      expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument()
    );

    for (const expectedText of [
      /source: project/i,
      /source: project/i,
      /source: project/i,
      /source: conversation/i,
    ] as const) {
      await switchHistoryThread(rerender, 100, /source: project/i);
      await switchHistoryThread(rerender, 42, expectedText);
    }

    expect(within(threadPanel).getByText("Posture trend: Flapping")).toBeInTheDocument();
    expect(within(threadPanel).getByText("Posture changed since previous run")).toBeInTheDocument();
    expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(5);

    fireEvent.click(within(threadPanel).getByRole("button", { name: "Changed only" }));

    await waitFor(() => expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(2));
    expect(within(threadPanel).getByText(/scope project/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/scope conversation/i)).toBeInTheDocument();

    fireEvent.click(within(threadPanel).getByRole("button", { name: "3" }));

    await waitFor(() =>
      expect(within(threadPanel).getByText("Posture trend: Insufficient history")).toBeInTheDocument()
    );
    expect(within(threadPanel).getByText("Posture changed since previous run")).toBeInTheDocument();

    fireEvent.click(within(threadPanel).getByRole("button", { name: "Changed only" }));

    await waitFor(() => expect(within(threadPanel).getAllByRole("listitem")).toHaveLength(1));
    expect(within(threadPanel).getByText(/scope conversation/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByText(/No posture changes in the recent history window\./i)
    ).not.toBeInTheDocument();
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
    expect(
      within(screen.getByTestId("command-center-thread-posture-panel")).getByRole("button", {
        name: "All entries",
      })
    ).toBeInTheDocument();
    expect(within(workbench).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/boundary: active_conversation_only/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/override: conversation/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/widen: none/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/^conversation-only$/i)).toBeInTheDocument();

    // Verify explainer text is also present
    expect(within(workbench).getByText(/This run stayed inside the active conversation\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/No widening occurred\./i)).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /copy audit note/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /^copy posture bundle$/i })).toBeInTheDocument();
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
    expect(
      within(workbench).queryByRole("button", { name: /copy audit note/i })
    ).not.toBeInTheDocument();
    expect(
      within(workbench).queryByRole("button", { name: /^copy posture bundle$/i })
    ).not.toBeInTheDocument();
  });

  it("renders explainer for conversation-only posture", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Ensure task-alpha is selected (threadId 42, conversation-only posture)
    const taskAlphaButton = within(workbench).queryByRole("button", { name: /task-alpha/i });
    if (taskAlphaButton) {
      fireEvent.click(taskAlphaButton);
    }

    // Verify explainer text for conversation-only posture
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/This run stayed inside the active conversation\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/Evidence was constrained to the active conversation\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/No widening occurred\./i)).toBeInTheDocument();
  });

  it("renders explainer for project posture with widening", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Select task-charlie (threadId 100, project posture with widening)
    fireEvent.click(within(workbench).getByRole("button", { name: /task-charlie/i }));
    expect(within(workbench).getByText("Selected: task-charlie")).toBeInTheDocument();

    // Verify explainer text for project posture with widening
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/source: project/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/widen: insufficient_thread_hits/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/This run operated within the current project scope\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/This run widened within the current project when thread-local evidence was insufficient\./i)).toBeInTheDocument();
    expect(within(workbench).getByText("What these fields mean")).toBeInTheDocument();
    expect(
      within(workbench).getByText(/Retrieval began in the current project scope\./i)
    ).toBeInTheDocument();
    expect(within(workbench).getByText(/Retrieval could move within the current project\./i)).toBeInTheDocument();
    expect(
      within(workbench).getByText(/No explicit override was applied\./i)
    ).toBeInTheDocument();
    expect(
      within(workbench).getByText(/Thread-local evidence was thin, so retrieval widened within the project\./i)
    ).toBeInTheDocument();
  });

  it("renders explainer for personal knowledge posture", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Select task-delta (threadId 200, personal_knowledge posture)
    fireEvent.click(within(workbench).getByRole("button", { name: /task-delta/i }));
    expect(within(workbench).getByText("Selected: task-delta")).toBeInTheDocument();

    // Verify explainer text for personal knowledge posture
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/source: personal_knowledge/i)).toBeInTheDocument();
    expect(within(workbench).getByText(/This run was allowed to use the user's personal knowledge scope\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/This run was allowed to widen across the same user's knowledge scope\./i)).toBeInTheDocument();
    expect(within(workbench).getByText("What these fields mean")).toBeInTheDocument();
    expect(
      within(workbench).getByText(/Retrieval began in the same user's personal knowledge scope\./i)
    ).toBeInTheDocument();
    expect(
      within(workbench).getByText(/Retrieval could move within the same user's broader knowledge\./i)
    ).toBeInTheDocument();
    expect(
      within(workbench).getByText(/No explicit override was applied\./i)
    ).toBeInTheDocument();
    expect(
      within(workbench).getByText(/Explicit personal-knowledge intent allowed retrieval to widen\./i)
    ).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /^copy posture$/i })).toBeInTheDocument();
  });

  it("renders loading state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-golf/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/loading retrieval posture/i)).toBeInTheDocument();
    expect(within(historyPanel).getByText("Recent retrieval posture")).toBeInTheDocument();
    expect(within(historyPanel).getByText(/loading recent retrieval posture history/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /^copy posture$/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /pin current posture/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy audit note/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture bundle/i })
    ).not.toBeInTheDocument();
  });

  it("renders error state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-hotel/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/retrieval posture unavailable/i)).toBeInTheDocument();
    expect(within(historyPanel).getByText("Recent retrieval posture")).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(/retrieval posture history unavailable/i)
    ).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /^copy posture$/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /pin current posture/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy audit note/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture bundle/i })
    ).not.toBeInTheDocument();
  });

  it("renders empty state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-india/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    const historyPanel = screen.getByTestId("command-center-retrieval-posture-history-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/no retrieval posture evidence for this thread/i)).toBeInTheDocument();
    expect(within(historyPanel).getByText("Recent retrieval posture")).toBeInTheDocument();
    expect(
      within(historyPanel).getByText(/no recent retrieval posture history for this thread/i)
    ).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /^copy posture$/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /pin current posture/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy audit note/i })
    ).not.toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture bundle/i })
    ).not.toBeInTheDocument();
  });

  it("renders fallback explainer for unsupported posture values", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    // Select task-echo (threadId 300, unknown posture)
    fireEvent.click(within(workbench).getByRole("button", { name: /task-echo/i }));
    expect(within(workbench).getByText("Selected: task-echo")).toBeInTheDocument();

    // Verify fallback explainer text
    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/source: unknown_mode/i)).toBeInTheDocument();
    expect(within(workbench).getByText("What these fields mean")).toBeInTheDocument();
    expect(
      within(workbench).getByText(
        /Retrieval posture metadata is present, but this combination does not yet have a tailored explanation\./i
      )
    ).toBeInTheDocument();
    expect(
      within(workbench).getAllByText(
        /This token is present but does not yet have a tailored glossary entry\./i
      )
    ).toHaveLength(3);
    expect(within(workbench).getByRole("button", { name: /^copy posture$/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /copy audit note/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /copy posture bundle/i })).toBeInTheDocument();
  });

  it("renders fallback explainer for partially missing posture values", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");

    fireEvent.click(within(workbench).getByRole("button", { name: /task-foxtrot/i }));
    expect(within(workbench).getByText("Selected: task-foxtrot")).toBeInTheDocument();

    expect(within(workbench).getByText("Retrieval posture")).toBeInTheDocument();
    expect(within(workbench).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(workbench).getByText("What these fields mean")).toBeInTheDocument();
    expect(
      within(workbench).getByText(
        /Retrieval posture metadata is present, but this combination does not yet have a tailored explanation\./i
      )
    ).toBeInTheDocument();
    expect(
      within(workbench).getByText(/This token is present but does not yet have a tailored glossary entry\./i)
    ).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /^copy posture$/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /copy audit note/i })).toBeInTheDocument();
    expect(within(workbench).getByRole("button", { name: /copy posture bundle/i })).toBeInTheDocument();
  });
});
