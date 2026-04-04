import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

import PersonaStudioPage from "../PersonaStudioPage";
import {
  createPersonaStudioSeedState,
  persistPersonaStudioLocalState,
} from "../personaStudioStore";
import {
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

const BACKEND_SEED_PROFILES = [
  {
    id: "profile-1",
    name: "Guardian Default",
    system_prompt:
      "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity.",
    model_provider: "openai",
    model_id: "gpt-4o",
    temperature: 0.7,
    created_at: "2026-04-02T00:00:00.000Z",
    updated_at: "2026-04-02T00:00:00.000Z",
  },
  {
    id: "profile-2",
    name: "Code Assistant",
    system_prompt:
      "You are an expert code assistant. Provide clear, concise, and accurate code solutions with explanation.",
    model_provider: "anthropic",
    model_id: "claude-sonnet-4-20250514",
    temperature: 0.3,
    created_at: "2026-04-02T00:00:00.000Z",
    updated_at: "2026-04-02T00:00:00.000Z",
  },
];

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
  resetPersonaStudioApiMock();
});

describe("Persona Studio persistence", () => {
  it("hydrates first-wave fields from backend while preserving local-only draft fields", async () => {
    resetPersonaStudioApiMock([
      BACKEND_SEED_PROFILES[0],
      {
        ...BACKEND_SEED_PROFILES[1],
        name: "Code Assistant Backend",
        system_prompt: "Backend prompt for the runtime profile.",
        model_provider: "openai",
        model_id: "gpt-4o-mini",
        temperature: 0.4,
      },
    ]);

    const state = createPersonaStudioSeedState();
    const profile = state.profiles.find((candidate) => candidate.id === "profile-2");

    if (!profile) {
      throw new Error("Missing persona studio seed profile-2");
    }

    const localOnlyDescription = "Local-only description";
    const localProfile = {
      ...profile,
      name: "Code Assistant Local",
      description: localOnlyDescription,
      config: {
        ...profile.config,
        identity: {
          ...profile.config.identity,
          name: "Code Assistant Local",
          description: localOnlyDescription,
        },
        model: {
          ...profile.config.model,
          provider: "local",
          model: "phi3",
          temperature: 1.1,
        },
        prompt: {
          ...profile.config.prompt,
          systemPrompt: "Local prompt that should be replaced by backend",
        },
      },
    };

    state.profiles = state.profiles.map((candidate) =>
      candidate.id === profile.id ? localProfile : candidate
    );
    state.draftProfilesById = {
      ...state.draftProfilesById,
      [profile.id]: clone(localProfile),
    };
    state.selectedProfileId = profile.id;
    persistPersonaStudioLocalState(state);

    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await waitFor(() =>
      expect(personaStudioApiMock.fetchPersonaProfiles).toHaveBeenCalled()
    );

    expect(
      await screen.findByDisplayValue("Code Assistant Backend")
    ).toBeInTheDocument();
    expect(screen.getByDisplayValue(localOnlyDescription)).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /prompt/i }));

    expect(
      screen.getByDisplayValue("Backend prompt for the runtime profile.")
    ).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /model/i }));

    await waitFor(() =>
      expect(
        screen.getByRole("combobox", { name: /provider/i })
      ).toHaveValue("openai")
    );
    expect(screen.getByDisplayValue("gpt-4o-mini")).toBeInTheDocument();
    expect(screen.getByText("0.4")).toBeInTheDocument();
  });

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

    await waitFor(() =>
      expect(personaStudioApiMock.updatePersonaProfile).toHaveBeenCalled()
    );
    await waitFor(() =>
      expect(screen.getByDisplayValue("Code Assistant Draft")).toBeInTheDocument()
    );

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

    await waitFor(() =>
      expect(
        screen.getByDisplayValue("Code Assistant Working")
      ).toBeInTheDocument()
    );
    expect(screen.getByText("Saved Locally")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /save as new/i }));

    await waitFor(() =>
      expect(personaStudioApiMock.createPersonaProfile).toHaveBeenCalled()
    );

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
