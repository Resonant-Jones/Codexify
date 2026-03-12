import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, test, vi } from "vitest";

import { CompletionReplayPage } from "@/components/operator/CompletionReplayPage";
import type { OperatorRunResult } from "@/lib/operatorReplay";

const BASE_RUN_RESULT: OperatorRunResult = {
  threadId: 12,
  createdThread: true,
  completion: {
    taskId: "task-123",
    turnId: "11111111-1111-4111-8111-111111111111",
    traceUrl: "/api/chat/debug/rag-trace/12/latest",
    depthMode: "diagnostic",
    requestedDepthMode: "diagnostic",
    effectiveDepthMode: "diagnostic",
    depthDowngradeReason: null,
  },
  taskTerminal: {
    type: "task.completed",
    payload: {
      duration_ms: 2450,
      provider: "local",
      model: "qwen3:14b",
      message_id: 8,
    },
  },
  taskWaitTimedOut: false,
  taskEventError: null,
  messages: [
    {
      id: 1,
      thread_id: 12,
      role: "user",
      content: "Replay this completion",
    },
    {
      id: 8,
      thread_id: 12,
      role: "assistant",
      content: "Here is the final answer.",
      turn_id: "11111111-1111-4111-8111-111111111111",
    },
  ],
  messagesError: null,
  trace: {
    documents: [
      {
        id: "doc-1",
        title: "Runbook",
        snippet: "Relevant runbook excerpt",
        score: 0.91,
        source: "knowledge-base",
      },
    ],
    graph: [
      {
        node_id: "mem-1",
        text: "Previous operator memory",
        score: 0.77,
        kind: "memory",
      },
    ],
    active_profile_id: "local_mode",
    retrieval_mode: "diagnostic",
  },
  traceError: null,
};

describe("CompletionReplayPage", () => {
  test("renders the three-pane operator layout", () => {
    const runReplay = vi.fn().mockResolvedValue(BASE_RUN_RESULT);

    render(<CompletionReplayPage runReplay={runReplay} />);

    expect(
      screen.getByRole("heading", { name: "Input / Runtime Parameters" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Retrieved Context / RAG Trace" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("heading", { name: "Prompt / Answer Inspection" })
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Run" })).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: /dry run/i })
    ).not.toBeInTheDocument();
  });

  test("shows a truthful empty state when trace data is missing", async () => {
    const user = userEvent.setup();
    const runReplay = vi.fn().mockResolvedValue({
      ...BASE_RUN_RESULT,
      trace: null,
      traceError: "Trace data not returned by current API.",
    });

    render(<CompletionReplayPage runReplay={runReplay} />);

    await user.type(
      screen.getByLabelText("User Message"),
      "Inspect missing trace behavior"
    );
    await user.click(screen.getByRole("button", { name: "Run" }));

    await waitFor(() => {
      expect(
        screen.getAllByText("Trace data not returned by current API.").length
      ).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getByText("Trace Unavailable")).toBeInTheDocument();
  });

  test("renders returned answer and metadata from a completed run", async () => {
    const user = userEvent.setup();
    const runReplay = vi.fn().mockResolvedValue(BASE_RUN_RESULT);

    render(<CompletionReplayPage runReplay={runReplay} />);

    await user.type(
      screen.getByLabelText("User Message"),
      "Inspect answer metadata"
    );
    await user.click(screen.getByRole("button", { name: "Run" }));

    expect(await screen.findByText("Here is the final answer.")).toBeInTheDocument();
    expect(screen.getByText("Runbook")).toBeInTheDocument();
    expect(screen.getByText("Relevant runbook excerpt")).toBeInTheDocument();
    expect(screen.getByText("Previous operator memory")).toBeInTheDocument();
    expect(screen.getByText("local")).toBeInTheDocument();
    expect(screen.getByText("qwen3:14b")).toBeInTheDocument();
    expect(screen.getByText("2,450 ms")).toBeInTheDocument();

    await waitFor(() => {
      expect(runReplay).toHaveBeenCalledTimes(1);
    });
  });
});
