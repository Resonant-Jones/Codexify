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
  it("renders the editor region and the Persona Preview panel side by side", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const layout = within(shell).getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const previewLane = within(layout).getByTestId("persona-preview-lane");

    expect(configurationLane).toBeVisible();
    expect(previewLane).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-editor")).toBeVisible();
  });

  it("renders the Persona Preview heading and boundary chips in the panel header", () => {
    renderPage();

    const previewPanel = screen.getByTestId("persona-preview-panel");
    const header = within(previewPanel).getByTestId("persona-preview-panel-header");

    expect(within(header).getByRole("heading", { name: "Persona Preview" })).toBeVisible();
    expect(within(header).getByText("Draft only")).toBeVisible();
    expect(within(header).getByText("No memory writes")).toBeVisible();
    expect(within(header).getByText("No thread persistence")).toBeVisible();
    expect(within(header).getByText(/sandboxed response tuning/i)).toBeVisible();
    expect(within(header).getByText(/isolated from guardian runtime/i)).toBeVisible();
  });

  it("keeps the Persona Preview panel visible while the editor scrolls", () => {
    renderPage();

    const layout = screen.getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const previewPanel = screen.getByTestId("persona-preview-panel");
    const previewLane = within(layout).getByTestId("persona-preview-lane");

    expect(configurationLane).toHaveClass("overflow-y-auto");
    expect(previewPanel).toBeVisible();
    expect(previewLane).toHaveClass("lg:sticky");
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
});
