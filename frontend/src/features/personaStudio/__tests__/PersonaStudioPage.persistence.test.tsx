import { beforeEach, describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import PersonaStudioPage from "../PersonaStudioPage";
import {
  createPersonaStudioSeedState,
  persistPersonaStudioLocalState,
} from "../personaStudioStore";

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function seedCodeAssistantPersonaState() {
  const state = createPersonaStudioSeedState();
  const profile = state.profiles.find((candidate) => candidate.id === "profile-2");

  if (!profile) {
    throw new Error("Missing persona studio seed profile-2");
  }

  const savedDescription = "Saved profile description";
  const savedProfile = {
    ...profile,
    name: "Code Assistant Saved",
    description: savedDescription,
    config: {
      ...profile.config,
      identity: {
        ...profile.config.identity,
        name: "Code Assistant Saved",
        description: savedDescription,
      },
    },
  };

  state.profiles = state.profiles.map((candidate) =>
    candidate.id === profile.id ? savedProfile : candidate
  );
  state.draftProfilesById = {
    ...state.draftProfilesById,
    [profile.id]: clone(savedProfile),
  };
  state.selectedProfileId = profile.id;
  state.activeTab = "Identity";

  persistPersonaStudioLocalState(state);
}

beforeEach(() => {
  window.localStorage.clear();
});

describe("Persona Studio persistence", () => {
  it("renders saved persona state, preserves drafts across tab changes, and round-trips save/reset", async () => {
    seedCodeAssistantPersonaState();

    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    expect(
      screen.getByRole("heading", { name: "Code Assistant Saved" })
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Code Assistant Saved")).toBeInTheDocument();
    expect(
      screen.getByDisplayValue("Saved profile description")
    ).toBeInTheDocument();
    expect(screen.getByText("Saved Locally")).toBeInTheDocument();
    expect(screen.getByText(/"name": "Code Assistant Saved"/)).toBeInTheDocument();

    const nameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Code Assistant Draft");

    expect(screen.getByDisplayValue("Code Assistant Draft")).toBeInTheDocument();
    expect(screen.getByText("Unsaved Draft")).toBeInTheDocument();
    expect(screen.getByText(/"name": "Code Assistant Draft"/)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /model/i }));
    await user.click(screen.getByRole("button", { name: /identity/i }));

    expect(screen.getByDisplayValue("Code Assistant Draft")).toBeInTheDocument();
    expect(screen.getByText("Unsaved Draft")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByText("Saved Locally")).toBeInTheDocument();
    expect(screen.queryByText("Unsaved Draft")).not.toBeInTheDocument();

    await user.clear(screen.getByDisplayValue("Code Assistant Draft"));
    await user.type(screen.getByPlaceholderText(/enter persona name/i), "Code Assistant Reset Candidate");

    expect(screen.getByText("Unsaved Draft")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /^reset$/i }));

    expect(screen.getByDisplayValue("Code Assistant Draft")).toBeInTheDocument();
    expect(screen.getByText("Saved Locally")).toBeInTheDocument();
    expect(screen.queryByText("Unsaved Draft")).not.toBeInTheDocument();
  });

  it("duplicates the current draft into a new persona and leaves the original saved profile intact", async () => {
    seedCodeAssistantPersonaState();

    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    const nameInput = screen.getByPlaceholderText(/enter persona name/i);
    await user.clear(nameInput);
    await user.type(nameInput, "Code Assistant Working");
    await user.click(screen.getByRole("button", { name: /^save$/i }));

    expect(screen.getByText("Saved Locally")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save as new/i }));

    expect(
      screen.getByRole("heading", { name: "Code Assistant Working Copy" })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /code assistant working copy/i })
    ).toBeInTheDocument();
    expect(
      screen.getByRole("button", { name: /code assistant working(?! copy)/i })
    ).toBeInTheDocument();
    expect(screen.getByText("Saved Locally")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /code assistant working(?! copy)/i }));

    expect(
      screen.getByRole("heading", { name: "Code Assistant Working" })
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue("Code Assistant Working")).toBeInTheDocument();
  });

  it("does not render chat composer or message thread UI", () => {
    render(<PersonaStudioPage />);

    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
    expect(screen.queryByText(/message thread/i)).not.toBeInTheDocument();
  });
});
