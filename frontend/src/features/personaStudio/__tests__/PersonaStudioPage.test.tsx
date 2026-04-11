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
    expect(screen.queryByTestId("persona-studio-diagnostics")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^profiles$/i })).toHaveAttribute(
      "data-state",
      "active"
    );
  });

  it("renders the preview harness in the main editor", () => {
    renderPage();

    expect(screen.getByTestId("persona-studio-preview-harness")).toBeVisible();
    expect(screen.getByText(/preview-only \/ ephemeral/i)).toBeVisible();
    expect(screen.getByText(/uses the current draft, including unsaved edits/i)).toBeVisible();
  });

  it("appends preview exchanges from canned prompt chips", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^coding$/i }));

    const transcript = screen.getByTestId("persona-studio-preview-transcript");
    expect(within(transcript).getByText(/^coding$/i)).toBeVisible();
    expect(within(transcript).getByText(/local preview summary/i)).toBeVisible();
  });

  it("appends a typed preview prompt to the local transcript", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(
      screen.getByRole("textbox", { name: /preview prompt/i }),
      "Summarize the plan"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-studio-preview-transcript");
    expect(within(transcript).getByText(/summarize the plan/i)).toBeVisible();
    expect(within(transcript).getByText(/local preview summary/i)).toBeVisible();
  });

  it("appends a deterministic assistant preview summary after a prompt", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^planning$/i }));

    const transcript = screen.getByTestId("persona-studio-preview-transcript");
    expect(within(transcript).getByText(/local preview summary/i)).toBeVisible();
    expect(within(transcript).getByText(/draft-aware/i)).toBeVisible();
    expect(within(transcript).getByText(/guardian default/i)).toBeVisible();
    expect(within(transcript).getByText(/openai \/ gpt-4o/i)).toBeVisible();
    expect(within(transcript).getByText(/0\.7/i)).toBeVisible();
  });

  it("reflects unsaved draft edits in the assistant preview summary", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.clear(screen.getByPlaceholderText("Enter persona name"));
    await user.type(screen.getByPlaceholderText("Enter persona name"), "Shadow Guardian");
    await user.click(screen.getByRole("button", { name: /^casual help$/i }));

    const transcript = screen.getByTestId("persona-studio-preview-transcript");
    expect(within(transcript).getByText(/shadow guardian/i)).toBeVisible();
    expect(within(transcript).getByText(/local preview summary/i)).toBeVisible();
  });

  it("can clear the local preview transcript", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^research$/i }));
    expect(screen.getByTestId("persona-studio-preview-transcript")).toHaveTextContent(
      /local preview summary/i
    );

    await user.click(screen.getByRole("button", { name: /clear preview/i }));

    expect(screen.getByTestId("persona-studio-preview-transcript")).toHaveTextContent(
      /no preview messages yet/i
    );
  });

  it("does not persist preview messages across remounts", async () => {
    const user = userEvent.setup();
    const firstRender = renderPage();

    await user.click(screen.getByRole("button", { name: /^coding$/i }));
    expect(screen.getByTestId("persona-studio-preview-transcript")).toHaveTextContent(
      /local preview summary/i
    );

    firstRender.unmount();
    renderPage();

    expect(screen.getByTestId("persona-studio-preview-transcript")).toHaveTextContent(
      /no preview messages yet/i
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
    expect(screen.queryByTestId("persona-studio-utility-profiles-panel")).not.toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-diagnostics")).toHaveAttribute("data-state", "active");
    expect(screen.getByText("Save Status")).toBeVisible();
    expect(screen.getByText("Effective Config")).toBeVisible();
    expect(screen.getByText("Debug Log")).toBeVisible();

    await user.click(screen.getByRole("button", { name: /^profiles$/i }));

    expect(screen.getByTestId("persona-studio-utility-profiles-panel")).toHaveAttribute(
      "data-state",
      "active"
    );
    expect(screen.queryByTestId("persona-studio-diagnostics")).not.toBeInTheDocument();
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
