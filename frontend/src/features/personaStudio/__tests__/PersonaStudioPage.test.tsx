import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import PersonaStudioPage from "../PersonaStudioPage";
import { resetPersonaStudioApiMock } from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock();
});

function renderPage() {
  return render(<PersonaStudioPage />);
}

describe("Persona Studio Page", () => {
  it("renders the utility pane with Profiles active by default", () => {
    renderPage();

    expect(screen.getByTestId("persona-studio-utility-pane")).toBeVisible();
    expect(screen.getByTestId("persona-studio-utility-profiles-panel")).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByTestId("persona-studio-diagnostics")).toHaveAttribute(
      "data-state",
      "inactive"
    );
    expect(screen.getByRole("button", { name: /^profiles$/i })).toHaveAttribute(
      "data-state",
      "active"
    );
  });

  it("can collapse and reopen the utility pane", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /hide utility pane/i }));
    expect(screen.queryByTestId("persona-studio-utility-pane")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /show utility pane/i })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /show utility pane/i }));
    expect(screen.getByTestId("persona-studio-utility-pane")).toBeVisible();
  });

  it("switches the utility pane between Profiles and Diagnostics", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /diagnostics/i }));

    expect(screen.getByRole("button", { name: /^diagnostics$/i })).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByTestId("persona-studio-utility-profiles-panel")).toHaveAttribute(
      "data-state",
      "inactive"
    );
    expect(screen.getByTestId("persona-studio-diagnostics")).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByText("Save Status")).toBeVisible();
    expect(screen.getByText("Effective Config")).toBeVisible();
    expect(screen.getByText("Debug Log")).toBeVisible();

    await user.click(screen.getByRole("button", { name: /^profiles$/i }));

    expect(screen.getByTestId("persona-studio-utility-profiles-panel")).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.getByTestId("persona-studio-diagnostics")).toHaveAttribute(
      "data-state",
      "inactive"
    );
  });

  it("renders the section tabs in the header area", () => {
    renderPage();

    const header = screen.getByTestId("persona-studio-page-header");
    const sectionTabs = within(header).getByTestId("persona-studio-section-tabs");
    expect(sectionTabs).toBeVisible();
    expect(within(screen.getByTestId("persona-studio-editor")).queryByTestId("persona-studio-section-tabs")).not.toBeInTheDocument();
  });

  it("keeps the active profile presentation only in the main editor", () => {
    renderPage();

    expect(screen.getAllByTestId("persona-studio-active-profile-summary")).toHaveLength(1);
    expect(
      within(screen.getByTestId("persona-studio-utility-pane")).queryByTestId(
        "persona-studio-active-profile-summary"
      )
    ).not.toBeInTheDocument();
  });
});
