import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import ImprintReviewPanel from "@/features/settings/components/ImprintReviewPanel";
import {
  acceptImprintProposal,
  fetchImprintReviewStatus,
  rejectImprintProposal,
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
const acceptImprintProposalMock = vi.mocked(acceptImprintProposal);
const rejectImprintProposalMock = vi.mocked(rejectImprintProposal);

describe("ImprintReviewPanel", () => {
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
        /Imprint is a deeper style and reasoning layer\. Persona is the user-editable mask or voice layer\./
      )
    ).toBeInTheDocument();
    expect(
      screen.getByText("Respond with clear structure and warmer phrasing.")
    ).toBeInTheDocument();

    expect(fetchImprintReviewStatusMock).toHaveBeenCalledWith({
      projectId: 5,
      threadId: 11,
    });
    expect(requestImprintProposalForReviewMock).toHaveBeenCalledWith({
      projectId: 5,
      threadId: 11,
    });
  });

  test("shows empty state when no active imprint or pending proposal exists", async () => {
    fetchImprintReviewStatusMock.mockResolvedValue({
      activeImprint: null,
      personaSummary: null,
      promptMeta: null,
    });
    requestImprintProposalForReviewMock.mockResolvedValue(null);

    render(<ImprintReviewPanel />);

    expect(await screen.findAllByText("No pending proposal")).toHaveLength(2);
    expect(screen.getByText("No active imprint")).toBeInTheDocument();
  });

  test("accepts a proposal successfully and reloads status", async () => {
    const user = userEvent.setup();

    fetchImprintReviewStatusMock
      .mockResolvedValueOnce({
        activeImprint: null,
        personaSummary: null,
        promptMeta: null,
      })
      .mockResolvedValueOnce({
        activeImprint: {
          createdAt: "2026-03-09T10:20:00Z",
          heatScore: 0.8,
          id: 27,
          preferredName: "friend",
          status: "active",
        },
        personaSummary: {
          createdAt: "2026-03-09T10:21:00Z",
          id: 99,
          snippet: "Returned by backend",
          source: "imprint_zero_seed",
        },
        promptMeta: {
          docsCount: 1,
          estimatedTokens: 1400,
        },
      });
    requestImprintProposalForReviewMock.mockResolvedValue({
      imprintDraft: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        projectId: null,
        status: "draft",
        userId: "u1",
      },
      name: "Harbor",
      personaDraft: "Review me safely.",
    });
    acceptImprintProposalMock.mockResolvedValue({
      imprint: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        status: "active",
      },
      persona: {
        createdAt: "2026-03-09T10:21:00Z",
        id: 99,
        isActive: true,
        source: "imprint_zero_seed",
      },
    });

    render(<ImprintReviewPanel />);

    await screen.findByText("Proposal available for review");
    await user.click(screen.getByRole("button", { name: "Accept" }));

    await waitFor(() => {
      expect(acceptImprintProposalMock).toHaveBeenCalledWith({
        imprintId: 27,
        projectId: undefined,
        threadId: undefined,
      });
    });
    expect(fetchImprintReviewStatusMock).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Proposal accepted")).toBeInTheDocument();
    expect(
      screen.getByText("Persona upsert returned by backend")
    ).toBeInTheDocument();
  });

  test("rejects a proposal successfully and reloads status", async () => {
    const user = userEvent.setup();

    fetchImprintReviewStatusMock
      .mockResolvedValueOnce({
        activeImprint: null,
        personaSummary: null,
        promptMeta: null,
      })
      .mockResolvedValueOnce({
        activeImprint: null,
        personaSummary: null,
        promptMeta: null,
      });
    requestImprintProposalForReviewMock.mockResolvedValue({
      imprintDraft: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        projectId: null,
        status: "draft",
        userId: "u1",
      },
      name: "Harbor",
      personaDraft: "Review me safely.",
    });
    rejectImprintProposalMock.mockResolvedValue({
      imprintId: 27,
      ok: true,
      status: "rejected",
    });

    render(<ImprintReviewPanel />);

    await screen.findByText("Proposal available for review");
    await user.click(screen.getByRole("button", { name: "Reject" }));

    await waitFor(() => {
      expect(rejectImprintProposalMock).toHaveBeenCalledWith({
        imprintId: 27,
      });
    });
    expect(fetchImprintReviewStatusMock).toHaveBeenCalledTimes(2);
    expect(await screen.findByText("Proposal rejected")).toBeInTheDocument();
  });

  test("surfaces backend failure on accept", async () => {
    const user = userEvent.setup();

    fetchImprintReviewStatusMock.mockResolvedValue({
      activeImprint: null,
      personaSummary: null,
      promptMeta: null,
    });
    requestImprintProposalForReviewMock.mockResolvedValue({
      imprintDraft: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        projectId: null,
        status: "draft",
        userId: "u1",
      },
      name: "Harbor",
      personaDraft: "Review me safely.",
    });
    acceptImprintProposalMock.mockRejectedValue(
      Object.assign(new Error("blocked"), {
        response: { data: { detail: "identity updates disabled for this context" } },
      })
    );

    render(<ImprintReviewPanel />);

    await screen.findByText("Proposal available for review");
    await user.click(screen.getByRole("button", { name: "Accept" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "identity updates disabled for this context"
    );
  });

  test("surfaces backend failure on reject", async () => {
    const user = userEvent.setup();

    fetchImprintReviewStatusMock.mockResolvedValue({
      activeImprint: null,
      personaSummary: null,
      promptMeta: null,
    });
    requestImprintProposalForReviewMock.mockResolvedValue({
      imprintDraft: {
        guardianName: "Harbor",
        heatScore: 0.8,
        id: 27,
        preferredName: "friend",
        projectId: null,
        status: "draft",
        userId: "u1",
      },
      name: "Harbor",
      personaDraft: "Review me safely.",
    });
    rejectImprintProposalMock.mockRejectedValue(
      Object.assign(new Error("blocked"), {
        response: { data: { detail: "imprint not found" } },
      })
    );

    render(<ImprintReviewPanel />);

    await screen.findByText("Proposal available for review");
    await user.click(screen.getByRole("button", { name: "Reject" }));

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "imprint not found"
    );
  });
});
