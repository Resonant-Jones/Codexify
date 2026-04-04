import { afterEach, describe, expect, it, vi } from "vitest";

import {
  aggregateCommandCenterEvents,
  normalizeCommandCenterEvent,
} from "../commandCenterRunAggregation";
import {
  COMMAND_CENTER_RUN_KINDS,
  COMMAND_CENTER_RUN_STATUSES,
  COMMAND_CENTER_RUN_TERMINAL_OUTCOMES,
  COMMAND_CENTER_TRACE_PRESENCE_STATES,
} from "@/features/commandCenter/types";

function useSequentialNow(start = Date.parse("2026-04-01T16:00:00Z")): void {
  let current = start;
  vi.spyOn(Date, "now").mockImplementation(() => current++);
}

function makeMessage(
  type: string,
  data: Record<string, unknown>,
  lastEventId: string
): MessageEvent<string> {
  return new MessageEvent(type, {
    data: JSON.stringify(data),
    lastEventId,
  });
}

afterEach(() => {
  vi.restoreAllMocks();
});

describe("commandCenterRunAggregation", () => {
  it("collapses lifecycle events with the same task_id into one run", () => {
    useSequentialNow();

    const created = normalizeCommandCenterEvent(
      makeMessage(
        "task.created",
        {
          latest_turn_message_id: "msg-1",
          queued_at: "2026-04-01T16:00:00Z",
          run_id: "run-1",
          task_id: "task-1",
          thread_id: 42,
          turn_id: "turn-1",
          type: "chat.completion",
        },
        "evt-1"
      )
    );
    const running = normalizeCommandCenterEvent(
      makeMessage(
        "task.running",
        {
          latest_turn_message_id: "msg-2",
          origin: "api:chat.complete|turn_id=turn-1|source_mode=personal_knowledge",
          warmup_at: "2026-04-01T16:00:02Z",
          run_id: "run-1",
          task_id: "task-1",
          thread_id: 42,
          turn_id: "turn-1",
          state: "awaiting_model",
          type: "chat.completion",
        },
        "evt-2"
      )
    );
    const taskState = normalizeCommandCenterEvent(
      makeMessage(
        "task.state",
        {
          latest_turn_message_id: "msg-3",
          first_token_at: "2026-04-01T16:00:03Z",
          trace: {
            latest_turn_message_id: "msg-4",
            retrieval_query: "How does the cache behave?",
            retrieval_query_matches_latest_turn: true,
            retrieval_target: "search-index",
            source_mode: "personal_knowledge",
            trace_url: "/api/chat/debug/rag-trace/42/latest",
            widen_reason: "explicit_personal_knowledge",
            payload_summary: {
              graph_count: 1,
              memory_count: 2,
              semantic_count: 4,
            },
          },
          run_id: "run-1",
          state: "awaiting_first_token",
          task_id: "task-1",
          thread_id: 42,
          turn_id: "turn-1",
          type: "chat.completion",
        },
        "evt-3"
      )
    );
    const chunk = normalizeCommandCenterEvent(
      makeMessage(
        "task.progress",
        {
          first_output_at: "2026-04-01T16:00:04Z",
          latest_turn_message_id: "msg-3",
          run_id: "run-1",
          task_id: "task-1",
          thread_id: 42,
          token: "Hello",
          turn_id: "turn-1",
          type: "chat.completion",
        },
        "evt-3a"
      )
    );
    const completed = normalizeCommandCenterEvent(
      makeMessage(
        "task.completed",
        {
          completed_at: "2026-04-01T16:00:05Z",
          duration_ms: 4200,
          latest_turn_message_id: "msg-4",
          message_id: "msg-4",
          run_id: "run-1",
          retrieval_query: "How does the cache behave?",
          retrieval_query_matches_latest_turn: true,
          retrieval_target: "search-index",
          task_id: "task-1",
          thread_id: 42,
          turn_id: "turn-1",
          trace_url: "/api/chat/debug/rag-trace/42/latest",
          type: "chat.completion",
        },
        "evt-4"
      )
    );

    const result = aggregateCommandCenterEvents([
      created,
      running,
      taskState,
      chunk,
      completed,
    ]);

    expect(result.runs).toHaveLength(1);

    const run = result.runs[0];
    expect(run).toBeDefined();
    expect(run?.taskId).toBe("task-1");
    expect(run?.identityKind).toBe("task");
    expect(run?.eventCount).toBe(5);
    expect(run?.runKind).toBe(COMMAND_CENTER_RUN_KINDS.CHAT_COMPLETION);
    expect(run?.runType).toBe("chat completion");
    expect(run?.state).toBe("completed");
    expect(run?.terminalOutcome).toBe(COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED);
    expect(run?.status).toBe(COMMAND_CENTER_RUN_STATUSES.COMPLETED);
    expect(run?.summary).toBe("chat completion · completed");
    expect(run?.lastType).toBe("task.completed");
    expect(run?.latestTurnMessageId).toBe("msg-4");
    expect(run?.threadId).toBe(42);
    expect(run?.turnId).toBe("turn-1");
    expect(run?.events).toHaveLength(5);
    expect(run?.lifecycleStates).toEqual([
      "QUEUED",
      "AWAITING_MODEL",
      "AWAITING_FIRST_TOKEN",
      "STREAMING",
      "COMPLETED",
    ]);
    expect(run?.streamingEvidence).toMatchObject({
      chunkCount: 1,
      hasStreamedContent: true,
    });
    expect(run?.timings).toMatchObject({
      completedAt: Date.parse("2026-04-01T16:00:05Z"),
      firstOutputAt: Date.parse("2026-04-01T16:00:04Z"),
      firstTokenAt: Date.parse("2026-04-01T16:00:03Z"),
      queuedAt: Date.parse("2026-04-01T16:00:00Z"),
      totalDurationMs: 4200,
      warmupAt: Date.parse("2026-04-01T16:00:02Z"),
    });
    expect(run?.traceUrl).toBe("/api/chat/debug/rag-trace/42/latest");
    expect(run?.traceEvidence).toMatchObject({
      documentCount: 4,
      graphCount: 1,
      latestTurnTracePresent: true,
      latestTurnMessageId: "msg-4",
      memoryCount: 2,
      retrievalQuery: "How does the cache behave?",
      retrievalQueryMatchesLatestTurn: true,
      retrievalQueryPresent: true,
      retrievalTarget: "search-index",
      sourceMode: "personal_knowledge",
      tracePresenceState: COMMAND_CENTER_TRACE_PRESENCE_STATES.LATEST_TURN_TRACE_PRESENT,
      tracePresent: true,
      traceUrl: "/api/chat/debug/rag-trace/42/latest",
      widenReason: "explicit_personal_knowledge",
    });
    expect(
      run?.events?.some(
        (event) => event.type === "task.state" && event.state === "awaiting first token"
      )
    ).toBe(true);
  });

  it("keeps chunk events on the same run record instead of creating new cards", () => {
    useSequentialNow();

    const created = normalizeCommandCenterEvent(
      makeMessage(
        "task.created",
        {
          task_id: "task-2",
          thread_id: 7,
          type: "chat.completion",
        },
        "evt-10"
      )
    );
    const chunkOne = normalizeCommandCenterEvent(
      makeMessage(
        "task.progress",
        {
          task_id: "task-2",
          thread_id: 7,
          type: "chat.completion",
        },
        "evt-11"
      )
    );
    const chunkTwo = normalizeCommandCenterEvent(
      makeMessage(
        "task.progress",
        {
          task_id: "task-2",
          thread_id: 7,
          type: "chat.completion",
        },
        "evt-12"
      )
    );

    expect(chunkOne.type).toBe("task.chunk");
    expect(chunkTwo.type).toBe("task.chunk");

    const result = aggregateCommandCenterEvents([created, chunkOne, chunkTwo]);

    expect(result.runs).toHaveLength(1);

    const run = result.runs[0];
    expect(run).toBeDefined();
    expect(run?.eventCount).toBe(3);
    expect(run?.runType).toBe("chat completion");
    expect(run?.state).toBe("chunk");
    expect(run?.status).toBe("running");
    expect(run?.summary).toBe("chat completion · chunk");
    expect(run?.lastType).toBe("task.chunk");
    expect(run?.lifecycleStates).toEqual(["QUEUED", "STREAMING"]);
    expect(run?.streamingEvidence).toMatchObject({
      chunkCount: 2,
      hasStreamedContent: true,
    });
    expect(run?.events?.filter((event) => event.type === "task.chunk")).toHaveLength(2);
  });

  it("updates the existing run record when the terminal event arrives", () => {
    useSequentialNow();

    const created = normalizeCommandCenterEvent(
      makeMessage(
        "task.created",
        {
          task_id: "task-3",
          thread_id: 8,
          type: "chat.completion",
        },
        "evt-20"
      )
    );
    const completed = normalizeCommandCenterEvent(
      makeMessage(
        "task.completed",
        {
          completed_at: "2026-04-01T16:10:05Z",
          duration_ms: 1800,
          latest_turn_message_id: "msg-9",
          message_id: "msg-9",
          task_id: "task-3",
          thread_id: 8,
          type: "chat.completion",
        },
        "evt-21"
      )
    );

    const result = aggregateCommandCenterEvents([created, completed]);

    expect(result.runs).toHaveLength(1);

    const run = result.runs[0];
    expect(run).toBeDefined();
    expect(run?.eventCount).toBe(2);
    expect(run?.lastType).toBe("task.completed");
    expect(run?.state).toBe("completed");
    expect(run?.terminalOutcome).toBe(COMMAND_CENTER_RUN_TERMINAL_OUTCOMES.COMPLETED);
    expect(run?.status).toBe(COMMAND_CENTER_RUN_STATUSES.COMPLETED);
    expect(run?.summary).toBe("chat completion · completed");
    expect(run?.lastEventAt).toBe(completed.receivedAt);
    expect(run?.traceEvidence).toBeNull();
    expect(run?.timings).toMatchObject({
      completedAt: Date.parse("2026-04-01T16:10:05Z"),
      totalDurationMs: 1800,
    });
  });

  it("keeps unclassified events visible without polluting classified runs", () => {
    useSequentialNow();

    const classified = normalizeCommandCenterEvent(
      makeMessage(
        "task.created",
        {
          task_id: "task-4",
          thread_id: 9,
          type: "chat.completion",
        },
        "evt-30"
      )
    );
    const unclassified = normalizeCommandCenterEvent(
      makeMessage(
        "message",
        {
          message: "No stable identity yet",
        },
        "evt-31"
      )
    );

    const result = aggregateCommandCenterEvents([classified, unclassified]);

    expect(result.runs).toHaveLength(2);

    const classifiedRun = result.runs.find((run) => run.taskId === "task-4");
    const unclassifiedRun = result.runs.find(
      (run) => run.identityKind === "synthetic" && run.status === "unknown"
    );

    expect(classifiedRun).toBeDefined();
    expect(classifiedRun?.eventCount).toBe(1);
    expect(classifiedRun?.summary).toBe("chat completion · created");
    expect(unclassifiedRun).toBeDefined();
    expect(unclassifiedRun?.runType).toBeNull();
    expect(unclassifiedRun?.summary).toBe("unclassified event");
    expect(unclassifiedRun?.eventCount).toBe(1);
    expect(unclassifiedRun?.taskId).toBeNull();
    expect(unclassifiedRun?.requestId).toBeNull();
  });
});
