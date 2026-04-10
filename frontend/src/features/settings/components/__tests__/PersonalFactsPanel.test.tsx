import {
  cleanup,
  fireEvent,
  render,
  screen,
  within,
} from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import PersonalFactsPanel from "@/features/settings/components/PersonalFactsPanel";
import type {
  PersonalFactCandidateView,
  PersonalFactHistoryView,
  PersonalFactVerifiedView,
  UsePersonalFactsResult,
} from "@/features/settings/hooks/usePersonalFacts";

const usePersonalFactsMock = vi.hoisted(() => vi.fn());

vi.mock("@/features/settings/hooks/usePersonalFacts", () => ({
  default: usePersonalFactsMock,
}));

function createCandidateView(
  overrides: Partial<PersonalFactCandidateView> = {}
): PersonalFactCandidateView {
  return {
    confidenceLabel: "91% confidence",
    evidence: [
      {
        confidence: 0.87,
        created_at: "2026-04-02T14:17:00Z",
        evidence_meta: null,
        excerpt: "User referred to New York during the onboarding check-in.",
        fact_id: 11,
        id: 501,
        modality: "text",
        source_message_id: 77,
        source_type: "runtime_extraction",
      },
    ],
    evidenceCount: 1,
    evidenceSummary:
      "runtime_extraction · text: User referred to New York during the onboarding check-in.",
    fact: {
      confidence: 0.91,
      created_at: "2026-04-02T14:18:00Z",
      id: 11,
      is_active: true,
      key: "timezone",
      last_confirmed_at: null,
      status: "candidate",
      updated_at: "2026-04-02T14:18:00Z",
      user_id: "user-1",
      value: "America/New_York",
    },
    reviewPosture: "High confidence, but still quarantined until user approval.",
    runtimePosture:
      "Quarantined only. Not eligible for retrieval, prompt assembly, or runtime behavior.",
    ...overrides,
  };
}

function createVerifiedView(
  overrides: Partial<PersonalFactVerifiedView> = {}
): PersonalFactVerifiedView {
  return {
    confidenceLabel: "97% confidence",
    evidence: [
      {
        confidence: 0.96,
        created_at: "2026-04-04T09:02:00Z",
        evidence_meta: null,
        excerpt: "User signed messages with the name Ari.",
        fact_id: 22,
        id: 701,
        modality: "text",
        source_message_id: 81,
        source_type: "reviewed_note",
      },
      {
        confidence: 0.89,
        created_at: "2026-04-05T13:45:00Z",
        evidence_meta: null,
        excerpt: "Consistent follow-up note confirmed the same preferred name.",
        fact_id: 22,
        id: 702,
        modality: "text",
        source_message_id: 82,
        source_type: "reviewed_note",
      },
    ],
    evidenceCount: 2,
    evidenceSummary:
      "reviewed_note · text: User signed messages with the name Ari. (+1 more)",
    fact: {
      confidence: 0.97,
      created_at: "2026-04-04T09:00:00Z",
      id: 22,
      is_active: true,
      key: "preferred_name",
      last_confirmed_at: "2026-04-04T09:02:00Z",
      status: "verified",
      updated_at: "2026-04-05T13:45:00Z",
      user_id: "user-1",
      value: "Ari",
    },
    runtimePosture: "Runtime eligible while active and verified.",
    updatedAtLabel: "Apr 5, 2026, 9:45 AM",
    ...overrides,
  };
}

function createHistoryView(
  overrides: Partial<PersonalFactHistoryView> = {}
): PersonalFactHistoryView {
  return {
    action: "value_updated",
    after: "Ari",
    before: "Arielle",
    factId: 22,
    fieldLabel: "Value",
    id: "22-9001",
    key: "preferred_name",
    kind: "amendment",
    reason: "User corrected the preferred name.",
    timestamp: "2026-04-05T13:45:00Z",
    timestampLabel: "Apr 5, 2026, 9:45 AM",
    ...overrides,
  };
}

function renderPanel(overrides: Partial<UsePersonalFactsResult> = {}) {
  const state: UsePersonalFactsResult = {
    approveCandidate: vi.fn(async () => true),
    amendVerified: vi.fn(async () => true),
    busyFactId: null,
    candidates: [createCandidateView()],
    deleteCandidate: vi.fn(async () => true),
    disputeCandidate: vi.fn(async () => true),
    editThenApproveCandidate: vi.fn(async () => true),
    error: null,
    hasLoaded: true,
    history: [createHistoryView()],
    loading: false,
    reload: vi.fn(async () => {}),
    retireVerified: vi.fn(async () => true),
    quarantinedCount: 1,
    runtimePolicySummary:
      "Only verified, active facts are runtime-eligible. Candidate facts stay quarantined, and retired or disputed facts remain outside runtime use.",
    verified: [createVerifiedView()],
    verifiedCount: 1,
    ...overrides,
  };

  usePersonalFactsMock.mockReturnValue(state);

  render(<PersonalFactsPanel />);

  return state;
}

describe("PersonalFactsPanel", () => {
  beforeEach(() => {
    usePersonalFactsMock.mockReset();
  });

  it(
    "renders the compact lifecycle shell with real data and nested section tabs",
    () => {
    renderPanel();

    expect(screen.getByTestId("personal-facts-panel")).toBeInTheDocument();
    expect(screen.getByTestId("personal-facts-summary")).toBeInTheDocument();
    expect(screen.getByTestId("personal-facts-guardrail")).toBeInTheDocument();
    expect(screen.getByText("Quarantine before trust")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Candidate facts must never participate in retrieval, prompt assembly, or runtime behavior. Only user-approved, verified, active facts are runtime-eligible."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Personal Facts")).toBeInTheDocument();
    expect(screen.getByText("Runtime policy")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Only verified, active facts are runtime-eligible. Candidate facts stay quarantined, and retired or disputed facts remain outside runtime use."
      )
    ).toBeInTheDocument();

    expect(
      screen.getByRole("tablist", { name: "Personal facts sections" })
    ).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "Candidates" })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByRole("tab", { name: "Verified" })).toBeInTheDocument();
    expect(screen.getByRole("tab", { name: "History" })).toBeInTheDocument();

    const candidateCard = screen.getByTestId("personal-facts-candidate-11");
    expect(candidateCard).toBeInTheDocument();
    expect(candidateCard).toHaveTextContent("timezone");
    expect(candidateCard).toHaveTextContent("America/New_York");
    expect(candidateCard).toHaveTextContent("Not runtime-trusted");
    expect(candidateCard).toHaveTextContent("Evidence / source summary");

    expect(
      within(candidateCard).getByRole("button", { name: "Approve" })
    ).toBeInTheDocument();
    expect(
      within(candidateCard).getByRole("button", {
        name: "Edit then approve",
      })
    ).toBeInTheDocument();
    expect(
      within(candidateCard).getByRole("button", { name: "Dispute" })
    ).toBeInTheDocument();
    expect(
      within(candidateCard).getByRole("button", { name: "Delete" })
    ).toBeInTheDocument();
    },
    15000
  );

  it(
    "switches sections, reveals evidence trails, and wires edit actions",
    async () => {
    const user = userEvent.setup();
    const state = renderPanel();

    await user.click(screen.getByRole("tab", { name: "Verified" }));
    const verifiedCard = screen.getByTestId("personal-facts-verified-22");
    expect(verifiedCard).toHaveTextContent("Runtime eligible");
    expect(
      within(verifiedCard).getByRole("button", { name: "View evidence" })
    ).toBeInTheDocument();

    await user.click(
      within(verifiedCard).getByRole("button", { name: "View evidence" })
    );
    expect(within(verifiedCard).getByText("Evidence trail")).toBeInTheDocument();
    expect(
      within(verifiedCard).getByText("User signed messages with the name Ari.")
    ).toBeInTheDocument();

    await user.click(within(verifiedCard).getByRole("button", { name: "Amend" }));
    expect(screen.getByRole("button", { name: "Amend verified fact" })).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Value"));
    await user.type(screen.getByLabelText("Value"), "Arielle");
    await user.clear(screen.getByLabelText("Reason"));
    await user.type(screen.getByLabelText("Reason"), "User corrected the preferred name.");
    await user.click(screen.getByRole("button", { name: "Amend verified fact" }));
    expect(state.amendVerified).toHaveBeenCalledWith(
      22,
      "Arielle",
      "User corrected the preferred name."
    );

    await user.click(screen.getByRole("tab", { name: "Candidates" }));
    const candidateCard = screen.getByTestId("personal-facts-candidate-11");
    await user.click(
      within(candidateCard).getByRole("button", { name: "Edit then approve" })
    );
    expect(
      screen.getByRole("button", { name: "Edit candidate then approve" })
    ).toBeInTheDocument();
    await user.clear(screen.getByLabelText("Value"));
    await user.type(screen.getByLabelText("Value"), "America/Chicago");
    await user.clear(screen.getByLabelText("Reason"));
    await user.type(
      screen.getByLabelText("Reason"),
      "Confirmed after timezone correction."
    );
    await user.click(
      screen.getByRole("button", { name: "Edit candidate then approve" })
    );
    expect(state.editThenApproveCandidate).toHaveBeenCalledWith(
      11,
      "America/Chicago",
      "Confirmed after timezone correction."
    );
  },
    20000
  );

  it(
    "shows generic loading and empty states without fake personal data",
    () => {
    renderPanel({
      candidates: [],
      hasLoaded: false,
      history: [],
      loading: true,
      verified: [],
      quarantinedCount: 0,
      verifiedCount: 0,
    });

    expect(screen.getByRole("status")).toHaveTextContent(
      "Loading live candidates…"
    );
    expect(screen.getByRole("tab", { name: "Candidates" })).toHaveAttribute(
      "aria-selected",
      "true"
    );

    cleanup();
    usePersonalFactsMock.mockReset();
    renderPanel({
      candidates: [],
      hasLoaded: true,
      history: [],
      loading: false,
      verified: [],
      quarantinedCount: 0,
      verifiedCount: 0,
    });

    expect(screen.getByText("No candidate facts yet")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "Verified" }));
    expect(screen.getByText("No verified facts yet")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("tab", { name: "History" }));
    expect(screen.getByText("No history entries yet")).toBeInTheDocument();
  },
    15000
  );
});
