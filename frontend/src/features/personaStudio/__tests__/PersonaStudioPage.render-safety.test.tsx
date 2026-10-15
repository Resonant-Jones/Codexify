import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

const { state } = vi.hoisted(() => {
  const profile = {
    id: "profile-1",
    name: "Guardian Default",
    description: "Default Persona Profile",
    isDefault: true,
    config: {
      identity: { name: "Guardian Default", description: "Default Persona Profile" },
      model: { provider: "openai", model: "gpt-4o", temperature: 0.7, topK: 40, topP: 0.95, maxTokens: 4096 },
      voice: { enabled: false, provider: "elevenlabs", voicePreset: "rachel", speed: 1, wakeWord: "Hey Guardian", interruptible: true },
      prompt: { systemPrompt: "Stay grounded.", styleNotes: "Be direct.", directives: "Protect privacy." },
      tools: { pinnedTools: [], allowedTools: [], skills: [], permissions: { web: false, email: false, calendar: false, cli: false, filesystem: false } },
      retrieval: { enabled: false, mode: "semantic", topK: 5, rerank: false },
    },
  };
  return {
    state: {
      profiles: [profile],
      selectedProfile: profile,
      savedRevision: 12,
      isDirty: false,
      hasSavedVersion: true,
      setSelectedProfileId: vi.fn(),
      updateSelectedProfile: vi.fn(),
      saveSelectedProfile: vi.fn(),
      saveSelectedProfileAsNew: vi.fn(),
      resetSelectedProfile: vi.fn(),
    },
  };
});

vi.mock("../personaStudioStore", () => ({
  usePersonaStudioLocalDraftState: () => state,
}));

import PersonaStudioPage from "../PersonaStudioPage";

beforeEach(() => vi.clearAllMocks());

describe("Persona Studio V2 render and authority safety", () => {
  it("owns exactly the Assistant and Configuration primary frames with no page footer", () => {
    render(<PersonaStudioPage />);

    const workspace = screen.getByTestId("persona-studio-workspace");
    expect(workspace.children).toHaveLength(2);
    expect(screen.getAllByTestId(/persona-studio-(assistant|configuration)-frame/)).toHaveLength(2);
    expect(screen.getByRole("heading", { name: "Studio Assistant" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Configuration" })).toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-framecard")).not.toBeInTheDocument();
    expect(screen.queryByTestId("persona-studio-footer")).not.toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Saved · rev 12");
    expect(screen.queryByText(/rev 13/i)).not.toBeInTheDocument();
  });

  it("keeps Test embedded and keeps Binding authority observational", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);

    await user.click(screen.getByRole("tab", { name: /^test$/i }));
    expect(screen.getByTestId("persona-preview-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("persona-preview-panel-header")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();

    await user.click(screen.getByRole("tab", { name: /^form$/i }));
    await user.click(screen.getByRole("button", { name: /activation & bindings/i }));
    expect(screen.getByTestId("persona-studio-form-section-bindings")).toHaveTextContent(/not editable/i);
    expect(screen.getByTestId("persona-studio-form-section-bindings")).toHaveTextContent(/not resolved/i);
    expect(screen.queryByLabelText(/credential/i)).not.toBeInTheDocument();
  });
});
