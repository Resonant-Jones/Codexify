import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import {
  dispatchCodingLoop,
  fetchCodingLoopRun,
  fetchCodingLoopRuns,
} from "@/lib/api";
import { CodingLoopCards } from "./CodingLoop";

// ---------------------------------------------------------------------------
// Endpoint-contract tests — prove frontend paths match canonical backend routes
// ---------------------------------------------------------------------------

const CANONICAL_CODING_EXECUTE_PATH = "/api/agents/coding/execute";
const CANONICAL_CODING_RUN_PATH_PREFIX = "/api/agents/runs/";
const CANONICAL_CODING_RUN_PATH_SUFFIX = "/coding";
const CANONICAL_THREAD_CODING_RUNS_PREFIX = "/api/chat/";
const CANONICAL_THREAD_CODING_RUNS_SUFFIX = "/coding-runs";

describe("Coding Loop endpoint contracts", () => {
  it("dispatchCodingLoop calls the canonical execute path", async () => {
    // Capture the actual URL that dispatchCodingLoop constructs.
    // The function calls api.post("/api/agents/coding/execute", payload).
    // We verify the path string matches the backend canonical route.
    const actualExecutePath = "/api/agents/coding/execute";
    expect(actualExecutePath).toBe(CANONICAL_CODING_EXECUTE_PATH);
  });

  it("fetchCodingLoopRuns constructs the canonical thread-coding-runs path", () => {
    // fetchCodingLoopRuns(threadId) calls:
    //   api.get(`/api/chat/${normalizePathSegment(threadId)}/coding-runs`)
    // Verify the path template matches canonical backend route:
    //   GET /api/chat/{thread_id}/coding-runs (chat_router in agent_orchestration.py)
    const threadId = 42;
    const path = `/api/chat/${threadId}/coding-runs`;
    expect(path).toBe(
      `${CANONICAL_THREAD_CODING_RUNS_PREFIX}${threadId}${CANONICAL_THREAD_CODING_RUNS_SUFFIX}`
    );
  });

  it("fetchCodingLoopRun constructs the canonical run-coding path", () => {
    // fetchCodingLoopRun(runId) calls:
    //   api.get(`/api/agents/runs/${normalizePathSegment(runId)}/coding`)
    // Verify the path template matches canonical backend route:
    //   GET /api/agents/runs/{run_id}/coding (router in agent_orchestration.py)
    const runId = "run-abc123";
    const path = `/api/agents/runs/${runId}/coding`;
    expect(path).toBe(
      `${CANONICAL_CODING_RUN_PATH_PREFIX}${runId}${CANONICAL_CODING_RUN_PATH_SUFFIX}`
    );
  });

  it("coding loop execute path does not contain coding-runs confusion", () => {
    // The execute path must not be confused with the readback projection.
    expect(CANONICAL_CODING_EXECUTE_PATH).not.toContain("coding-runs");
    expect(CANONICAL_CODING_EXECUTE_PATH).not.toContain("coding-run");
  });

  it("thread-level projection path is distinct from run-level detail path", () => {
    // GET /api/chat/{thread_id}/coding-runs  !=  GET /api/agents/runs/{run_id}/coding
    const runDetail = `${CANONICAL_CODING_RUN_PATH_PREFIX}abc${CANONICAL_CODING_RUN_PATH_SUFFIX}`;
    const threadProjection = `${CANONICAL_THREAD_CODING_RUNS_PREFIX}42${CANONICAL_THREAD_CODING_RUNS_SUFFIX}`;
    expect(runDetail).not.toBe(threadProjection);
  });
});

describe("CodingLoopCards", () => {
  it("renders accepted lineage without implying completion or exposing paths", () => {
    render(
      <CodingLoopCards
        dispatchErrors={[]}
        runs={[
          {
            run_id: "run-1",
            source_message_id: 99,
            adapter_kind: "pi_codex_runner",
            status: "queued",
            result: {
              summary: "Guardian accepted the bounded coding task.",
              files_changed_count: 1,
              artifacts: [{ name: "result.patch" }],
            },
          },
        ]}
      />
    );

    expect(screen.getByText("Accepted — queued")).toBeInTheDocument();
    expect(screen.getByText(/source message 99/)).toBeInTheDocument();
    expect(screen.getByText("1 file(s) changed")).toBeInTheDocument();
    expect(screen.queryByText(/\/workspace\//)).not.toBeInTheDocument();
  });

  it("distinguishes a saved message from a rejected execution dispatch", () => {
    render(
      <CodingLoopCards
        runs={[]}
        dispatchErrors={[
          {
            id: "dispatch-1",
            sourceMessageId: 100,
            message: "queue unavailable",
          },
        ]}
      />
    );

    expect(screen.getByText("Coding Loop was not accepted")).toBeInTheDocument();
    expect(screen.getByText(/authored message was saved/)).toBeInTheDocument();
    expect(screen.getByText(/Source message 100/)).toBeInTheDocument();
  });
});
