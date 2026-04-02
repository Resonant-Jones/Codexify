import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, test, vi } from "vitest";

import useImprintZero from "@/imprint/useImprintZero";
import {
  fetchImprintStatus,
  fetchSystemDocs,
  fetchSystemPromptSummary,
  requestImprintProposal,
} from "@/imprint/api";

vi.mock("@/imprint/api", () => ({
  acceptImprint: vi.fn(),
  fetchImprintStatus: vi.fn(),
  fetchSystemDocs: vi.fn(),
  fetchSystemPromptSummary: vi.fn(),
  rejectImprint: vi.fn(),
  requestImprintProposal: vi.fn(),
  toggleSystemDocApi: vi.fn(),
  updatePersonaApi: vi.fn(),
}));

const fetchImprintStatusMock = vi.mocked(fetchImprintStatus);
const fetchSystemPromptSummaryMock = vi.mocked(fetchSystemPromptSummary);
const fetchSystemDocsMock = vi.mocked(fetchSystemDocs);
const requestImprintProposalMock = vi.mocked(requestImprintProposal);

describe("useImprintZero", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    fetchImprintStatusMock.mockResolvedValue({
      imprint: null,
      persona: null,
      system_prompt_meta: {
        docs_count: 1,
        estimated_tokens: 1200,
      },
    });
    fetchSystemPromptSummaryMock.mockResolvedValue({
      estimated_tokens_total: 1200,
      threshold: {
        warn_tokens: 6000,
        hard_tokens: 8000,
        status: "ok",
      },
      docs_count: 1,
      warnings: [],
    });
    fetchSystemDocsMock.mockResolvedValue({ docs: [] });
  });

  test("surfaces backend proposal truth from the runtime path", async () => {
    const backendPromptMetadata = {
      generator_version: "imprint-proposal-v1",
      heat_score: 0.73,
      persona_hints: ["stay grounded"],
      prompt_hints: ["ask clarifying questions"],
      requested_depth: "deep",
    };

    requestImprintProposalMock.mockResolvedValue({
      imprint_draft: {
        guardian_name: "Harbor",
        heat_score: 0.73,
        id: 21,
        preferred_name: "friend",
        project_id: 7,
        status: "draft",
        user_id: "u1",
      },
      name: "Harbor",
      persona_draft: "Respond with clear structure and warmer phrasing.",
      prompt_metadata: backendPromptMetadata,
      proposal: {
        generator_version: "imprint-proposal-v1",
        persona_draft: "Respond with clear structure and warmer phrasing.",
        preferred_name: "friend",
        project_id: 7,
        proposal_hash: "proposal-hash-abcdef",
        proposal_name: "Harbor",
        proposal_version: 1,
        prompt_metadata: backendPromptMetadata,
        scope_kind: "project_scoped",
        snapshot_hash: "snapshot-hash-123456",
        snapshot_version: 4,
        user_id: "u1",
      },
    });

    const { result } = renderHook(() => useImprintZero());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.generateProposal();
    });

    expect(requestImprintProposalMock).toHaveBeenCalledTimes(1);
    expect(result.current.proposal?.name).toBe("Harbor");
    expect(result.current.proposal?.persona_draft).toBe(
      "Respond with clear structure and warmer phrasing."
    );
    expect(result.current.proposal?.proposal?.proposal_name).toBe("Harbor");
    expect(result.current.proposal?.proposal?.generator_version).toBe(
      "imprint-proposal-v1"
    );
    expect(result.current.proposal?.proposal?.proposal_hash).toBe(
      "proposal-hash-abcdef"
    );
    expect(result.current.proposal?.prompt_metadata).toEqual(
      backendPromptMetadata
    );
  });

  test("surfaces backend failures without inventing proposal truth", async () => {
    requestImprintProposalMock.mockRejectedValue(
      new Error("backend unavailable")
    );

    const { result } = renderHook(() => useImprintZero());

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });

    await act(async () => {
      await result.current.generateProposal();
    });

    expect(requestImprintProposalMock).toHaveBeenCalledTimes(1);
    expect(result.current.error).toBe("backend unavailable");
    expect(result.current.proposal).toBeNull();
  });
});
