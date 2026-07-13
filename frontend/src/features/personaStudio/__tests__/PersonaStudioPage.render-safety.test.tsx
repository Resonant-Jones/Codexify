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
  it("mounts the edited shell, rail, truth matrix, guide lane, and preview panel together", async () => {
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
    expect(within(configurationLane).getByTestId("persona-studio-profile-selector")).toBeVisible();
    expect(rail).toBeVisible();
    expect(screen.getByTestId("persona-studio-guide-lane")).toBeVisible();
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

  it("renders a compact inline text profile trigger that matches the action-button height", () => {
    render(<PersonaStudioPage />);

    const trigger = screen.getByTestId("persona-studio-profile-selector-trigger");
    const save = screen.getByTestId("persona-studio-action-save");
    const saveAsNew = screen.getByTestId("persona-studio-action-save-as-new");
    const reset = screen.getByTestId("persona-studio-action-reset");
    const resetAll = screen.getByTestId("persona-studio-action-reset-all");

    expect(
      screen.getByTestId("persona-studio-profile-selector-trigger-name")
    ).toHaveTextContent(/guardian default/i);
    expect(trigger).toHaveAttribute("aria-label", expect.stringMatching(/profile:/i));
    expect(trigger).toHaveAttribute("title", expect.stringMatching(/profile:/i));
    expect(trigger.querySelector("svg")).toBeNull();
    expect(
      screen.queryByTestId("persona-studio-profile-selector-tile")
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("persona-studio-profile-selector-card")
    ).not.toBeInTheDocument();

    const editor = screen.getByTestId("persona-studio-editor");
    const selector = screen.getByTestId("persona-studio-profile-selector");
    expect(editor.compareDocumentPosition(selector) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();

    const triggerRect = trigger.getBoundingClientRect();
    [save, saveAsNew, reset, resetAll].forEach((action) => {
      const actionRect = action.getBoundingClientRect();
      expect(triggerRect.height).toBeLessThanOrEqual(actionRect.height + 1);
    });
    expect(triggerRect.height).toBeLessThan(40);
  });

  it("renders the right rail with only Preview and Diagnostics tabs", () => {
    render(<PersonaStudioPage />);

    const tablist = screen.getByTestId("persona-studio-rail-tabs");
    const railTabs = within(tablist).getAllByRole("tab");
    expect(railTabs.map((tab) => tab.textContent?.trim())).toEqual([
      "Preview",
      "Diagnostics",
    ]);

    expect(
      within(tablist).queryByRole("tab", { name: /^profiles$/i })
    ).not.toBeInTheDocument();
  });

  it("applies the Persona Studio action material markers to the tray and preview controls", () => {
    render(<PersonaStudioPage />);

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

  it("applies the Persona Studio action material markers to the tray and preview controls", () => {
    render(<PersonaStudioPage />);

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
