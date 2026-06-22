/**
 * Tests for FactCandidateReview component.
 *
 * Covers: rendering (loading, empty, populated), approve, reject,
 * edit-before-approve, refresh, error handling, sensitive indicators.
 */

import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import FactCandidateReview from "../FactCandidateReview";

// ── Mock API helpers ──

const mockFetchPersonalFacts = vi.fn();
const mockFetchPersonalFactEvidence = vi.fn();
const mockApproveFactCandidate = vi.fn();
const mockRejectFactCandidate = vi.fn();

vi.mock("@/lib/api", () => ({
  fetchPersonalFacts: (...args: unknown[]) =>
    mockFetchPersonalFacts(...args),
  fetchPersonalFactEvidence: (...args: unknown[]) =>
    mockFetchPersonalFactEvidence(...args),
  approveFactCandidate: (...args: unknown[]) =>
    mockApproveFactCandidate(...args),
  rejectFactCandidate: (...args: unknown[]) =>
    mockRejectFactCandidate(...args),
}));

// ── Helpers ──

function makeFact(overrides: Record<string, unknown> = {}) {
  return {
    id: 1,
    user_id: "user1",
    key: "location",
    value: "NYC",
    status: "candidate",
    confidence: 0.94,
    is_active: true,
    last_confirmed_at: null,
    created_at: "2026-01-01T00:00:00Z",
    updated_at: "2026-01-01T00:00:00Z",
    guardrail_metadata: null,
    ...overrides,
  };
}

function makeEvidence(overrides: Record<string, unknown> = {}) {
  return {
    id: 10,
    fact_id: 1,
    source_message_id: 42,
    excerpt: "I live in NYC",
    modality: "text",
    confidence: 0.94,
    source_type: "runtime_extraction",
    evidence_meta: { thread_id: 7, source: "chat" },
    created_at: "2026-01-01T00:00:00Z",
    ...overrides,
  };
}

function setupMockCandidates(
  facts: ReturnType<typeof makeFact>[],
  evidencePerFact: ReturnType<typeof makeEvidence>[] = []
) {
  mockFetchPersonalFacts.mockResolvedValue(facts);
  mockFetchPersonalFactEvidence.mockImplementation((factId: number) => {
    const match = evidencePerFact.find((e) => e.fact_id === factId);
    return Promise.resolve(match ? [match] : []);
  });
}

beforeEach(() => {
  vi.clearAllMocks();
  mockFetchPersonalFacts.mockResolvedValue([]);
  mockFetchPersonalFactEvidence.mockResolvedValue([]);
  mockApproveFactCandidate.mockResolvedValue({});
  mockRejectFactCandidate.mockResolvedValue({});
});

// ── Render states ──

describe("FactCandidateReview rendering", () => {
  it("renders the component header", async () => {
    render(<FactCandidateReview />);
    expect(screen.getByText("Fact Candidates")).toBeDefined();
    expect(
      screen.getByText(/Review and approve personal facts/)
    ).toBeDefined();
  });

  it("shows loading state initially", () => {
    // Don't resolve the API call yet
    mockFetchPersonalFacts.mockReturnValue(new Promise(() => {}));
    render(<FactCandidateReview />);
    expect(screen.getByText("Loading candidates...")).toBeDefined();
  });

  it("shows empty state when no candidates", async () => {
    setupMockCandidates([]);
    render(<FactCandidateReview />);
    await waitFor(() => {
      expect(screen.getByText("No pending candidates.")).toBeDefined();
    });
  });

  it("renders candidate list with key, value, and confidence", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "location", value: "NYC", confidence: 0.94 })]);
    render(<FactCandidateReview />);
    await waitFor(() => {
      expect(screen.getByText("location")).toBeDefined();
      expect(screen.getByText("NYC")).toBeDefined();
      expect(screen.getByText("conf: 94%")).toBeDefined();
    });
  });

  it("shows evidence metadata when present", async () => {
    const fact = makeFact({ id: 1 });
    const evidence = makeEvidence({
      fact_id: 1,
      evidence_meta: { thread_id: 7, source_message_id: 42 },
    });
    setupMockCandidates([fact], [evidence]);
    render(<FactCandidateReview />);
    await waitFor(() => {
      expect(screen.getByText(/msg #42/)).toBeDefined();
      expect(screen.getByText(/thread #7/)).toBeDefined();
    });
  });

  it("shows sensitive indicator for sensitive keys", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "password", value: "secret123" })]);
    render(<FactCandidateReview />);
    await waitFor(() => {
      expect(screen.getByText("⚠ sensitive")).toBeDefined();
      expect(screen.getByText("force required")).toBeDefined();
    });
  });

  it("does not show sensitive indicator for normal keys", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "location", value: "NYC" })]);
    render(<FactCandidateReview />);
    await waitFor(() => {
      expect(screen.getByText("NYC")).toBeDefined();
    });
    expect(screen.queryByText("⚠ sensitive")).toBeNull();
  });
});

// ── Approve flow ──

describe("FactCandidateReview approve", () => {
  it("calls approveFactCandidate on approve click", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "location" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("location")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve location candidate"));
    await waitFor(() => {
      expect(mockApproveFactCandidate).toHaveBeenCalledWith(1, {
        reason: "user approved from review panel",
        value: undefined,
        force_sensitive: undefined,
      });
    });
  });

  it("removes approved candidate from list", async () => {
    setupMockCandidates([
      makeFact({ id: 1, key: "name" }),
      makeFact({ id: 2, key: "location" }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("name")).toBeDefined();
      expect(screen.getByText("location")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve name candidate"));
    await waitFor(() => {
      expect(screen.queryByText("name")).toBeNull();
      expect(screen.getByText("location")).toBeDefined();
    });
  });

  it("shows error when approve fails and keeps candidate", async () => {
    mockApproveFactCandidate.mockRejectedValue(new Error("Network error"));
    setupMockCandidates([makeFact({ id: 1, key: "location" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("location")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve location candidate"));
    await waitFor(() => {
      expect(screen.getByText("Network error")).toBeDefined();
      // Candidate should still be visible
      expect(screen.getByText("location")).toBeDefined();
    });
  });
});

// ── Reject flow ──

describe("FactCandidateReview reject", () => {
  it("calls rejectFactCandidate on reject click", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "employer" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("employer")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Reject employer candidate"));
    await waitFor(() => {
      expect(mockRejectFactCandidate).toHaveBeenCalledWith(1, {
        reason: "rejected from review panel",
      });
    });
  });

  it("removes rejected candidate from list", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "employer" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("employer")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Reject employer candidate"));
    await waitFor(() => {
      expect(screen.queryByText("employer")).toBeNull();
    });
  });

  it("shows error when reject fails and keeps candidate", async () => {
    mockRejectFactCandidate.mockRejectedValue(new Error("Reject failed"));
    setupMockCandidates([makeFact({ id: 1, key: "employer" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("employer")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Reject employer candidate"));
    await waitFor(() => {
      expect(screen.getByText("Reject failed")).toBeDefined();
      expect(screen.getByText("employer")).toBeDefined();
    });
  });
});

// ── Edit-before-approve flow ──

describe("FactCandidateReview edit before approve", () => {
  it("opens edit field on edit click", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "preference", value: "dark mode" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("dark mode")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit preference candidate"));
    await waitFor(() => {
      expect(screen.getByLabelText("Edit fact value")).toBeDefined();
    });
  });

  it("populates edit field with current value", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "preference", value: "dark mode" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("dark mode")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit preference candidate"));
    const textarea = screen.getByLabelText("Edit fact value") as HTMLTextAreaElement;
    expect(textarea.value).toBe("dark mode");
  });

  it("sends edited value on approve", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "preference", value: "dark mode" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("dark mode")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit preference candidate"));

    const textarea = screen.getByLabelText("Edit fact value") as HTMLTextAreaElement;
    fireEvent.change(textarea, {
      target: { value: "User prefers dark mode for IDE" },
    });

    fireEvent.click(
      screen.getByLabelText("Save edited value and approve")
    );

    await waitFor(() => {
      expect(mockApproveFactCandidate).toHaveBeenCalledWith(1, {
        reason: "user approved from review panel",
        value: "User prefers dark mode for IDE",
        force_sensitive: undefined,
      });
    });
  });

  it("cancel edit restores normal display", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "preference", value: "dark mode" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("dark mode")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit preference candidate"));
    expect(screen.getByLabelText("Edit fact value")).toBeDefined();

    fireEvent.click(screen.getByLabelText("Cancel editing"));
    await waitFor(() => {
      expect(screen.queryByLabelText("Edit fact value")).toBeNull();
      expect(screen.getByText("dark mode")).toBeDefined();
    });
  });
});

// ── Refresh flow ──

describe("FactCandidateReview refresh", () => {
  it("calls fetchPersonalFacts again on refresh click", async () => {
    setupMockCandidates([]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("No pending candidates.")).toBeDefined();
    });

    // Set up new data for the second call
    setupMockCandidates([makeFact({ id: 2, key: "occupation", value: "dev" })]);

    fireEvent.click(screen.getByLabelText("Refresh candidates"));
    await waitFor(() => {
      expect(screen.getByText("occupation")).toBeDefined();
    });
    // Should have been called twice: initial load + refresh
    expect(mockFetchPersonalFacts).toHaveBeenCalledTimes(2);
  });

  it("handles empty response after refresh", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "name", value: "Alex" })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("name")).toBeDefined();
    });

    // Refresh returns empty
    setupMockCandidates([]);
    fireEvent.click(screen.getByLabelText("Refresh candidates"));
    await waitFor(() => {
      expect(screen.getByText("No pending candidates.")).toBeDefined();
    });
  });
});

// ── Error handling ──

describe("FactCandidateReview error handling", () => {
  it("shows error when list fetch fails", async () => {
    mockFetchPersonalFacts.mockRejectedValue(new Error("API unavailable"));
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("API unavailable")).toBeDefined();
    });
  });

  it("shows error when approve fails and keeps candidates visible", async () => {
    mockApproveFactCandidate.mockRejectedValue(new Error("Server error"));
    setupMockCandidates([
      makeFact({ id: 1, key: "name", value: "ErrorUser" }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("name")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve name candidate"));
    await waitFor(() => {
      expect(screen.getByText("Server error")).toBeDefined();
      // Candidate still visible after failed approve
      expect(screen.getByText("name")).toBeDefined();
    });
  });

  it("shows error when reject fails and keeps candidates visible", async () => {
    mockRejectFactCandidate.mockRejectedValue(new Error("Reject error"));
    setupMockCandidates([
      makeFact({ id: 1, key: "location", value: "BadCity" }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("location")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Reject location candidate"));
    await waitFor(() => {
      expect(screen.getByText("Reject error")).toBeDefined();
      expect(screen.getByText("location")).toBeDefined();
    });
  });
});

// ── Multiple candidates ──

describe("FactCandidateReview multiple candidates", () => {
  it("renders all candidates", async () => {
    setupMockCandidates([
      makeFact({ id: 1, key: "name", value: "Sam" }),
      makeFact({ id: 2, key: "location", value: "Portland" }),
      makeFact({ id: 3, key: "occupation", value: "developer" }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("Sam")).toBeDefined();
      expect(screen.getByText("Portland")).toBeDefined();
      expect(screen.getByText("developer")).toBeDefined();
    });
  });

  it("handles mixed sensitive and normal candidates", async () => {
    setupMockCandidates([
      makeFact({ id: 1, key: "name", value: "Sam" }),
      makeFact({ id: 2, key: "password", value: "secret123" }),
      makeFact({ id: 3, key: "location", value: "NYC" }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      // Sensitive indicator on password, not on others
      const sensitiveBadges = screen.getAllByText("⚠ sensitive");
      expect(sensitiveBadges).toHaveLength(1);
      expect(screen.getByText("name")).toBeDefined();
      expect(screen.getByText("location")).toBeDefined();
    });
  });
});

// ── Guardrail metadata ──

describe("FactCandidateReview guardrail metadata", () => {
  it("renders disposition when guardrail_metadata.disposition is reviewable", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "location",
        guardrail_metadata: {
          disposition: "reviewable",
          reasons: ["import_noise"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: false,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("reviewable")).toBeDefined();
    });
  });

  it("renders promotion-blocked indicator when promotion_blocked=true", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "profession",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("promotion blocked")).toBeDefined();
      expect(screen.getByText("quarantine")).toBeDefined();
    });
  });

  it("renders review-required indicator when review_required=true", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "hobby",
        guardrail_metadata: {
          disposition: "reviewable",
          reasons: [],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: false,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("review required")).toBeDefined();
    });
  });

  it("renders not-runtime-eligible posture when runtime_eligible=false", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "name",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["low_confidence"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: false,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText(/Not runtime-eligible/)).toBeDefined();
      expect(
        screen.getByText(/candidate remains excluded/)
      ).toBeDefined();
    });
  });

  it("renders readable reason label for source_role_assistant", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "profession",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("Source role: assistant")).toBeDefined();
    });
  });

  it("renders readable reason label for import_noise", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "location",
        guardrail_metadata: {
          disposition: "reviewable",
          reasons: ["import_noise"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: false,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("Import noise")).toBeDefined();
    });
  });

  it("renders fallback label for unknown reason", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "test",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["future_reason_not_yet_defined"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(
        screen.getByText("future reason not yet defined")
      ).toBeDefined();
    });
  });

  it("renders existing content when guardrail_metadata is absent", async () => {
    setupMockCandidates([
      makeFact({ id: 1, key: "location", value: "NYC", guardrail_metadata: null }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("NYC")).toBeDefined();
      expect(screen.getByText("location")).toBeDefined();
    });
  });

  it("does not crash with malformed guardrail_metadata", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "test",
        guardrail_metadata: {
          disposition: null,
          reasons: "not-an-array",
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByText("test")).toBeDefined();
    });
  });

  it("preserves edit and reject affordances for blocked candidates, blocks ordinary approve", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "location",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant", "import_noise"],
          runtime_eligible: false,
          review_required: true,
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      // Ordinary approve is NOT shown for promotion-blocked candidates
      expect(
        screen.queryByLabelText("Approve location candidate")
      ).toBeNull();
      // Edit and reject remain available
      expect(
        screen.getByLabelText("Edit location candidate")
      ).toBeDefined();
      expect(
        screen.getByLabelText("Reject location candidate")
      ).toBeDefined();
    });
  });
});

// ── Guardrail override UI ──

describe("FactCandidateReview guardrail override", () => {
  it("promotion-blocked candidate does not show ordinary approve", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "profession",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant"],
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(
        screen.queryByLabelText("Approve profession candidate")
      ).toBeNull();
      expect(
        screen.getByText(/blocked from direct approval/)
      ).toBeDefined();
    });
  });

  it("shows override affordance when editing a blocked candidate", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "profession",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant"],
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByLabelText("Edit profession candidate")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit profession candidate"));

    await waitFor(() => {
      expect(screen.getByLabelText("Override reason")).toBeDefined();
    });
  });

  it("override action sends override_guardrail=true and override_note", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "profession",
        value: "chef",
        guardrail_metadata: {
          disposition: "quarantine",
          reasons: ["source_role_assistant"],
          promotion_blocked: true,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(screen.getByLabelText("Edit profession candidate")).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Edit profession candidate"));

    await waitFor(() => {
      expect(screen.getByLabelText("Override reason")).toBeDefined();
    });

    const noteInput = screen.getByLabelText("Override reason") as HTMLInputElement;
    fireEvent.change(noteInput, {
      target: { value: "User confirms this is their profession" },
    });

    const textarea = screen.getByLabelText("Edit fact value") as HTMLTextAreaElement;
    fireEvent.change(textarea, {
      target: { value: "professional chef" },
    });

    fireEvent.click(
      screen.getByLabelText("Save edited value and approve")
    );

    await waitFor(() => {
      expect(mockApproveFactCandidate).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          override_guardrail: true,
          override_note: "User confirms this is their profession",
          value: "professional chef",
        })
      );
    });
  });

  it("clean candidate does not send override_guardrail", async () => {
    setupMockCandidates([
      makeFact({
        id: 1,
        key: "location",
        guardrail_metadata: {
          disposition: "reviewable",
          reasons: ["import_noise"],
          promotion_blocked: false,
        },
      }),
    ]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(
        screen.getByLabelText("Approve location candidate")
      ).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve location candidate"));

    await waitFor(() => {
      const callArgs = mockApproveFactCandidate.mock.calls[0];
      expect(callArgs[1].override_guardrail).toBeUndefined();
    });
  });

  it("candidate without guardrail_metadata preserves existing approve behavior", async () => {
    setupMockCandidates([makeFact({ id: 1, key: "location", guardrail_metadata: null })]);
    render(<FactCandidateReview />);

    await waitFor(() => {
      expect(
        screen.getByLabelText("Approve location candidate")
      ).toBeDefined();
    });

    fireEvent.click(screen.getByLabelText("Approve location candidate"));

    await waitFor(() => {
      const callArgs = mockApproveFactCandidate.mock.calls[0];
      expect(callArgs[1].override_guardrail).toBeUndefined();
    });
  });
});
