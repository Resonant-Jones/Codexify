import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, test, vi } from "vitest";

import PersonalFactsPanel from "@/features/settings/components/PersonalFactsPanel";
import {
  fetchPersonaSettings,
  updatePersonaSettings,
} from "@/features/settings/api/persona";

vi.mock("@/features/settings/api/persona", () => ({
  fetchPersonaSettings: vi.fn(),
  updatePersonaSettings: vi.fn(),
}));

const fetchPersonaSettingsMock = vi.mocked(fetchPersonaSettings);
const updatePersonaSettingsMock = vi.mocked(updatePersonaSettings);

describe("PersonalFactsPanel", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  test("loads the active persona text inside the shared settings surface", async () => {
    fetchPersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "Answer with a calm, crisp voice.",
      source: "user",
      createdAt: "2026-03-08T14:22:00Z",
      canClear: false,
    });

    render(<PersonalFactsPanel projectId={42} threadId={9} />);

    expect(screen.getByTestId("personal-facts-panel")).toBeInTheDocument();
    expect(screen.getByRole("status")).toHaveTextContent("Loading active persona…");

    expect(
      await screen.findByDisplayValue("Answer with a calm, crisp voice.")
    ).toBeInTheDocument();
    expect(
      screen.getByText(
        "Persona is the user-editable voice or mask layer. It shapes tone and style without changing deeper identity."
      )
    ).toBeInTheDocument();

    expect(fetchPersonaSettingsMock).toHaveBeenCalledWith({
      projectId: 42,
      threadId: 9,
    });
  });

  test("saves updated persona text", async () => {
    const user = userEvent.setup();

    fetchPersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "Keep answers measured.",
      source: "user",
      createdAt: "2026-03-08T14:22:00Z",
      canClear: false,
    });
    updatePersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "Keep answers measured and concrete.",
      source: "user",
      createdAt: "2026-03-08T14:24:00Z",
      canClear: false,
    });

    render(<PersonalFactsPanel />);

    const textarea = await screen.findByLabelText("Active persona text");
    await user.clear(textarea);
    await user.type(textarea, "Keep answers measured and concrete.");
    await user.click(screen.getByRole("button", { name: "Save Persona" }));

    await waitFor(() => {
      expect(updatePersonaSettingsMock).toHaveBeenCalledWith({
        text: "Keep answers measured and concrete.",
        projectId: undefined,
        threadId: undefined,
      });
    });

    expect(
      await screen.findByDisplayValue("Keep answers measured and concrete.")
    ).toBeInTheDocument();
  });

  test("blocks accidental empty saves unless clearing is enabled", async () => {
    const user = userEvent.setup();

    fetchPersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "Stay concise.",
      source: "user",
      createdAt: "2026-03-08T14:22:00Z",
      canClear: false,
    });

    render(<PersonalFactsPanel />);

    const textarea = await screen.findByLabelText("Active persona text");
    await user.clear(textarea);

    expect(screen.getByRole("button", { name: "Save Persona" })).toBeDisabled();
    expect(screen.getByRole("note")).toHaveTextContent(
      "Add persona text before saving. Clearing is not enabled here."
    );
    expect(updatePersonaSettingsMock).not.toHaveBeenCalled();
  });

  test("allows empty saves when the backend marks clearing as enabled", async () => {
    const user = userEvent.setup();

    fetchPersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "Stay concise.",
      source: "user",
      createdAt: "2026-03-08T14:22:00Z",
      canClear: true,
    });
    updatePersonaSettingsMock.mockResolvedValue({
      id: 7,
      text: "",
      source: "user",
      createdAt: "2026-03-08T14:30:00Z",
      canClear: true,
    });

    render(<PersonalFactsPanel />);

    const textarea = await screen.findByLabelText("Active persona text");
    await user.clear(textarea);
    await user.click(screen.getByRole("button", { name: "Save Persona" }));

    await waitFor(() => {
      expect(updatePersonaSettingsMock).toHaveBeenCalledWith({
        text: "",
        projectId: undefined,
        threadId: undefined,
      });
    });
  });

  test("uses reset for unsaved changes and reload when clean", async () => {
    const user = userEvent.setup();

    fetchPersonaSettingsMock
      .mockResolvedValueOnce({
        id: 7,
        text: "Stay concise.",
        source: "user",
        createdAt: "2026-03-08T14:22:00Z",
        canClear: false,
      })
      .mockResolvedValueOnce({
        id: 7,
        text: "Reloaded persona.",
        source: "user",
        createdAt: "2026-03-08T14:35:00Z",
        canClear: false,
      });

    render(<PersonalFactsPanel />);

    const textarea = await screen.findByLabelText("Active persona text");
    await user.type(textarea, " with nuance");
    await user.click(screen.getByRole("button", { name: "Reset" }));

    expect(await screen.findByDisplayValue("Stay concise.")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Reload" }));

    await waitFor(() => {
      expect(fetchPersonaSettingsMock).toHaveBeenCalledTimes(2);
    });

    expect(await screen.findByDisplayValue("Reloaded persona.")).toBeInTheDocument();
  });

  test("shows a load error and leaves reload available", async () => {
    fetchPersonaSettingsMock.mockRejectedValue(new Error("persona fetch failed"));

    render(<PersonalFactsPanel />);

    expect(await screen.findByRole("alert")).toHaveTextContent(
      "persona fetch failed"
    );
    expect(screen.getByRole("button", { name: "Reload" })).toBeEnabled();
  });
});
