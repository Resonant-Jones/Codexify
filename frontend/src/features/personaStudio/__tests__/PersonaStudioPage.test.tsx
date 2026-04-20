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
  it("re-homes the utility pane into a secondary support surface", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const supportSurfaces = screen.getByTestId("persona-studio-support-surfaces");

    expect(within(shell).getByTestId("persona-studio-utility-pane")).toBeVisible();
    expect(within(shell).getByTestId("persona-studio-editor")).toBeVisible();
    expect(within(shell).getByTestId("persona-studio-ephemeral-chat-lane")).toBeVisible();
    expect(supportSurfaces).toBeVisible();
    expect(within(supportSurfaces).getByTestId("persona-studio-utility-pane")).toBeVisible();
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

  it("renders the primary two-lane shell with the harness on the right", () => {
    renderPage();

    const shell = screen.getByTestId("persona-studio-shell");
    const layout = within(shell).getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const ephemeralLane = within(layout).getByTestId("persona-studio-ephemeral-chat-lane");
    const harness = within(ephemeralLane).getByTestId("persona-studio-ephemeral-chat-harness");
    const header = within(harness).getByTestId("persona-studio-ephemeral-chat-header");
    const transcript = within(harness).getByTestId("persona-studio-ephemeral-chat-transcript");
    const composer = within(harness).getByTestId("persona-studio-ephemeral-chat-composer");

    expect(configurationLane).toBeVisible();
    expect(ephemeralLane).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-editor")).toBeVisible();
    expect(harness).toBeVisible();
    expect(header).toBeVisible();
    expect(transcript).toBeVisible();
    expect(composer).toBeVisible();
    expect(within(header).getByText("Ephemeral Chat Harness")).toBeVisible();
    expect(within(header).getByText(/^session-local$/i)).toBeVisible();
    expect(within(header).getByText(/^non-runtime$/i)).toBeVisible();
    expect(within(header).getByText(/^ephemeral$/i)).toBeVisible();
    expect(within(composer).getByRole("button", { name: /clear ephemeral session/i })).toBeVisible();
    expect(within(configurationLane).queryByTestId("persona-studio-utility-pane")).not.toBeInTheDocument();
    expect(within(shell).getByTestId("persona-studio-support-surfaces")).toBeVisible();
    expect(screen.getByText(/session-scoped draft-testing surface/i)).toBeVisible();
    expect(screen.getByText(/^session-local$/i)).toBeVisible();
    expect(screen.getByText(/^non-runtime$/i)).toBeVisible();
    expect(screen.getByText(/^ephemeral$/i)).toBeVisible();
    expect(screen.getByText(/isolated from guardian runtime/i)).toBeVisible();
    expect(
      screen.getByPlaceholderText(/session-local, ephemeral, non-runtime draft test/i)
    ).toBeVisible();
  });

  it("supports a multi-turn ephemeral transcript", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^coding$/i }));
    await user.type(screen.getByRole("textbox", { name: /ephemeral chat prompt/i }), "Summarize the plan");
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-studio-ephemeral-chat-transcript");
    expect(within(transcript).getByText(/^session transcript$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 1$/i)).toBeVisible();
    expect(within(transcript).getByText(/^turn 2$/i)).toBeVisible();
    expect(within(transcript).getAllByText(/^draft input$/i).length).toBeGreaterThan(0);
    expect(within(transcript).getAllByText(/^ephemeral assistant$/i).length).toBeGreaterThan(0);
    expect(within(transcript).getByText(/^coding$/i)).toBeVisible();
    expect(within(transcript).getByText(/^summarize the plan$/i)).toBeVisible();
    expect(within(transcript).getByText(/this is the first temporary turn in this studio session/i)).toBeVisible();
    expect(within(transcript).getAllByText(/current draft snapshot:/i)).toHaveLength(2);
    expect(within(transcript).getByText(/this is temporary turn 2 in the current studio session/i)).toBeVisible();
  });

  it("keeps prior messages visible and changes later replies when the draft changes", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^planning$/i }));

    await user.type(
      screen.getByRole("textbox", { name: /ephemeral chat prompt/i }),
      "Refine the answer"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));
    await waitFor(() =>
      expect(
        screen.getByTestId("persona-studio-ephemeral-chat-transcript")
      ).toHaveTextContent(/current draft snapshot:/i)
    );

    await user.click(screen.getByRole("button", { name: /model/i }));
    await user.selectOptions(screen.getByRole("combobox", { name: /provider/i }), "anthropic");

    await waitFor(() =>
      expect(screen.getByText(/draft changed since the last reply/i)).toBeVisible()
    );

    await user.type(
      screen.getByRole("textbox", { name: /ephemeral chat prompt/i }),
      "Refine the answer again"
    );
    await user.click(screen.getByRole("button", { name: /^send$/i }));

    const transcript = screen.getByTestId("persona-studio-ephemeral-chat-transcript");
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

    await user.click(screen.getByRole("button", { name: /^planning$/i }));

    const transcript = screen.getByTestId("persona-studio-ephemeral-chat-transcript");
    expect(within(transcript).getByText(/current draft snapshot:/i)).toBeVisible();
    expect(within(transcript).getByText(/^guardian default$/i)).toBeVisible();
    expect(within(transcript).getByText(/^openai \/ gpt-4o$/i)).toBeVisible();
    expect(within(transcript).getByText(/^0\.7$/i)).toBeVisible();
  });

  it("clears the ephemeral session on demand", async () => {
    const user = userEvent.setup();
    renderPage();

    await user.click(screen.getByRole("button", { name: /^research$/i }));
    expect(screen.getByTestId("persona-studio-ephemeral-chat-transcript")).toHaveTextContent(
      /current draft/i
    );

    await user.click(screen.getByRole("button", { name: /clear ephemeral session/i }));

    expect(screen.getByTestId("persona-studio-ephemeral-chat-transcript")).toHaveTextContent(
      /no ephemeral turns yet/i
    );
  });

  it("does not persist the ephemeral session across remounts", async () => {
    const user = userEvent.setup();
    const firstRender = renderPage();

    await user.click(screen.getByRole("button", { name: /^coding$/i }));
    await waitFor(() =>
      expect(screen.getByTestId("persona-studio-ephemeral-chat-transcript")).toHaveTextContent(
        /current draft snapshot:/i
      )
    );

    firstRender.unmount();
    renderPage();

    expect(screen.getByTestId("persona-studio-ephemeral-chat-transcript")).toHaveTextContent(
      /no ephemeral turns yet/i
    );
  });

  it("renders the truthful empty-state copy for draft testing", () => {
    renderPage();

    const transcript = screen.getByTestId("persona-studio-ephemeral-chat-transcript");
    expect(within(transcript).getByText(/^empty harness$/i)).toBeVisible();
    expect(within(transcript).getByText(/local draft testing/i)).toBeVisible();
    expect(
      within(transcript).getByText(/use this session-local harness to test the active persona draft/i)
    ).toBeVisible();
    expect(
      within(transcript).getByText(/send a temporary message, inspect the draft snapshot/i)
    ).toBeVisible();
  });

  it("does not touch runtime write paths or session persistence", async () => {
    const user = userEvent.setup();
    const sessionSetItemSpy = vi.spyOn(window.sessionStorage, "setItem");
    renderPage();

    await user.click(screen.getByRole("button", { name: /^coding$/i }));
    await waitFor(() =>
      expect(screen.getByTestId("persona-studio-ephemeral-chat-transcript")).toHaveTextContent(
        /current draft snapshot:/i
      )
    );

    expect(personaStudioApiMock.fetchPersonaProfiles).toHaveBeenCalledTimes(1);
    expect(personaStudioApiMock.createPersonaProfile).not.toHaveBeenCalled();
    expect(personaStudioApiMock.updatePersonaProfile).not.toHaveBeenCalled();
    expect(sessionSetItemSpy).not.toHaveBeenCalled();
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

    const sectionTabs = screen.getByTestId("persona-studio-tabs");
    expect(sectionTabs).toBeVisible();
    expect(within(screen.getByTestId("persona-studio-editor")).queryByTestId("persona-studio-tabs")).not.toBeInTheDocument();
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
