import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import PersonaStudioPage from "../PersonaStudioPage";
import { personaStudioApiMock, resetPersonaStudioApiMock } from "./personaStudioApiMock";

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

describe("Persona Studio two-pane layout", () => {
  it("renders the editor region and the right rail side by side", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const layout = within(shell).getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const railLane = within(layout).getByTestId("persona-studio-rail-lane");

    expect(configurationLane).toBeVisible();
    expect(railLane).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-editor")).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-profile-selector")).toBeVisible();
    expect(within(railLane).getByTestId("persona-studio-rail")).toBeVisible();
  });

  it("renders the Draft Preview heading and consolidated safety row in the panel header", () => {
    renderPage();

    const previewPanel = screen.getByTestId("persona-preview-panel");
    const header = within(previewPanel).getByTestId("persona-preview-panel-header");

    expect(within(header).getByRole("heading", { name: "Draft Preview" })).toBeVisible();
    expect(within(header).getByText(/test before saving/i)).toBeVisible();
    expect(within(header).getByTestId("persona-preview-panel-safety-row")).toHaveTextContent(
      /temporary preview\. not saved to chat history/i
    );
  });

  it("keeps the right rail visible while the editor scrolls", () => {
    renderPage();

    const layout = screen.getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const railLane = within(layout).getByTestId("persona-studio-rail-lane");
    const previewPanel = screen.getByTestId("persona-preview-panel");

    expect(configurationLane).toHaveClass("overflow-y-auto");
    expect(previewPanel).toBeVisible();
    expect(railLane).toHaveClass("lg:sticky");
  });

  it("preserves the existing Persona Studio tab navigation", async () => {
    const user = userEvent.setup();
    renderPage();

    const tabs = within(screen.getByTestId("persona-studio-tabs")).getAllByRole("button");
    const tabNames = tabs.map((tab) => tab.textContent?.trim());
    expect(tabNames).toEqual([
      "Identity",
      "Model",
      "Voice",
      "Prompt",
      "Tools",
      "Retrieval",
      "Truth Matrix",
    ]);

    await user.click(screen.getByRole("button", { name: /^voice$/i }));
    expect(screen.getByRole("button", { name: /^voice$/i })).toHaveAttribute(
      "data-state",
      "active"
    );

    await user.click(screen.getByRole("button", { name: /^retrieval$/i }));
    expect(screen.getByRole("button", { name: /^retrieval$/i })).toHaveAttribute(
      "data-state",
      "active"
    );
  });

  it("does not call chat, thread, or memory write APIs on initial render", () => {
    renderPage();

    expect(personaStudioApiMock.createPersonaProfile).not.toHaveBeenCalled();
    expect(personaStudioApiMock.updatePersonaProfile).not.toHaveBeenCalled();
  });

  it("does not persist the preview panel content across remounts", () => {
    const firstRender = renderPage();

    expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
      /no preview turns yet/i
    );

    firstRender.unmount();
    renderPage();

    expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
      /no preview turns yet/i
    );
  });

  it("renders the right rail with Preview | Diagnostics tabs and Preview as default", () => {
    renderPage();

    const tablist = screen.getByTestId("persona-studio-rail-tabs");
    expect(tablist).toHaveAttribute("role", "tablist");

    const railTabs = within(tablist).getAllByRole("tab");
    const tabNames = railTabs.map((tab) => tab.textContent?.trim());
    expect(tabNames).toEqual(["Preview", "Diagnostics"]);
    expect(railTabs[0]).toHaveAttribute("aria-selected", "true");
    expect(railTabs[1]).toHaveAttribute("aria-selected", "false");
  });

  it("switches the rail between Preview and Diagnostics", async () => {
    const user = userEvent.setup();
    renderPage();

    expect(screen.getByTestId("persona-preview-panel")).toBeVisible();

    await user.click(screen.getByRole("tab", { name: /^diagnostics$/i }));
    expect(screen.getByRole("tab", { name: /^diagnostics$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("persona-studio-rail-diagnostics-panel")).toBeVisible();

    await user.click(screen.getByRole("tab", { name: /^preview$/i }));
    expect(screen.getByRole("tab", { name: /^preview$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("persona-preview-panel")).toBeVisible();
  });

  it("renders the compact inline profile trigger inside the configuration lane with profile text", () => {
    renderPage();

    const layout = screen.getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId(
      "persona-studio-configuration-lane"
    );

    const trigger = within(configurationLane).getByTestId(
      "persona-studio-profile-selector-trigger"
    );

    expect(
      within(configurationLane).getByTestId(
        "persona-studio-profile-selector-trigger-name"
      )
    ).toHaveTextContent(/guardian default/i);
    expect(trigger.querySelector("svg")).toBeNull();

    expect(
      within(configurationLane).getByTestId("persona-studio-action-save")
    ).toBeInTheDocument();
    expect(
      within(configurationLane).getByTestId("persona-studio-action-save-as-new")
    ).toBeInTheDocument();
    expect(
      within(configurationLane).getByTestId("persona-studio-action-reset")
    ).toBeInTheDocument();
    expect(
      within(configurationLane).getByTestId("persona-studio-action-reset-all")
    ).toBeInTheDocument();

    expect(
      screen.getAllByRole("button", { name: /^reset local studio data$/i })
    ).toHaveLength(1);

    expect(
      screen.queryByRole("button", { name: /^reset all data$/i })
    ).not.toBeInTheDocument();
  });

  it("applies the Persona Studio action material tiers to tray and preview controls", () => {
    renderPage();

    expect(screen.getByTestId("persona-studio-profile-selector-trigger")).toHaveAttribute(
      "data-ps-material",
      "selector"
    );
    expect(screen.getByTestId("persona-studio-action-save")).toHaveAttribute(
      "data-ps-material",
      "primary"
    );
    expect(screen.getByTestId("persona-studio-action-save-as-new")).toHaveAttribute(
      "data-ps-material",
      "secondary"
    );
    expect(screen.getByTestId("persona-studio-action-reset")).toHaveAttribute(
      "data-ps-material",
      "reset"
    );
    expect(screen.getByTestId("persona-studio-action-reset-all")).toHaveAttribute(
      "data-ps-material",
      "reset"
    );
    expect(screen.getByRole("button", { name: /^send$/i })).toHaveAttribute(
      "data-ps-material",
      "primary"
    );
    expect(
      screen.getByRole("button", { name: /clear preview session/i })
    ).toHaveAttribute("data-ps-material", "secondary");
  });
});
