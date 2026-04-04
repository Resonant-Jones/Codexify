import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RagTracePanel from "@/features/commandCenter/components/RagTracePanel";
import { fetchLatestRagTrace } from "@/lib/api";
import type { CommandCenterRun } from "@/features/commandCenter/types";

vi.mock("@/lib/api", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api")>("@/lib/api");
  return {
    ...actual,
    fetchLatestRagTrace: vi.fn(),
  };
});

const fetchLatestRagTraceMock = vi.mocked(fetchLatestRagTrace);

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (reason?: unknown) => void;
  const promise = new Promise<T>((nextResolve, nextReject) => {
    resolve = nextResolve;
    reject = nextReject;
  });
  return { promise, reject, resolve };
}

function buildRun(
  overrides: Partial<CommandCenterRun> = {}
): CommandCenterRun {
  return {
    eventCount: 1,
    key: "task_001",
    lastEvent: {
      eventId: "evt-1",
      json: {},
      kind: "task.completed",
      raw: "{\"thread_id\":42}",
      receivedAt: Date.now(),
      runId: "run_001",
      sseType: "task.completed",
      status: null,
      summary: "Task completed",
      taskId: "task_001",
      type: "task.completed",
    },
    lastEventAt: Date.now(),
    lastKind: "task.completed",
    lastType: "task.completed",
    runId: "run_001",
    status: "completed",
    summary: "Task completed",
    taskId: "task_001",
    threadId: 42,
    traceUrl: "/api/chat/debug/rag-trace/42/latest",
    ...overrides,
  };
}

describe("RagTracePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders a loading state while the trace request is in flight", async () => {
    const pending = deferred<Record<string, unknown>>();
    fetchLatestRagTraceMock.mockReturnValue(pending.promise);

    render(<RagTracePanel run={buildRun()} />);

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Loading retrieval trace…"
    );

    pending.resolve({ documents: [], graph: [] });
    expect(
      await screen.findByText("No retrieval evidence available for this thread yet.")
    ).toBeInTheDocument();
  });

  test("renders explicit empty states for no selected run and no resolvable thread", async () => {
    const { rerender } = render(<RagTracePanel run={null} />);

    expect(
      screen.getByText("Select a run to inspect retrieval evidence.")
    ).toBeInTheDocument();
    expect(fetchLatestRagTraceMock).not.toHaveBeenCalled();

    rerender(
      <RagTracePanel
        run={buildRun({
          threadId: null,
          traceUrl: null,
        })}
      />
    );

    expect(
      await screen.findByText("No resolvable thread available for this run.")
    ).toBeInTheDocument();
    expect(fetchLatestRagTraceMock).not.toHaveBeenCalled();
  });

  test("renders semantic evidence without rewriting the evidence text", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({
      documents: [
        {
          id: "doc-low",
          score: 0.42,
          snippet: "Lower confidence evidence from retrieval.",
          title: "beta-notes.md",
        },
        {
          id: "doc-high",
          score: 0.91,
          snippet: "Original evidence text: keep this wording intact.",
          title: "alpha-notes.md",
        },
      ],
      graph: [],
    });

    render(<RagTracePanel run={buildRun()} />);

    expect(await screen.findByRole("heading", { name: "Semantic Results" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Memory Results" })).not.toBeInTheDocument();
    expect(
      screen.getByText("Original evidence text: keep this wording intact.")
    ).toBeInTheDocument();
    expect(screen.getByText("Source: alpha-notes.md")).toBeInTheDocument();

    const highEvidence = screen.getByText(
      "Original evidence text: keep this wording intact."
    );
    const lowEvidence = screen.getByText(
      "Lower confidence evidence from retrieval."
    );
    expect(
      highEvidence.compareDocumentPosition(lowEvidence) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  test("renders semantic results before memory results and sorts both sections by score", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({
      documents: [
        {
          id: "sem-low",
          score: 0.2,
          snippet: "Semantic evidence with lower score.",
          title: "semantic-low.md",
        },
        {
          id: "sem-high",
          score: 0.8,
          snippet: "Semantic evidence with higher score.",
          title: "semantic-high.md",
        },
      ],
      memory: [
        {
          id: "mem-low",
          score: 0.1,
          text: "Memory evidence with lower score.",
          origin: "memory",
        },
        {
          id: "mem-high",
          score: 0.7,
          text: "Memory evidence with higher score.",
          origin: "memory",
        },
      ],
    });

    render(<RagTracePanel run={buildRun()} />);

    const semanticHeading = await screen.findByRole("heading", {
      name: "Semantic Results",
    });
    const memoryHeading = screen.getByRole("heading", {
      name: "Memory Results",
    });
    expect(
      semanticHeading.compareDocumentPosition(memoryHeading) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();

    const highSemantic = screen.getByText("Semantic evidence with higher score.");
    const lowSemantic = screen.getByText("Semantic evidence with lower score.");
    expect(
      highSemantic.compareDocumentPosition(lowSemantic) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();

    const highMemory = screen.getByText("Memory evidence with higher score.");
    const lowMemory = screen.getByText("Memory evidence with lower score.");
    expect(
      highMemory.compareDocumentPosition(lowMemory) &
        Node.DOCUMENT_POSITION_FOLLOWING
    ).toBeTruthy();
  });

  test("renders an unavailable state when the resolved thread has no trace yet", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({
      documents: [],
      graph: [],
    });

    render(<RagTracePanel run={buildRun()} />);

    expect(
      await screen.findByText("No retrieval evidence available for this thread yet.")
    ).toBeInTheDocument();
  });

  test("renders backend errors without exposing a retry action", async () => {
    fetchLatestRagTraceMock.mockRejectedValue(
      Object.assign(new Error("trace viewer unavailable"), {
        response: { data: { detail: "trace viewer unavailable" } },
      })
    );

    render(<RagTracePanel run={buildRun()} />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "trace viewer unavailable"
    );
    expect(screen.queryByRole("button", { name: /retry/i })).not.toBeInTheDocument();
  });
});
