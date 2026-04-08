import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import PersonalFactsPanel from "@/features/settings/components/PersonalFactsPanel";

describe("PersonalFactsPanel", () => {
  it("renders the full lifecycle contract with quarantine, verified, and history sections", () => {
    render(<PersonalFactsPanel />);

    expect(screen.getByTestId("personal-facts-panel")).toBeInTheDocument();
    expect(screen.getByTestId("personal-facts-guardrail")).toBeInTheDocument();
    expect(screen.getByText("Quarantine before trust")).toBeInTheDocument();
    expect(
      screen.getByText(
        "Candidate facts must never participate in retrieval, prompt assembly, or runtime behavior. Only user-approved, verified, active facts are runtime-eligible."
      )
    ).toBeInTheDocument();
    expect(screen.getByText("Candidates")).toBeInTheDocument();
    expect(screen.getByText("Verified")).toBeInTheDocument();
    expect(screen.getByText("History")).toBeInTheDocument();
    expect(screen.getByText("Not runtime-trusted")).toBeInTheDocument();
    expect(screen.getByText("Runtime eligible")).toBeInTheDocument();
    expect(screen.getByText("Before / after")).toBeInTheDocument();

    expect(screen.getByTestId("personal-facts-candidate-location")).toHaveTextContent(
      "Confidence 91%"
    );
    expect(screen.getByTestId("personal-facts-verified-timezone")).toHaveTextContent(
      "Evidence count"
    );
    expect(screen.getByTestId("personal-facts-history-location")).toHaveTextContent(
      "User updated the current city after moving."
    );

    const candidateCard = screen.getByTestId("personal-facts-candidate-location");
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

    const verifiedCard = screen.getByTestId("personal-facts-verified-timezone");
    expect(
      within(verifiedCard).getByRole("button", { name: "Amend" })
    ).toBeInTheDocument();
    expect(
      within(verifiedCard).getByRole("button", { name: "View evidence" })
    ).toBeInTheDocument();
    expect(
      within(verifiedCard).getByRole("button", { name: "Retire" })
    ).toBeInTheDocument();
  });
});
