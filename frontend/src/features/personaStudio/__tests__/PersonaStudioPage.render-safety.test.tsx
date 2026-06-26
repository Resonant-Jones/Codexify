import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";

const { mockPersonaStudioState } = vi.hoisted(() => {
  const minimalProfile = {
    id: "profile-1",
    name: "Guardian Default",
    description: "Default runtime persona",
    isDefault: true,
    config: {
      identity: {
        name: "Guardian Default",
        description: "Default runtime persona",
      },
      model: {
        provider: "openai",
        model: "gpt-4o",
        temperature: 0.7,
        topK: 40,
        topP: 0.95,
        maxTokens: 4096,
      },
      voice: {
        enabled: false,
        provider: "elevenlabs",
        voicePreset: "rachel",
        speed: 1,
        wakeWord: "Hey Guardian",
        interruptible: true,
      },
      prompt: {
        systemPrompt: "You are a Guardian.",
        styleNotes: "Be direct.",
        directives: "Stay grounded.",
      },
      tools: {
        pinnedTools: [],
        allowedTools: [],
        skills: [],
        permissions: {
          web: false,
          email: false,
          calendar: false,
          cli: false,
          filesystem: false,
        },
      },
      retrieval: {
        enabled: false,
        mode: "semantic",
        topK: 5,
        rerank: false,
      },
    },
  };

  return {
    mockPersonaStudioState: {
      profiles: [minimalProfile],
      selectedProfileId: minimalProfile.id,
      activeTab: "Truth Matrix",
      selectedProfile: minimalProfile,
      selectedSavedProfile: minimalProfile,
      isDirty: false,
      hasSavedVersion: true,
      setSelectedProfileId: vi.fn(),
      setActiveTab: vi.fn(),
      updateSelectedProfile: vi.fn(),
      saveProfile: vi.fn(),
      saveAsNewProfile: vi.fn(),
      resetToSaved: vi.fn(),
    },
  };
});

vi.mock("../personaStudioStore", () => ({
  usePersonaStudioLocalDraftState: () => mockPersonaStudioState,
}));

import PersonaStudioPage from "../PersonaStudioPage";

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Persona Studio Page render safety", () => {
  it("mounts the edited shell, rail, truth matrix, and preview panel together", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    const shell = screen.getByTestId("persona-studio-shell");
    const layout = within(shell).getByTestId("persona-studio-editor-two-lane-layout");
    const configurationLane = within(layout).getByTestId("persona-studio-configuration-lane");
    const railLane = within(layout).getByTestId("persona-studio-rail-lane");
    const rail = within(railLane).getByTestId("persona-studio-rail");

    expect(configurationLane).toBeVisible();
    expect(railLane).toBeVisible();
    expect(within(configurationLane).getByTestId("persona-studio-editor")).toBeVisible();
    expect(rail).toBeVisible();
    expect(screen.getByTestId("persona-preview-panel")).toBeVisible();
    expect(screen.getByTestId("persona-preview-panel-transcript")).toBeVisible();
    expect(screen.getByTestId("persona-preview-panel-composer")).toBeVisible();

    const truthMatrixTab = screen.getByRole("button", { name: /^truth matrix$/i });
    expect(truthMatrixTab).toHaveAttribute("data-state", "active");

    const matrix = screen.getByRole("table", { name: /persona studio truth matrix/i });
    expect(within(matrix).getByRole("columnheader", { name: /control/i })).toBeInTheDocument();
    expect(within(matrix).getByRole("rowheader", { name: /persona name/i })).toBeInTheDocument();
    expect(within(matrix).getByRole("rowheader", { name: /retrieval top k/i })).toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /^diagnostics$/i }));

    const diagnosticsPanel = screen.getByTestId("persona-studio-rail-diagnostics-panel");
    expect(diagnosticsPanel).toBeVisible();
    expect(diagnosticsPanel).toHaveAttribute("role", "tabpanel");
    expect(screen.getByText("Save Status")).toBeVisible();
    expect(screen.getByText("Effective Config")).toBeVisible();
    expect(screen.getByText("Debug Log")).toBeVisible();
  });
});
