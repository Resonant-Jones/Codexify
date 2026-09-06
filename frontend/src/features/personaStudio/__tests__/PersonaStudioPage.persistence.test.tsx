import { act, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import React from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PersonaStudioBackendProfile } from "../personaStudioApi";
import PersonaStudioPage from "../PersonaStudioPage";
import { createPersonaStudioSeedState, persistPersonaStudioLocalState } from "../personaStudioStore";

import { normalizeProfile, personaStudioApiMock, resetPersonaStudioApiMock } from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

function backendProfile(): PersonaStudioBackendProfile {
  const config = createPersonaStudioSeedState().profiles[0].config;
  return normalizeProfile({
    id: "profile-1",
    manifest: {
      apiVersion: "codexify.persona/v1", profileIdentity: "profile-1", revision: 12,
      identity: { name: "Backend Persona", description: "Backend description" },
      prompt: { systemPrompt: "Backend prompt", styleNotes: "Backend style", directives: "Backend directive" },
      model: { ...config.model, model: "backend-model", temperature: 0.4 },
      voice: config.voice, capabilities: config.tools, retrieval: config.retrieval,
    },
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

const editor = () => screen.getByTestId("persona-studio-editor");

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock([backendProfile()]);
});

describe("Persona Studio persistence", () => {
  it("hydrates canonical authored fields and establishes the saved editor baseline", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    expect(editor()).toHaveAttribute("data-saved-profile-id", "");
    await screen.findByDisplayValue("Backend Persona");
    expect(screen.getByDisplayValue("Backend description")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-saved-profile-id", "profile-1");
    expect(editor()).toHaveAttribute("data-draft-state", "clean");
    expect(screen.getByTestId("persona-studio-action-save")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: /^prompt$/i }));
    expect(screen.getByDisplayValue("Backend prompt")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Backend style")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Backend directive")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /^model$/i }));
    expect(screen.getByDisplayValue("backend-model")).toBeInTheDocument();
  });

  it("keeps drafts across tabs and waits for update acknowledgement before becoming clean", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    await user.clear(screen.getByPlaceholderText(/enter persona name/i));
    await user.type(screen.getByPlaceholderText(/enter persona name/i), "Submitted draft");
    await user.click(screen.getByRole("button", { name: /^model$/i }));
    await user.click(screen.getByRole("button", { name: /^identity$/i }));
    expect(screen.getByDisplayValue("Submitted draft")).toBeInTheDocument();
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.updatePersonaProfile.mockReturnValueOnce(pending.promise);
    await user.click(screen.getByTestId("persona-studio-action-save"));
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
    const response = backendProfile();
    response.manifest.identity.name = "Acknowledged name";
    response.manifest.revision = response.current_revision = 30;
    await act(async () => pending.resolve(response));
    expect(screen.getByDisplayValue("Acknowledged name")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "clean");
    await user.type(screen.getByPlaceholderText(/enter persona name/i), " edit");
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Acknowledged name")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "clean");
  });

  it("keeps a failed update dirty and resets to the previous canonical snapshot", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    await user.type(screen.getByPlaceholderText(/enter persona name/i), " unsaved");
    personaStudioApiMock.updatePersonaProfile.mockRejectedValueOnce(new Error("offline"));
    await user.click(screen.getByTestId("persona-studio-action-save"));
    expect(screen.getByDisplayValue("Backend Persona unsaved")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
    expect(editor()).toHaveAttribute("data-saved-profile-id", "profile-1");
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Backend Persona")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "clean");
  });

  it("keeps a new copy unsaved until creation acknowledgement and preserves concurrent edits", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.createPersonaProfile.mockReturnValueOnce(pending.promise);
    await user.click(screen.getByTestId("persona-studio-action-save-as-new"));
    expect(editor()).toHaveAttribute("data-saved-profile-id", "");
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
    await user.type(screen.getByPlaceholderText(/enter persona name/i), " newer");
    const body = personaStudioApiMock.createPersonaProfile.mock.calls[0][0];
    if (!("manifest" in body)) throw new Error("Expected canonical write");
    const response = normalizeProfile({ id: body.manifest.profileIdentity, manifest: { ...body.manifest, revision: 4 } });
    await act(async () => pending.resolve(response));
    expect(screen.getByDisplayValue("Backend Persona Copy newer")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
    expect(editor()).toHaveAttribute("data-saved-profile-id", body.manifest.profileIdentity);
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Backend Persona Copy")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-draft-state", "clean");
    await user.click(screen.getByTestId("persona-studio-profile-selector-trigger"));
    expect(within(screen.getByTestId("persona-studio-profile-selector-list")).getByText("Backend Persona")).toBeVisible();
  });

  it("recovers failed creation as an unsaved draft after offline remount", async () => {
    const user = userEvent.setup();
    const page = render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    personaStudioApiMock.createPersonaProfile.mockRejectedValueOnce(new Error("offline"));
    await user.click(screen.getByTestId("persona-studio-action-save-as-new"));
    expect(editor()).toHaveAttribute("data-saved-profile-id", "");
    page.unmount();
    personaStudioApiMock.fetchPersonaProfiles.mockRejectedValueOnce(new Error("offline"));
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona Copy");
    expect(editor()).toHaveAttribute("data-saved-profile-id", "");
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
  });

  it("recovers local-only work without claiming a saved backend profile", async () => {
    persistPersonaStudioLocalState(createPersonaStudioSeedState());
    personaStudioApiMock.fetchPersonaProfiles.mockRejectedValueOnce(new Error("offline"));
    render(<PersonaStudioPage />);
    await waitFor(() => expect(personaStudioApiMock.fetchPersonaProfiles).toHaveBeenCalled());
    expect(screen.getByDisplayValue("Guardian Default")).toBeInTheDocument();
    expect(editor()).toHaveAttribute("data-saved-profile-id", "");
    expect(editor()).toHaveAttribute("data-draft-state", "dirty");
    expect(screen.getByTestId("persona-studio-action-save")).toBeEnabled();
  });

  it("does not render chat composer or message thread UI", async () => {
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    expect(screen.queryByTestId("composer-shell")).not.toBeInTheDocument();
    expect(screen.queryByTestId("composer-input")).not.toBeInTheDocument();
    expect(screen.queryByTestId("chat-conversation-lane")).not.toBeInTheDocument();
  });
});
