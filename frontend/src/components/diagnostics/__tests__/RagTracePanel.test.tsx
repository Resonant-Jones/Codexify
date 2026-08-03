import { render, screen } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import RagTracePanel from "@/components/diagnostics/RagTracePanel";
import { useRagTrace } from "@/hooks/useRagTrace";

vi.mock("@/hooks/useRagTrace", () => ({
  useRagTrace: vi.fn(),
  default: vi.fn(),
}));

const useRagTraceMock = vi.mocked(useRagTrace);

describe("diagnostics RagTracePanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("renders provenance metadata and suppression summaries", () => {
    useRagTraceMock.mockReturnValue({
      trace: {
        documents: [
          {
            id: "doc-1",
            title: "thread-note.md",
            score: 0.91,
            snippet: "retrieved snippet",
            source_type: "semantic-note",
            role: "assistant",
            thread_id: 42,
            project_id: 7,
            retrieval_lane: "thread_semantic",
            policy_reason: "local_hits",
            retrieval_policy: { source_mode: "project" },
          },
        ],
        graph: [],
        retrieval_policy: {
          source_mode: "project",
          boundary_label: "same_user_same_project",
          allow_thread_docs: true,
          allow_project_docs: true,
          allow_semantic_widening: false,
          allow_global_widening: false,
        },
        retrieval_provenance: {
          requested_source_mode: "project",
          normalized_source_mode: "project",
          retrieval_status: "workspace_local_success",
        },
        retrieval_suppression: {
          count: 1,
          counts_by_reason: {
            assistant_vision_refusal_on_image_turn: 1,
          },
          items: [
            {
              id: "suppressed-1",
              source_type: "retrieval",
              role: "assistant",
              thread_id: 42,
              project_id: 7,
              retrieval_lane: "thread_semantic",
              policy_reason: "assistant_vision_refusal_on_image_turn",
              suppressed: true,
              suppression_reason: "assistant_vision_refusal_on_image_turn",
            },
          ],
        },
      },
      loading: false,
      error: null,
      fetchTrace: vi.fn(),
    });

    render(<RagTracePanel threadId={42} />);

    expect(
      screen.getByText("Source type: semantic-note")
    ).toBeInTheDocument();
    expect(screen.getAllByText("Role: assistant")).toHaveLength(2);
    expect(screen.getAllByText("Lane: thread_semantic")).toHaveLength(2);
    expect(screen.getAllByText("Thread: 42")).toHaveLength(2);
    expect(screen.getAllByText("Project: 7")).toHaveLength(2);
    expect(screen.getByText("Policy: local_hits")).toBeInTheDocument();
    expect(screen.getByText("Source mode: project")).toBeInTheDocument();
    expect(
      screen.getByText("Boundary: same_user_same_project")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Requested: project")
    ).toBeInTheDocument();
    expect(
      screen.getByText("Status: workspace_local_success")
    ).toBeInTheDocument();
    expect(
      screen.getByText("assistant_vision_refusal_on_image_turn: 1")
    ).toBeInTheDocument();
    expect(
      screen.getByText("suppressed-1")
    ).toBeInTheDocument();
  });
});
