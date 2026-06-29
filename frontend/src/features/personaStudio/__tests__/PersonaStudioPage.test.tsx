import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor, within } from "@testing-library/react";
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

describe("Persona Studio Page", () => {
  it("keeps the editor and right rail on one unified parent surface", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const editor = within(shell).getByTestId("persona-studio-editor");
    const header = within(shell).getByTestId("persona-studio-shell-header");
    const railLane = within(shell).getByTestId("persona-studio-rail-lane");
    const rail = within(railLane).getByTestId("persona-studio-rail");
    const previewPanel = within(rail).getByTestId("persona-preview-panel");
    const configurationLane = within(shell).getByTestId("persona-studio-configuration-lane");

    expect(shell).toBeVisible();
    expect(header).toBeVisible();
    expect(editor).toBeVisible();
    expect(railLane).toBeVisible();
    expect(rail).toBeVisible();
    expect(previewPanel).toBeVisible();
    expect(shell).toHaveClass("overflow-y-auto");
    expect(configurationLane).toHaveClass("overflow-y-auto");
    expect(screen.getByTestId("persona-studio-rail-tabs")).toBeVisible();
  });

  it("renders the primary two-lane shell with the rail on the right (Preview tab default)", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const layout = within(shell).getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const railLane = within(layout).getByTestId("persona-studio-rail-lane");
    const previewPanel = within(railLane).getByTestId("persona-preview-panel");
    const header = within(previewPanel).getByTestId("persona-preview-panel-header");
    const transcript = within(previewPanel).getByTestId("persona-preview-panel-transcript");
    const composer = within(previewPanel).getByTestId("persona-preview-panel-composer");

    expect(configurationLane).toBeVisible();
    expect(railLane).toBeVisible();
    expect(within(shell).getByRole("heading", { name: /persona studio/i })).toBeVisible();
    expect(within(shell).getByTestId("persona-studio-tabs")).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-editor")).toBeVisible();
    expect(previewPanel).toBeVisible();
    expect(header).toBeVisible();
    expect(transcript).toBeVisible();
    expect(composer).toBeVisible();
    expect(within(header).getByText("Draft Preview")).toBeVisible();
    expect(within(header).getByText(/test before saving/i)).toBeVisible();
    expect(within(header).getByTestId("persona-preview-panel-safety-row")).toHaveTextContent(
      /temporary preview\. not saved to chat history/i
    );
    expect(within(composer).getByRole("button", { name: /clear preview session/i })).toBeVisible();
    expect(screen.getByTestId("persona-preview-panel-safety-row")).toHaveTextContent(
      /temporary preview\. not saved to chat history/i
    );
    expect(
      screen.getByPlaceholderText(/send a temporary test prompt/i)
    ).toBeVisible();
  });

  it("supports a multi-turn preview transcript", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Coding");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Summarize the plan");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-preview-panel-transcript");
    expect(within(transcript).getByText(/^transcript$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 1$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 2$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 3$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 4$/i)).toBeVisible();
    expect(within(transcript).getAllByText(/^user bubble$/i).length).toBeGreaterThan(0);
    expect(within(transcript).getAllByText(/^preview block$/i).length).toBeGreaterThan(0);
    expect(within(transcript).getByText(/^coding$/i)).toBeVisible();
    expect(within(transcript).getByText(/^summarize the plan$/i)).toBeVisible();
    expect(within(transcript).getByText(/this is the first preview turn in this studio session/i)).toBeVisible();
    expect(within(transcript).getAllByText(/current draft snapshot:/i)).toHaveLength(2);
    expect(within(transcript).getByText(/this is preview turn 2 in the current studio session/i)).toBeVisible();
    expect(within(transcript).queryByText(/^ephemeral assistant$/i)).not.toBeInTheDocument();
    expect(within(transcript).getAllByTestId("persona-preview-panel-turn-row")).toHaveLength(4);
    expect(within(transcript).getAllByText(/^user bubble$/i)).toHaveLength(2);
    expect(within(transcript).getAllByText(/^preview block$/i)).toHaveLength(2);
    expect(
      within(transcript)
        .getAllByTestId("persona-preview-panel-turn-row")
        .map((row) => row.getAttribute("data-message-layout"))
    ).toEqual(["user-bubble", "preview-block", "user-bubble", "preview-block"]);
  });

  it("keeps prior turns visible and changes later replies when the draft changes", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Planning");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    await user.type(
      screen.getByRole("textbox", { name: /persona preview prompt/i }),
      "Refine the answer"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() =>
      expect(
        screen.getByTestId("persona-preview-panel-transcript")
      ).toHaveTextContent(/current draft snapshot:/i)
    );

    await user.click(screen.getByRole("button", { name: /model/i }));
    await user.selectOptions(screen.getByRole("combobox", { name: /provider/i }), "anthropic");

    await waitFor(() =>
      expect(screen.getByText(/draft changed since the last reply/i)).toBeVisible()
    );

    await user.type(
      screen.getByRole("textbox", { name: /persona preview prompt/i }),
      "Refine the answer again"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-preview-panel-transcript");
    expect(within(transcript).getByText(/^turn 1$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 2$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 3$/i)).toBeVisible();
    expect(within(transcript).getAllByText(/anthropic \/ gpt-4o/i).length).toBeGreaterThan(0);
    expect(within(transcript).getAllByText(/^earlier draft$/i).length).toBeGreaterThan(0);
    expect(within(transcript).getByText(/^current draft$/i)).toBeVisible();
  });

  it("renders draft snapshot context in each assistant reply", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Planning");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-preview-panel-transcript");
    expect(within(transcript).getByText(/current draft snapshot:/i)).toBeVisible();
    expect(within(transcript).getByText(/^guardian default$/i)).toBeVisible();
    expect(within(transcript).getByText(/^openai \/ gpt-4o$/i)).toBeVisible();
    expect(within(transcript).getByText(/^0\.7$/i)).toBeVisible();
  });

  it("clears the preview session on demand", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Research");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
      /current draft/i
    );

    await user.click(screen.getByRole("button", { name: /clear preview session/i }));

    expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
      /no preview turns yet/i
    );
  });

  it("does not persist the preview session across remounts", async () => {
    const user = userEvent.setup();
    const firstRender = renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Coding");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() =>
      expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
        /current draft snapshot:/i
      )
    );

    firstRender.unmount();
    renderPage();

    expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
      /no preview turns yet/i
    );
  });

  it("renders the truthful empty-state copy for the draft preview", () => {
    renderPage();

    const transcript = screen.getByTestId("persona-preview-panel-transcript");
    expect(
      within(transcript).getByText(/no preview turns yet\./i)
    ).toBeVisible();
  });

  it("does not touch runtime write paths or session persistence", async () => {
    const user = userEvent.setup();
    const sessionSetItemSpy = vi.spyOn(window.sessionStorage, "setItem");
    renderPage();

    await user.type(screen.getByRole("textbox", { name: /persona preview prompt/i }), "Coding");
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() =>
      expect(screen.getByTestId("persona-preview-panel-transcript")).toHaveTextContent(
        /current draft snapshot:/i
      )
    );

    expect(personaStudioApiMock.fetchPersonaProfiles).toHaveBeenCalledTimes(1);
    expect(personaStudioApiMock.createPersonaProfile).not.toHaveBeenCalled();
    expect(personaStudioApiMock.updatePersonaProfile).not.toHaveBeenCalled();
    expect(sessionSetItemSpy).not.toHaveBeenCalled();
  });

  it("switches the rail between Preview and Diagnostics tabs", async () => {
    const user = userEvent.setup();
    renderPage();

    // Default Preview tab — diagnostics not visible
    expect(screen.getByRole("button", { name: /^preview$/i })).toHaveAttribute(
      "aria-pressed",
      "true"
    );
    expect(screen.queryByTestId("persona-studio-rail-diagnostics-panel")).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /^profiles$/i })).not.toBeInTheDocument();

    // Switch to Diagnostics
    await user.click(screen.getByRole("tab", { name: /^diagnostics$/i }));
    expect(screen.getByRole("tab", { name: /^diagnostics$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("persona-studio-rail-diagnostics-panel")).toBeVisible();

    // Switch back to Preview
    await user.click(screen.getByRole("tab", { name: /^preview$/i }));
    expect(screen.getByRole("tab", { name: /^preview$/i })).toHaveAttribute(
      "aria-selected",
      "true"
    );
    expect(screen.getByTestId("persona-preview-panel")).toBeVisible();
  });

  it("renders the selector tray beneath the editor with chip tiers and no helper text", async () => {
    const user = userEvent.setup();
    renderPage();

    const selector = screen.getByTestId("persona-studio-profile-selector");
    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");

    expect(selector).toBeVisible();
    expect(selector.querySelectorAll("svg")).toHaveLength(0);
    expect(selector.querySelectorAll("p, small")).toHaveLength(0);
    expect(trigger).toHaveTextContent(/guardian default/i);
    expect(trigger).toHaveAttribute("data-persona-studio-action-tier", "utility");
    expect(trigger.querySelector("svg")).toBeNull();

    await user.click(trigger);

    expect(screen.getByTestId("persona-studio-profile-selector-dropdown")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-1")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-2")).toBeVisible();
    expect(screen.getByTestId("persona-studio-profile-option-profile-3")).toBeVisible();

    expect(screen.getByRole("button", { name: /^save profile$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "primary"
    );
    expect(screen.getByRole("button", { name: /^save as new profile$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "secondary"
    );
    expect(screen.getByRole("button", { name: /^reset profile changes$/i })).toHaveAttribute(
      "data-persona-studio-action-tier",
      "reset"
    );
    expect(
      screen.getByRole("button", { name: /^reset local studio data$/i })
    ).toHaveAttribute("data-persona-studio-action-tier", "reset");
    expect(
      screen.getAllByRole("button", { name: /^reset local studio data$/i })
    ).toHaveLength(1);
    expect(screen.queryByRole("button", { name: /^reset all data$/i })).not.toBeInTheDocument();
  });

  it("renders the section tabs in the header area", () => {
    renderPage();

    const sectionTabs = screen.getByTestId("persona-studio-tabs");
    expect(sectionTabs).toBeVisible();
    expect(within(screen.getByTestId("persona-studio-editor")).queryByTestId("persona-studio-tabs")).not.toBeInTheDocument();
  });

  it("keeps the profile selector beneath the editor and removes the old summary card", () => {
    renderPage();

    expect(screen.getByTestId("persona-studio-profile-selector")).toBeInTheDocument();
    expect(
      within(screen.getByTestId("persona-studio-configuration-lane")).queryByTestId(
        "persona-studio-active-profile-summary"
      )
    ).not.toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-active-profile-summary")).not.toBeInTheDocument();
  });

  it("applies Persona Studio action material markers to the tray and preview controls", () => {
    renderPage();

    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    const save = screen.getByTestId("persona-studio-action-save");
    const saveAsNew = screen.getByTestId("persona-studio-action-save-as-new");
    const reset = screen.getByTestId("persona-studio-action-reset");
    const resetAll = screen.getByTestId("persona-studio-action-reset-all");
    const send = screen.getByRole("button", { name: /^send$/i });
    const clear = screen.getByRole("button", { name: /clear preview session/i });

    // Utility / selector chip
    expect(trigger).toHaveClass("ps-action-chip");
    expect(trigger).toHaveAttribute("data-ps-material", "selector");

    // Primary action chips (Save profile, Send)
    expect(save).toHaveClass("ps-action-chip");
    expect(save).toHaveAttribute("data-ps-material", "primary");
    expect(send).toHaveClass("ps-action-chip");
    expect(send).toHaveAttribute("data-ps-material", "primary");

    // Secondary action chips (Save as new profile, Clear preview session)
    expect(saveAsNew).toHaveClass("ps-action-chip");
    expect(saveAsNew).toHaveAttribute("data-ps-material", "secondary");
    expect(clear).toHaveClass("ps-action-chip");
    expect(clear).toHaveAttribute("data-ps-material", "secondary");

    // Reset / danger chips (Reset profile changes, Reset local Studio data)
    expect(reset).toHaveClass("ps-action-chip");
    expect(reset).toHaveAttribute("data-ps-material", "reset");
    expect(resetAll).toHaveClass("ps-action-chip");
    expect(resetAll).toHaveAttribute("data-ps-material", "reset");
  });

  it("keeps the profile/action tray text-first, compact, and free of added decorative SVGs or helper text", () => {
    renderPage();

    const tray = screen.getByTestId("persona-studio-profile-selector");

    // Every Persona Studio action chip in the tray stays text-first: no
    // decorative SVG icon introduced by this material pass.
    const chips = tray.querySelectorAll("[data-ps-material]");
    expect(chips.length).toBeGreaterThan(0);
    chips.forEach((chip) => {
      expect(chip.querySelector("svg")).toBeNull();
      // No subtitle/helper paragraphs introduced inside or directly under a chip
      expect(chip.querySelector("p, .helper-text, .subtitle")).toBeNull();
    });

    // The tray stays a single compact row (no microcopy block rendered beneath)
    expect(tray.tagName).toBe("DIV");
    expect(tray.className).toMatch(/flex/);
    expect(tray.querySelector("h1, h2, h3, p")).toBeNull();
  });
});
