import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PersonaStudioBackendProfile } from "../personaStudioApi";
import PersonaStudioPage from "../PersonaStudioPage";
import { createPersonaStudioSeedState } from "../personaStudioStore";
import {
  normalizeProfile,
  personaStudioApiMock,
  resetPersonaStudioApiMock,
} from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

function backendProfile(): PersonaStudioBackendProfile {
  const config = createPersonaStudioSeedState().profiles[0].config;
  return normalizeProfile({
    id: "profile-1",
    manifest: {
      apiVersion: "codexify.persona/v1",
      profileIdentity: "profile-1",
      revision: 12,
      identity: { name: "Backend Persona", description: "Backend description" },
      prompt: { systemPrompt: "Backend prompt", styleNotes: "Backend style", directives: "Backend directives" },
      model: { ...config.model, model: "backend-model", temperature: 0.4 },
      voice: config.voice,
      capabilities: config.tools,
      retrieval: config.retrieval,
    },
  });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock([backendProfile()]);
});

describe("Persona Studio acknowledgement persistence", () => {
  it("hydrates the acknowledged manifest and uses its revision as the clean baseline", async () => {
    render(<PersonaStudioPage />);

    await screen.findByDisplayValue("Backend Persona");
    expect(screen.getByDisplayValue("Backend description")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-configuration-viewport")).toHaveAttribute("data-saved-profile-id", "profile-1");
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Saved · rev 12");
    expect(screen.getByTestId("persona-studio-action-save")).toBeDisabled();
  });

  it("waits for acknowledgement before clearing dirty state, then reverts to that acknowledgement", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    const name = await screen.findByLabelText(/persona name/i);
    await user.clear(name);
    await user.type(name, "Submitted draft");
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Unsaved changes · saved rev 12");

    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.updatePersonaProfile.mockReturnValueOnce(pending.promise);
    await user.click(screen.getByTestId("persona-studio-action-save"));
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Unsaved changes · saved rev 12");

    const acknowledged = backendProfile();
    acknowledged.manifest.identity.name = "Acknowledged name";
    acknowledged.manifest.revision = acknowledged.current_revision = 30;
    await act(async () => pending.resolve(acknowledged));
    await waitFor(() => expect(screen.getByDisplayValue("Acknowledged name")).toBeInTheDocument());
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Saved · rev 30");

    await user.type(screen.getByLabelText(/persona name/i), " changed");
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Acknowledged name")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Saved · rev 30");
  });

  it("leaves a failed save dirty and lets Revert restore the prior acknowledgement", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    const name = await screen.findByLabelText(/persona name/i);
    await user.type(name, " unsaved");
    personaStudioApiMock.updatePersonaProfile.mockRejectedValueOnce(new Error("offline"));
    await user.click(screen.getByTestId("persona-studio-action-save"));

    await waitFor(() => expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Unsaved changes · saved rev 12"));
    expect(screen.getByDisplayValue("Backend Persona unsaved")).toBeInTheDocument();
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Backend Persona")).toBeInTheDocument();
    expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Saved · rev 12");
  });

  it("preserves an edit concurrent with Duplicate-as-new acknowledgement", async () => {
    const user = userEvent.setup();
    render(<PersonaStudioPage />);
    await screen.findByDisplayValue("Backend Persona");
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.createPersonaProfile.mockReturnValueOnce(pending.promise);

    await user.click(screen.getByTestId("persona-studio-profile-selector-trigger"));
    await user.click(screen.getByTestId("persona-studio-action-save-as-new"));
    const name = await screen.findByLabelText(/persona name/i);
    await user.type(name, " newer");
    const body = personaStudioApiMock.createPersonaProfile.mock.calls[0]?.[0] as {
      manifest: { profileIdentity: string; [key: string]: unknown };
    };
    const acknowledged = normalizeProfile({
      id: body.manifest.profileIdentity,
      manifest: { ...body.manifest, revision: 4 } as PersonaStudioBackendProfile["manifest"],
    });
    await act(async () => pending.resolve(acknowledged));

    await waitFor(() => expect(screen.getByTestId("persona-studio-save-status")).toHaveTextContent("Unsaved changes · saved rev 4"));
    expect(screen.getByDisplayValue("Backend Persona Copy newer")).toBeInTheDocument();
    await user.click(screen.getByTestId("persona-studio-action-reset"));
    expect(screen.getByDisplayValue("Backend Persona Copy")).toBeInTheDocument();
  });
});
