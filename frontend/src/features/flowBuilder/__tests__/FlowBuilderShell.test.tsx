/**
 * Flow Builder Shell Tests
 *
 * Tests for the fixture-backed Flow Builder shell prototype.
 * Validates that the prototype renders fixture data correctly
 * and does not expose live execution controls.
 *
 * NOT runtime proof tests. These test fixture rendering only.
 */

import { describe, it, expect } from "vitest";
import { render, screen, within } from "@testing-library/react";
import { FlowBuilderShell } from "../FlowBuilderShell";
import { flowBuilderFixture } from "../fixtures";

describe("FlowBuilderShell", () => {
  it("renders fixture title in header", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const header = screen.getByRole("heading", { level: 1 });
    expect(header).toHaveTextContent("Flow Builder Shell Prototype");
  });

  it("renders draft title from fixture", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("Lead Qualification Flow")).toBeInTheDocument();
  });

  it("renders starter card", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByRole("heading", { level: 3, name: "Starter" })).toBeInTheDocument();
    expect(screen.getByText("Manual trigger")).toBeInTheDocument();
  });

  it("renders semantic extract step", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("Extract lead fields")).toBeInTheDocument();
  });

  it("renders semantic summarize step", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("Summarize qualification reasoning")).toBeInTheDocument();
  });

  it("renders conditional container", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("High score check")).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Then branch/i })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: /Else branch/i })).toBeInTheDocument();
  });

  it("renders notification action step", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("Send qualification summary")).toBeInTheDocument();
  });

  it("renders four top-level ordered steps", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("4 total steps")).toBeInTheDocument();
  });

  it("renders variable chips", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getAllByText("Contact Name")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Company")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Email Address")[0]).toBeInTheDocument();
    expect(screen.getAllByText("Qualification Score")[0]).toBeInTheDocument();
  });

  it("marks sensitive chip appropriately", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const sensitiveChip = document.querySelector(".fb-chip-sensitive");
    expect(sensitiveChip).toBeInTheDocument();
    expect(sensitiveChip?.textContent).toContain("Email Address");
  });

  it("renders validation warning", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText(/permission_risk/i)).toBeInTheDocument();
    expect(screen.getByText(/Email address output is marked sensitive/i)).toBeInTheDocument();
  });

  it("renders validation warning count", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText(/Warnings: 2/)).toBeInTheDocument();
  });

  it("renders TestRun summary", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("test-run:sample-001")).toBeInTheDocument();
    expect(screen.getByText("TestRun")).toBeInTheDocument();
    const testRunSection = screen.getByText("test-run:sample-001").closest(".fb-test-run-section");
    expect(testRunSection).not.toBeNull();
    expect(within(testRunSection as HTMLElement).getByText("completed")).toBeInTheDocument();
  });

  it("renders Activation summary with paused state", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("activation:sample-001")).toBeInTheDocument();
    expect(screen.getByText("Activation")).toBeInTheDocument();
    const activationSection = screen
      .getByText("activation:sample-001")
      .closest(".fb-activation-section");
    expect(activationSection).not.toBeNull();
    expect(within(activationSection as HTMLElement).getByText("paused")).toBeInTheDocument();
  });

  it("renders RunReceipt summary", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("run-receipt:sample-001")).toBeInTheDocument();
    expect(screen.getByText("Run Receipt")).toBeInTheDocument();
  });

  it("renders step receipts with completed and skipped states", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getAllByText("completed").length).toBeGreaterThan(0);
    expect(screen.getAllByText("skipped").length).toBeGreaterThan(0);
    expect(screen.getByText(/Branch: else/)).toBeInTheDocument();
  });

  it("renders activity events", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("draft_created")).toBeInTheDocument();
    expect(screen.getByText("draft_validated")).toBeInTheDocument();
    expect(screen.getByText("test_run_started")).toBeInTheDocument();
    expect(screen.getByText("step_completed")).toBeInTheDocument();
    expect(screen.getByText("step_skipped")).toBeInTheDocument();
    expect(screen.getByText("run_completed")).toBeInTheDocument();
    expect(screen.getByText("receipt_persisted")).toBeInTheDocument();
    expect(screen.getByText("activation_paused")).toBeInTheDocument();
  });

  it("does not expose live execution controls with 'Run now' text", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.queryByText(/^Run now$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Activate now$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^Execute$/i)).not.toBeInTheDocument();
  });

  it("exposes disabled prototype-only buttons instead", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const prototypeButtons = screen.getAllByRole("button", { name: /Prototype only/i });
    expect(prototypeButtons.length).toBeGreaterThan(0);
  });

  it("renders prototype banner warning", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText(/No execution, persistence, or API wiring/i)).toBeInTheDocument();
  });

  it("renders step count", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText(/\d+ total steps/)).toBeInTheDocument();
  });

  it("renders validation eligibility information", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText("TestRun Eligible")).toBeInTheDocument();
    expect(screen.getByText("Activation Eligible")).toBeInTheDocument();
  });

  it("renders shell footer with prototype disclaimer", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const footer = screen.getByText(/Prototype only.*Fixtures are not runtime proof/i);
    expect(footer).toBeInTheDocument();
  });

  it("supports custom className prop", () => {
    const { container } = render(
      <FlowBuilderShell fixture={flowBuilderFixture} className="custom-test-class" />
    );

    expect(container.firstChild).toHaveClass("custom-test-class");
  });

  it("uses default fixture when no fixture prop provided", () => {
    render(<FlowBuilderShell />);

    expect(screen.getByText("Lead Qualification Flow")).toBeInTheDocument();
  });

  it("renders semantic step kind badge", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const semanticBadges = screen.getAllByText(/semantic:/);
    expect(semanticBadges.length).toBeGreaterThan(0);
  });

  it("renders condition expression details", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    expect(screen.getByText(/step:extract-leads-001\.output\.qualification_score/)).toBeInTheDocument();
    expect(screen.getByText("greater_than")).toBeInTheDocument();
    expect(
      screen.getByText((_, node) => node?.classList.contains("fb-conditional-condition") && node.textContent?.includes("70"))
    ).toBeInTheDocument();
  });

  it("renders step receipts with semantic metadata", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const semanticMetadata = document.querySelectorAll(".fb-step-receipt-outcome");
    expect(semanticMetadata.length).toBeGreaterThan(0);
  });

  it("renders activity event evidence references", () => {
    render(<FlowBuilderShell fixture={flowBuilderFixture} />);

    const evidenceIndicators = document.querySelectorAll(".fb-event-evidence");
    expect(evidenceIndicators.length).toBeGreaterThan(0);
  });
});
