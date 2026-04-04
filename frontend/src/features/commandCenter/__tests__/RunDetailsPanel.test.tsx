import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import RunDetailsPanel from "../components/RunDetailsPanel";

import type {
  CommandCenterEvent,
  CommandCenterRun,
} from "@/features/commandCenter/types";

const baseTimestamp = Date.parse("2026-04-01T16:00:00Z");

const lifecycleEvents: CommandCenterEvent[] = [
  {
    completedAt: null,
    durationMs: null,
    eventId: "evt-1",
    firstOutputAt: null,
    firstTokenAt: null,
    json: { thread_id: 42, type: "chat.completion" },
    kind: null,
    latestTurnContent: null,
    latestTurnMessageId: "msg-1",
    lifecycleState: "QUEUED",
    raw: '{"thread_id":42,"type":"chat.completion"}',
    queuedAt: baseTimestamp,
    receivedAt: baseTimestamp,
    requestId: null,
    retrievalQuery: null,
    retrievalQueryMatchesLatestTurn: null,
    retrievalTarget: null,
    runId: "run-1",
    sseType: "task.created",
    state: "created",
    status: null,
    summary: "chat completion created",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    traceUrl: null,
    turnId: "turn-1",
    type: "task.created",
    warmupAt: null,
  },
  {
    completedAt: null,
    durationMs: null,
    eventId: "evt-2",
    firstOutputAt: null,
    firstTokenAt: null,
    json: { thread_id: 42, type: "chat.completion" },
    kind: null,
    latestTurnContent: null,
    latestTurnMessageId: "msg-2",
    lifecycleState: "AWAITING_MODEL",
    raw: '{"thread_id":42,"type":"chat.completion"}',
    queuedAt: null,
    receivedAt: baseTimestamp + 1000,
    requestId: null,
    retrievalQuery: null,
    retrievalQueryMatchesLatestTurn: null,
    retrievalTarget: null,
    runId: "run-1",
    sseType: "task.running",
    state: "running",
    status: null,
    summary: "chat completion running",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    traceUrl: null,
    turnId: "turn-1",
    type: "task.running",
    warmupAt: null,
  },
  {
    completedAt: null,
    durationMs: null,
    eventId: "evt-3",
    firstOutputAt: null,
    firstTokenAt: baseTimestamp + 2000,
    json: { thread_id: 42, type: "chat.completion" },
    kind: null,
    latestTurnContent: null,
    latestTurnMessageId: "msg-3",
    lifecycleState: "AWAITING_FIRST_TOKEN",
    raw: '{"thread_id":42,"type":"chat.completion"}',
    queuedAt: null,
    receivedAt: baseTimestamp + 2000,
    requestId: null,
    retrievalQuery: null,
    retrievalQueryMatchesLatestTurn: null,
    retrievalTarget: null,
    runId: "run-1",
    sseType: "task.state",
    state: "awaiting first token",
    status: null,
    summary: "chat completion awaiting first token",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    traceUrl: null,
    turnId: "turn-1",
    type: "task.state",
    warmupAt: null,
  },
  {
    completedAt: null,
    durationMs: null,
    eventId: "evt-4",
    firstOutputAt: baseTimestamp + 3000,
    firstTokenAt: null,
    json: { thread_id: 42, token: "Hello" },
    kind: null,
    latestTurnContent: "Hello",
    latestTurnMessageId: "msg-3",
    lifecycleState: "STREAMING",
    raw: '{"thread_id":42,"token":"Hello"}',
    queuedAt: null,
    receivedAt: baseTimestamp + 3000,
    requestId: null,
    retrievalQuery: null,
    retrievalQueryMatchesLatestTurn: null,
    retrievalTarget: null,
    runId: "run-1",
    sseType: "task.chunk",
    state: "chunk",
    status: null,
    summary: "chat completion chunk",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    traceUrl: null,
    turnId: "turn-1",
    type: "task.chunk",
    warmupAt: null,
  },
  {
    completedAt: Date.parse("2026-04-01T16:00:05Z"),
    durationMs: 4200,
    eventId: "evt-5",
    firstOutputAt: null,
    firstTokenAt: null,
    json: { retrieval_query: "How does the cache behave?" },
    kind: null,
    latestTurnContent: null,
    latestTurnMessageId: "msg-4",
    lifecycleState: "COMPLETED",
    raw: '{"retrieval_query":"How does the cache behave?"}',
    queuedAt: null,
    receivedAt: baseTimestamp + 4000,
    requestId: null,
    retrievalQuery: "How does the cache behave?",
    retrievalQueryMatchesLatestTurn: true,
    retrievalTarget: "search-index",
    runId: "run-1",
    sseType: "task.completed",
    state: "completed",
    status: null,
    summary: "chat completion completed",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: "completed",
    threadId: 42,
    traceUrl: "/api/chat/debug/rag-trace/42/latest",
    turnId: "turn-1",
    type: "task.completed",
    warmupAt: null,
  },
];

function buildRun(overrides: Partial<CommandCenterRun> = {}): CommandCenterRun {
  return {
    eventCount: lifecycleEvents.length,
    events: lifecycleEvents,
    identityKind: "task",
    key: "task-1",
    lastEvent: lifecycleEvents[lifecycleEvents.length - 1],
    lastEventAt: lifecycleEvents[lifecycleEvents.length - 1].receivedAt,
    lastKind: null,
    lastType: "task.completed",
    latestTurnMessageId: "msg-4",
    lifecycleStates: [
      "QUEUED",
      "AWAITING_MODEL",
      "AWAITING_FIRST_TOKEN",
      "STREAMING",
      "COMPLETED",
    ],
    requestId: null,
    runId: "run-1",
    runKind: "chat_completion",
    runType: "chat completion",
    state: "completed",
    status: "completed",
    streamingEvidence: {
      chunkCount: 1,
      firstChunkAt: lifecycleEvents[3].receivedAt,
      hasStreamedContent: true,
    },
    summary: "chat completion · completed",
    taskId: "task-1",
    terminalOutcome: "completed",
    timings: {
      completedAt: Date.parse("2026-04-01T16:00:05Z"),
      firstOutputAt: baseTimestamp + 3000,
      firstTokenAt: baseTimestamp + 2000,
      queuedAt: baseTimestamp,
      totalDurationMs: 4200,
      warmupAt: baseTimestamp + 1000,
    },
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
    threadId: 42,
    turnId: "turn-1",
    ...overrides,
  };
}

describe("RunDetailsPanel", () => {
  it("renders lifecycle states in order", () => {
    render(<RunDetailsPanel run={buildRun()} />);

    expect(
      screen.getByText(
        "QUEUED → AWAITING_MODEL → AWAITING_FIRST_TOKEN → STREAMING → COMPLETED"
      )
    ).toBeInTheDocument();
    expect(screen.getAllByText("Completed").length).toBeGreaterThan(0);
  });

  it("renders timings only when they are present", () => {
    const { rerender } = render(<RunDetailsPanel run={buildRun()} />);

    expect(screen.getByText(/Queued:/)).toBeInTheDocument();
    expect(screen.getByText(/Total:/)).toBeInTheDocument();

    rerender(
      <RunDetailsPanel
        run={buildRun({
          timings: null,
        })}
      />
    );

    expect(screen.queryByText(/Queued:/)).not.toBeInTheDocument();
    expect(screen.queryByText(/Total:/)).not.toBeInTheDocument();
    expect(
      screen.getByText("No structured timing evidence recorded.")
    ).toBeInTheDocument();
  });

  it("renders compact retrieval and trace summary when canonical fields exist", () => {
    render(<RunDetailsPanel run={buildRun()} />);

    expect(screen.getByText("Source: Personal Knowledge")).toBeInTheDocument();
    expect(
      screen.getByText("Widen reason: explicit_personal_knowledge")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Trace status: Latest turn trace present")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Latest turn message: msg-4")).toHaveLength(2);
    expect(screen.getByText("Retrieval query:")).toBeInTheDocument();
    expect(screen.getByText("How does the cache behave?")).toBeInTheDocument();
    expect(screen.getByText("Documents: 4")).toBeInTheDocument();
    expect(screen.getByText("Memory: 2")).toBeInTheDocument();
    expect(screen.getByText("Graph: 1")).toBeInTheDocument();
  });

  it("renders a truthful trace summary when only partial fields are available", () => {
    render(
      <RunDetailsPanel
        run={buildRun({
          traceEvidence: {
            documentCount: null,
            graphCount: null,
            latestTurnContentPresent: false,
            latestTurnMessageId: null,
            latestTurnTracePresent: false,
            memoryCount: null,
            retrievalQuery: null,
            retrievalQueryMatchesLatestTurn: null,
            retrievalQueryPresent: false,
            retrievalTarget: null,
            sourceMode: "project",
            tracePresenceState: "none",
            tracePresent: false,
            traceUrl: null,
            widenReason: "none",
          },
          traceUrl: null,
        })}
      />
    );

    expect(screen.getByText("Grouping key: task-1")).toBeInTheDocument();
    expect(screen.getByText("Task: task-1")).toBeInTheDocument();
    expect(screen.getByText("Thread: 42")).toBeInTheDocument();
    expect(screen.getAllByText("Latest turn message: msg-4")).toHaveLength(2);
    expect(screen.getByText("Run: run-1")).toBeInTheDocument();
    expect(screen.getByText("Source: Project")).toBeInTheDocument();
    expect(screen.getByText("Widen reason: none")).toBeInTheDocument();
    expect(screen.getByText("Trace status: No trace")).toBeInTheDocument();
    expect(screen.getByText("No trace evidence recorded.")).toBeInTheDocument();
    expect(screen.queryByText("Retrieval query:")).not.toBeInTheDocument();
    expect(screen.queryByText("Documents: 4")).not.toBeInTheDocument();
  });

  it("renders a truthful empty state when no trace evidence is present", () => {
    render(
      <RunDetailsPanel
        run={buildRun({
          traceEvidence: null,
        })}
      />
    );

    expect(
      screen.getByText("No retrieval or trace evidence recorded.")
    ).toBeInTheDocument();
  });

  it("keeps raw events collapsed until opened", () => {
    render(
      <RunDetailsPanel
        run={buildRun({
          events: [
            {
              ...lifecycleEvents[0],
              json: { message: "Secondary payload" },
              raw: '{"message":"Secondary payload"}',
              summary: "Secondary payload",
            },
          ],
          eventCount: 1,
        })}
      />
    );

    expect(screen.queryByText("Secondary payload")).not.toBeInTheDocument();
    expect(
      screen.queryByText(/"message":\s+"Secondary payload"/)
    ).not.toBeInTheDocument();

    fireEvent.click(screen.getByText("Raw events"));

    expect(screen.getByText("Secondary payload")).toBeInTheDocument();
    expect(screen.getByText(/"message":\s+"Secondary payload"/)).toBeInTheDocument();
  });
});
