import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";

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
const mockClipboardWriteText = vi.fn();

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
  mockClipboardWriteText.mockReset();
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

  it("renders the standalone thread posture panel and updates with the selected thread", async () => {
    render(<CommandCenterPage enabled />);

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/no retrieval posture evidence for this thread/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture/i })
    ).not.toBeInTheDocument();

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    expect(within(threadPanel).getByText(/source: conversation/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/boundary: active_conversation_only/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/override: conversation/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/widen: none/i)).toBeInTheDocument();
    expect(within(threadPanel).getByText(/conversation-only/i)).toBeInTheDocument();
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
    expect(within(threadPanel).getByText("What these fields mean")).toBeInTheDocument();
    expect(within(threadPanel).getByRole("button", { name: /copy posture/i })).toBeInTheDocument();

    fireEvent.click(within(threadPanel).getByRole("button", { name: /copy posture/i }));

    const expectedPostureJson = JSON.stringify(
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

    expect(mockClipboardWriteText).toHaveBeenCalledWith(expectedPostureJson);
    await waitFor(() => {
      expect(within(threadPanel).getByText(/copied posture/i)).toBeInTheDocument();
    });
  });

  it("shows copy failure feedback when the clipboard write is rejected", async () => {
    mockClipboardWriteText.mockRejectedValueOnce(new Error("clipboard denied"));

    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-alpha/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    fireEvent.click(within(threadPanel).getByRole("button", { name: /copy posture/i }));

    await waitFor(() => {
      expect(within(threadPanel).getByText(/copy failed/i)).toBeInTheDocument();
    });
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

    // Verify explainer text is also present
    expect(within(workbench).getByText(/This run stayed inside the active conversation\./i)).toBeInTheDocument();
    expect(within(workbench).getByText(/No widening occurred\./i)).toBeInTheDocument();
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
    expect(within(workbench).getByRole("button", { name: /copy posture/i })).toBeInTheDocument();
  });

  it("renders loading state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-golf/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/loading retrieval posture/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture/i })
    ).not.toBeInTheDocument();
  });

  it("renders error state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-hotel/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/retrieval posture unavailable/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture/i })
    ).not.toBeInTheDocument();
  });

  it("renders empty state for the standalone posture panel", () => {
    render(<CommandCenterPage enabled />);

    const workbench = screen.getByTestId("command-center-trace-workbench");
    fireEvent.click(within(workbench).getByRole("button", { name: /task-india/i }));

    const threadPanel = screen.getByTestId("command-center-thread-posture-panel");
    expect(within(threadPanel).getByText("Thread retrieval posture")).toBeInTheDocument();
    expect(within(threadPanel).getByText(/no retrieval posture evidence for this thread/i)).toBeInTheDocument();
    expect(
      within(threadPanel).queryByRole("button", { name: /copy posture/i })
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
    expect(within(workbench).getByRole("button", { name: /copy posture/i })).toBeInTheDocument();
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
    expect(within(workbench).getByRole("button", { name: /copy posture/i })).toBeInTheDocument();
  });
});
