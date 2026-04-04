import React from "react";
import { describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";

import RunSummaryCard from "../components/RunSummaryCard";

import type {
  CommandCenterEvent,
  CommandCenterRun,
} from "@/features/commandCenter/types";

const baseTimestamp = Date.parse("2026-04-01T16:00:00Z");

const canonicalEvents: CommandCenterEvent[] = [
  {
    eventId: "evt-1",
    json: { type: "chat.completion", thread_id: 42 },
    kind: null,
    latestTurnMessageId: "msg-1",
    raw: '{"type":"chat.completion","thread_id":42}',
    receivedAt: baseTimestamp,
    requestId: null,
    runId: "run-task-1",
    sseType: "task.created",
    state: "created",
    status: null,
    summary: "chat completion created",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    turnId: "turn-1",
    type: "task.created",
  },
  {
    eventId: "evt-2",
    json: { type: "chat.completion", thread_id: 42 },
    kind: null,
    latestTurnMessageId: "msg-2",
    raw: '{"type":"chat.completion","thread_id":42}',
    receivedAt: baseTimestamp + 1000,
    requestId: null,
    runId: "run-task-1",
    sseType: "task.running",
    state: "running",
    status: null,
    summary: "chat completion running",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    turnId: "turn-1",
    type: "task.running",
  },
  {
    eventId: "evt-3",
    json: { type: "chat.completion", thread_id: 42 },
    kind: null,
    latestTurnMessageId: "msg-3",
    raw: '{"type":"chat.completion","thread_id":42}',
    receivedAt: baseTimestamp + 2000,
    requestId: null,
    runId: "run-task-1",
    sseType: "task.chunk",
    state: "chunk",
    status: null,
    summary: "chat completion chunk",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: null,
    threadId: 42,
    turnId: "turn-1",
    type: "task.chunk",
  },
  {
    eventId: "evt-4",
    json: { type: "chat.completion", thread_id: 42, message_id: "msg-4" },
    kind: null,
    latestTurnMessageId: "msg-4",
    raw: '{"type":"chat.completion","thread_id":42,"message_id":"msg-4"}',
    receivedAt: baseTimestamp + 3000,
    requestId: null,
    runId: "run-task-1",
    sseType: "task.completed",
    state: "completed",
    status: null,
    summary: "chat completion completed",
    taskId: "task-1",
    taskType: "chat.completion",
    terminalOutcome: "succeeded",
    threadId: 42,
    turnId: "turn-1",
    type: "task.completed",
  },
];

const canonicalRun: CommandCenterRun = {
  eventCount: canonicalEvents.length,
  events: canonicalEvents,
  identityKind: "task",
  key: "task-1",
  lastEvent: canonicalEvents[3],
  lastEventAt: canonicalEvents[3].receivedAt,
  lastKind: null,
  lastType: "task.completed",
  latestTurnMessageId: "msg-4",
  requestId: null,
  runId: "run-task-1",
  runType: "chat completion",
  state: "completed",
  status: "succeeded",
  streamingEvidence: {
    chunkCount: 1,
    firstChunkAt: baseTimestamp + 2000,
    hasStreamedContent: true,
  },
  summary: "chat completion · completed",
  taskId: "task-1",
  terminalOutcome: "succeeded",
  threadId: 42,
  turnId: "turn-1",
};

const unknownRun: CommandCenterRun = {
  eventCount: 1,
  identityKind: "synthetic",
  key: "event-raw-1",
  lastEvent: {
    eventId: "evt-raw-1",
    json: { message: "No stable identity" },
    kind: null,
    latestTurnMessageId: null,
    raw: '{"message":"No stable identity"}',
    receivedAt: baseTimestamp,
    requestId: null,
    runId: null,
    sseType: "message",
    state: null,
    status: "unknown",
    summary: "No stable identity",
    taskId: null,
    taskType: null,
    terminalOutcome: null,
    threadId: null,
    turnId: null,
    type: null,
  },
  lastEventAt: baseTimestamp,
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
};

describe("RunSummaryCard", () => {
  it("renders canonical task states as semantic labels with identity and counts", () => {
    const onOpen = vi.fn();

    render(<RunSummaryCard onOpen={onOpen} run={canonicalRun} />);

    const card = screen.getByTestId("command-center-run-task-1");

    expect(within(card).getByText("chat completion")).toBeInTheDocument();
    expect(within(card).getByText(/^completed$/)).toBeInTheDocument();
    expect(within(card).getByText(/^succeeded$/)).toBeInTheDocument();
    expect(within(card).getByText("Events: 4")).toBeInTheDocument();
    expect(within(card).getByText(/Updated:/)).toBeInTheDocument();
    expect(within(card).getByText("Task: task-1")).toBeInTheDocument();
    expect(within(card).getByText("Thread: 42")).toBeInTheDocument();
    expect(within(card).getByText("Turn: turn-1")).toBeInTheDocument();
    expect(within(card).getByText("Latest turn message: msg-4")).toBeInTheDocument();
    expect(within(card).getByText("Chunks: 1")).toBeInTheDocument();
    expect(within(card).getByText("Inspect raw events")).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /open details for chat completion/i })
    ).toBeInTheDocument();
  });

  it("keeps unknown labels only on truly unclassified runs", () => {
    const onOpen = vi.fn();

    render(
      <>
        <RunSummaryCard onOpen={onOpen} run={canonicalRun} />
        <RunSummaryCard onOpen={onOpen} run={unknownRun} />
      </>
    );

    expect(within(screen.getByTestId("command-center-run-task-1")).queryByText("Unknown run")).toBeNull();
    expect(within(screen.getByTestId("command-center-run-event-raw-1")).getByText("Unknown run")).toBeInTheDocument();
    expect(within(screen.getByTestId("command-center-run-event-raw-1")).getByText(/^unknown$/)).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /open details for unknown run/i })
    ).toBeInTheDocument();
  });
});
