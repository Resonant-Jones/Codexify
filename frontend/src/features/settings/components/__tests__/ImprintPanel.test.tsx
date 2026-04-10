import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import ImprintReviewPanel from "@/features/settings/components/ImprintReviewPanel";
import {
  fetchImprintReviewStatus,
  requestImprintProposalForReview,
} from "@/features/settings/api/imprint";

vi.mock("@/features/settings/api/imprint", () => ({
  acceptImprintProposal: vi.fn(),
  fetchImprintReviewStatus: vi.fn(),
  rejectImprintProposal: vi.fn(),
  requestImprintProposalForReview: vi.fn(),
}));

const fetchImprintReviewStatusMock = vi.mocked(fetchImprintReviewStatus);
const requestImprintProposalForReviewMock = vi.mocked(
  requestImprintProposalForReview
);
describe("ImprintPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("loads and renders active imprint plus pending proposal state", async () => {
    fetchImprintReviewStatusMock.mockResolvedValue({
      activeImprint: {
        createdAt: "2026-03-09T10:00:00Z",
        heatScore: 0.7,
        id: 14,
        preferredName: "friend",
        status: "active",
      },
      personaSummary: {
        createdAt: "2026-03-09T10:05:00Z",
        id: 2,
        snippet: "Calm, grounded voice.",
        source: "user",
      },
      promptMeta: {
        docsCount: 1,
        estimatedTokens: 1200,
      },
    });
    const backendPromptMetadata = {
      generator_version: "imprint-proposal-v1",
      heat_score: 0.73,
      persona_hints: ["stay grounded"],
      prompt_hints: ["ask clarifying questions"],
      requested_depth: "deep",
    };
    requestImprintProposalForReviewMock.mockResolvedValue({
      imprintDraft: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        projectId: 5,
        status: "draft",
        userId: "u1",
      },
      name: "Harbor",
      personaDraft: "Respond with clear structure and warmer phrasing.",
      promptMetadata: backendPromptMetadata,
      proposal: {
        generatorVersion: "imprint-proposal-v1",
        personaDraft: "Respond with clear structure and warmer phrasing.",
        preferredName: "friend",
        projectId: 5,
        proposalHash: "proposal-hash-abcdef",
        proposalName: "Harbor",
        proposalVersion: 1,
        promptMetadata: backendPromptMetadata,
        scopeKind: "project_scoped",
        snapshotHash: "snapshot-hash-123456",
        snapshotVersion: 4,
        userId: "u1",
      },
    });

    render(<ImprintReviewPanel projectId={5} threadId={11} />);

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading imprint review state…"
    );

    expect(await screen.findByText("Imprint Review")).toBeInTheDocument();
    expect(screen.getByText("Active imprint available")).toBeInTheDocument();
    expect(screen.getByText("Proposal available for review")).toBeInTheDocument();
    expect(
      screen.getByText(
        /Imprint is a persisted style and presentation layer\. Persona is the user-editable voice layer\./
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Respond with clear structure and warmer phrasing.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Generator: imprint-proposal-v1/)
    ).toBeInTheDocument();
    expect(screen.getByText("Prompt hints: 1")).toBeInTheDocument();
    expect(screen.getByText("Heat score: 0.73")).toBeInTheDocument();

    expect(fetchImprintReviewStatusMock).toHaveBeenCalledWith({
      projectId: 5,
      threadId: 11,
    });
    expect(requestImprintProposalForReviewMock).toHaveBeenCalledWith({
      projectId: 5,
      threadId: 11,
    });
  });
});
