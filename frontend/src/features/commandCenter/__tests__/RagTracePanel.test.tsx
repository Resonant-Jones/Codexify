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
const canonicalTraceEvidence: NonNullable<CommandCenterRun["traceEvidence"]> = {
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
};

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
    latestTurnMessageId: "msg-4",
    runId: "run_001",
    status: "completed",
    summary: "Task completed",
    taskId: "task_001",
    threadId: 42,
    traceUrl: "/api/chat/debug/rag-trace/42/latest",
    traceEvidence: null,
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
      await screen.findByText("No trace evidence exists for this run.")
    ).toBeInTheDocument();
    expect(screen.getByText("Thread: 42")).toBeInTheDocument();
    expect(screen.getByText("Latest turn message: msg-4")).toBeInTheDocument();
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
      await screen.findByText("No thread identity available for this run.")
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

    render(
      <RagTracePanel
        run={buildRun({
          traceEvidence: canonicalTraceEvidence,
        })}
      />
    );

    expect(await screen.findByRole("heading", { name: "Semantic Results" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Memory Results" })).not.toBeInTheDocument();
    expect(screen.getByText("Thread: 42")).toBeInTheDocument();
    expect(screen.getByText("Latest turn message: msg-4")).toBeInTheDocument();
    expect(screen.getByText("Trace summary: Latest turn trace present")).toBeInTheDocument();
    expect(screen.getByText("Live trace: Aligned to this run/thread")).toBeInTheDocument();
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

    render(
      <RagTracePanel
        run={buildRun({
          traceEvidence: canonicalTraceEvidence,
        })}
      />
    );

    const semanticHeading = await screen.findByRole("heading", {
      name: "Semantic Results",
    });
    const memoryHeading = screen.getByRole("heading", {
      name: "Memory Results",
    });
    expect(screen.getByText("Thread: 42")).toBeInTheDocument();
    expect(screen.getByText("Latest turn message: msg-4")).toBeInTheDocument();
    expect(screen.getByText("Trace summary: Latest turn trace present")).toBeInTheDocument();
    expect(screen.getByText("Live trace: Aligned to this run/thread")).toBeInTheDocument();
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

  test("renders a truthful no-trace state when no trace evidence exists", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({
      documents: [],
      graph: [],
    });

    render(<RagTracePanel run={buildRun()} />);

    expect(
      await screen.findByText("No trace evidence exists for this run.")
    ).toBeInTheDocument();
    expect(screen.getByText("Trace summary: No trace evidence exists for this run")).toBeInTheDocument();
    expect(screen.getByText("Live trace: No trace evidence exists for this run")).toBeInTheDocument();
  });

  test("renders a mismatch state when trace summary is present but the live trace is empty", async () => {
    fetchLatestRagTraceMock.mockResolvedValue({
      documents: [],
      graph: [],
    });

    render(
      <RagTracePanel
        run={buildRun({
          traceEvidence: canonicalTraceEvidence,
        })}
      />
    );

    expect(
      await screen.findByText("Trace summary present, live trace unavailable.")
    ).toBeInTheDocument();
    expect(screen.getByText("Trace summary: Latest turn trace present")).toBeInTheDocument();
    expect(
      screen.getByText("Live trace: Trace summary present, live trace unavailable")
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
