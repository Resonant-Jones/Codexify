import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

import type { PersonaProfileManifest, PersonaStudioBackendProfile } from "../personaStudioApi";
import {
  PERSONA_STUDIO_STORAGE_KEY,
  createPersonaStudioSeedState,
  persistPersonaStudioLocalState,
  readPersonaStudioLocalState,
  usePersonaStudioLocalDraftState,
} from "../personaStudioStore";

import { normalizeProfile, personaStudioApiMock, resetPersonaStudioApiMock } from "./personaStudioApiMock";

vi.mock("@/features/personaStudio/personaStudioApi", async () =>
  (await import("./personaStudioApiMock")).personaStudioApiMock
);

const manifest: PersonaProfileManifest = {
  apiVersion: "codexify.persona/v1",
  profileIdentity: "profile-1",
  revision: 17,
  identity: { name: "Canonical Persona", description: "Canonical description" },
  prompt: { systemPrompt: "Canonical prompt", styleNotes: "Measured", directives: "Ask first" },
  model: { provider: "local", model: "test-model", temperature: 0.2, topK: 23, topP: 0.8, maxTokens: 2345 },
  voice: { enabled: true, provider: "voice-provider", voicePreset: "alto", speed: 1.2, wakeWord: "Hello", interruptible: false },
  capabilities: {
    pinnedTools: ["lookup"], allowedTools: ["lookup", "inspect"], skills: ["summarize"],
    permissions: { web: true, email: false, calendar: true, cli: false, filesystem: true },
  },
  retrieval: { enabled: true, mode: "hybrid", topK: 11, rerank: true },
};

function response(value = manifest) {
  return normalizeProfile({ id: value.profileIdentity, manifest: value });
}

function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((yes, no) => { resolve = yes; reject = no; });
  return { promise, resolve, reject };
}

async function hydrated() {
  resetPersonaStudioApiMock([response()]);
  const hook = renderHook(usePersonaStudioLocalDraftState);
  await waitFor(() => expect(hook.result.current.savedRevision).toBe(17));
  return hook;
}

type StudioHook = { result: { current: ReturnType<typeof usePersonaStudioLocalDraftState> } };
function rename(hook: StudioHook, name: string) {
  act(() => hook.result.current.updateSelectedProfile((draft) => ({
    ...draft, name, config: { ...draft.config, identity: { ...draft.config.identity, name } },
  })));
}

beforeEach(() => {
  window.localStorage.clear();
  resetPersonaStudioApiMock();
});

describe("Persona Studio canonical saved-state authority", () => {
  it("hydrates every V1 field from the manifest, ignoring compatibility projections", async () => {
    const backend = { ...response(), name: "Wrong projection", system_prompt: "Wrong prompt", model_id: "wrong", temperature: 1.9 };
    personaStudioApiMock.fetchPersonaProfiles.mockResolvedValueOnce([backend]);
    const hook = renderHook(usePersonaStudioLocalDraftState);
    expect(hook.result.current.hasSavedVersion).toBe(false);
    await waitFor(() => expect(hook.result.current.savedRevision).toBe(17));
    expect(hook.result.current.selectedSavedManifest).toEqual(manifest);
    expect(hook.result.current.selectedProfile?.config).toEqual({
      identity: manifest.identity, prompt: manifest.prompt, model: manifest.model,
      voice: manifest.voice, tools: manifest.capabilities, retrieval: manifest.retrieval,
    });
    expect(hook.result.current.selectedProfile?.name).toBe(manifest.identity.name);
    expect(hook.result.current.selectedProfile?.description).toBe(manifest.identity.description);
    expect(hook.result.current.hasSavedVersion).toBe(true);
    expect(hook.result.current.isDirty).toBe(false);
  });

  it("reconfirms an unchanged cached profile after reload despite JSON key ordering", async () => {
    const first = await hydrated();
    first.unmount();
    // readPersonaStudioLocalState normalizes config into a different key order.
    const pending = deferred<PersonaStudioBackendProfile[]>();
    personaStudioApiMock.fetchPersonaProfiles.mockReturnValueOnce(pending.promise);
    const reloaded = renderHook(usePersonaStudioLocalDraftState);
    expect(reloaded.result.current.hasSavedVersion).toBe(false);
    expect(reloaded.result.current.savedRevision).toBeNull();
    expect(reloaded.result.current.isDirty).toBe(true);
    await act(async () => pending.resolve([response()]));
    expect(reloaded.result.current.savedRevision).toBe(17);
    expect(reloaded.result.current.selectedSavedManifest).toEqual(manifest);
    expect(reloaded.result.current.isDirty).toBe(false);
  });

  it("hydrates optional omissions with editor defaults, never cached broad values", async () => {
    const sparse = response({
      apiVersion: manifest.apiVersion, profileIdentity: manifest.profileIdentity, revision: 5,
      identity: { name: "Sparse", description: null },
      prompt: { systemPrompt: "Sparse prompt", styleNotes: null },
      model: { provider: "local", model: "sparse", temperature: 0, topP: null },
      voice: null, capabilities: null, retrieval: null,
    });
    personaStudioApiMock.fetchPersonaProfiles.mockResolvedValueOnce([sparse]);
    const hook = renderHook(usePersonaStudioLocalDraftState);
    await waitFor(() => expect(hook.result.current.hasSavedVersion).toBe(true));
    expect(hook.result.current.selectedProfile?.config).toMatchObject({
      identity: { name: "Sparse", description: "" },
      prompt: { systemPrompt: "Sparse prompt", styleNotes: "", directives: "" },
      model: { provider: "local", model: "sparse", temperature: 0, topK: 40, topP: 0.95, maxTokens: 4096 },
      voice: { enabled: false, voicePreset: "", wakeWord: "" },
      tools: { pinnedTools: [], allowedTools: [], skills: [], permissions: { web: false } },
      retrieval: { enabled: false },
    });
    expect(hook.result.current.selectedSavedManifest).toEqual(sparse.manifest);
    expect(hook.result.current.isDirty).toBe(false);
  });

  it("sends a complete revision-free manifest and waits for the server revision and normalization", async () => {
    const hook = await hydrated();
    rename(hook, "  Authored name  ");
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.updatePersonaProfile.mockReturnValueOnce(pending.promise);
    act(() => hook.result.current.saveSelectedProfile());
    const { revision: _revision, ...expectedWrite } = manifest;
    expectedWrite.identity = { ...manifest.identity, name: "  Authored name  " };
    expect(personaStudioApiMock.updatePersonaProfile).toHaveBeenCalledWith("profile-1", { manifest: expectedWrite });
    expect(hook.result.current.savedRevision).toBe(17);
    expect(hook.result.current.selectedSavedProfile?.name).toBe("Canonical Persona");
    expect(hook.result.current.isDirty).toBe(true);
    const acknowledged = { ...manifest, revision: 42, identity: { ...manifest.identity, name: "Authored name" } };
    await act(async () => pending.resolve(response(acknowledged)));
    expect(hook.result.current.selectedSavedManifest).toEqual(acknowledged);
    expect(hook.result.current.savedRevision).toBe(42);
    expect(hook.result.current.selectedProfile?.name).toBe("Authored name");
    expect(hook.result.current.isDirty).toBe(false);
    expect(JSON.parse(localStorage.getItem(PERSONA_STUDIO_STORAGE_KEY)!)).not.toHaveProperty("savedManifestsById");
    expect(localStorage.getItem(PERSONA_STUDIO_STORAGE_KEY)).not.toContain('"revision"');
  });

  it("preserves the canonical baseline and recoverable dirty work after update failure", async () => {
    const hook = await hydrated();
    rename(hook, "Failed update draft");
    personaStudioApiMock.updatePersonaProfile.mockRejectedValueOnce(new Error("offline"));
    await act(async () => hook.result.current.saveSelectedProfile());
    expect(hook.result.current.selectedSavedManifest).toEqual(manifest);
    expect(hook.result.current.savedRevision).toBe(17);
    expect(hook.result.current.selectedProfile?.name).toBe("Failed update draft");
    expect(hook.result.current.isDirty).toBe(true);
    expect(readPersonaStudioLocalState().draftProfilesById["profile-1"].name).toBe("Failed update draft");
    act(() => hook.result.current.resetSelectedProfile());
    expect(hook.result.current.selectedProfile?.name).toBe("Canonical Persona");
    expect(hook.result.current.isDirty).toBe(false);
  });

  it("preserves newer edits during an update and bounds repeated Save clicks", async () => {
    const hook = await hydrated();
    rename(hook, "Submitted");
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.updatePersonaProfile.mockReturnValueOnce(pending.promise);
    act(() => hook.result.current.saveSelectedProfile());
    rename(hook, "Newer edit");
    act(() => hook.result.current.saveSelectedProfile());
    expect(personaStudioApiMock.updatePersonaProfile).toHaveBeenCalledTimes(1);
    await act(async () => pending.resolve(response({ ...manifest, revision: 29, identity: { ...manifest.identity, name: "Submitted" } })));
    expect(hook.result.current.selectedSavedProfile?.name).toBe("Submitted");
    expect(hook.result.current.savedRevision).toBe(29);
    expect(hook.result.current.selectedProfile?.name).toBe("Newer edit");
    expect(hook.result.current.isDirty).toBe(true);
  });

  it("accepts a server no-op acknowledgement without incrementing its revision", async () => {
    const hook = await hydrated();
    rename(hook, " Canonical Persona ");
    personaStudioApiMock.updatePersonaProfile.mockResolvedValueOnce(response());
    await act(async () => hook.result.current.saveSelectedProfile());
    expect(hook.result.current.savedRevision).toBe(17);
    expect(hook.result.current.selectedProfile?.name).toBe("Canonical Persona");
    expect(hook.result.current.isDirty).toBe(false);
  });

  it("establishes Save As New only from acknowledgement and preserves the original", async () => {
    const hook = await hydrated();
    rename(hook, "Working");
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.createPersonaProfile.mockReturnValueOnce(pending.promise);
    act(() => hook.result.current.saveSelectedProfileAsNew());
    const id = hook.result.current.selectedProfileId;
    expect(id).not.toBe("profile-1");
    expect(hook.result.current.hasSavedVersion).toBe(false);
    expect(hook.result.current.savedRevision).toBeNull();
    expect(hook.result.current.isDirty).toBe(true);
    const body = personaStudioApiMock.createPersonaProfile.mock.calls[0][0];
    expect(body).toEqual({ manifest: { ...manifest, profileIdentity: id, revision: undefined, identity: { ...manifest.identity, name: "Working Copy" } } });
    expect(body).not.toHaveProperty("manifest.revision");
    if (!("manifest" in body)) throw new Error("Expected canonical write");
    await act(async () => pending.resolve(response({ ...body.manifest, revision: 8 })));
    expect(hook.result.current.savedRevision).toBe(8);
    expect(hook.result.current.hasSavedVersion).toBe(true);
    expect(hook.result.current.isDirty).toBe(false);
    act(() => hook.result.current.setSelectedProfileId("profile-1"));
    expect(hook.result.current.selectedSavedManifest).toEqual(manifest);
    expect(hook.result.current.selectedProfile?.name).toBe("Working");
  });

  it("keeps failed copies unsaved across offline reload and can retry creation", async () => {
    const hook = await hydrated();
    personaStudioApiMock.createPersonaProfile.mockRejectedValueOnce(new Error("offline"));
    await act(async () => hook.result.current.saveSelectedProfileAsNew());
    const id = hook.result.current.selectedProfileId;
    expect(hook.result.current.hasSavedVersion).toBe(false);
    expect(hook.result.current.savedRevision).toBeNull();
    expect(hook.result.current.isDirty).toBe(true);
    hook.unmount();
    personaStudioApiMock.fetchPersonaProfiles.mockRejectedValueOnce(new Error("offline"));
    const recovered = renderHook(usePersonaStudioLocalDraftState);
    await act(async () => {});
    expect(recovered.result.current.selectedProfileId).toBe(id);
    expect(recovered.result.current.selectedProfile?.name).toBe("Canonical Persona Copy");
    expect(recovered.result.current.selectedSavedManifest).toBeNull();
    expect(recovered.result.current.isDirty).toBe(true);
    await act(async () => recovered.result.current.saveSelectedProfile());
    expect(personaStudioApiMock.createPersonaProfile).toHaveBeenCalledTimes(2);
    expect(recovered.result.current.hasSavedVersion).toBe(true);
  });

  it("preserves edits made during creation when acknowledgement arrives", async () => {
    const hook = await hydrated();
    const pending = deferred<PersonaStudioBackendProfile>();
    personaStudioApiMock.createPersonaProfile.mockReturnValueOnce(pending.promise);
    act(() => hook.result.current.saveSelectedProfileAsNew());
    const body = personaStudioApiMock.createPersonaProfile.mock.calls[0][0];
    if (!("manifest" in body)) throw new Error("Expected canonical write");
    rename(hook, "Edited copy");
    await act(async () => pending.resolve(response({ ...body.manifest, revision: 3 })));
    expect(hook.result.current.selectedSavedProfile?.name).toBe("Canonical Persona Copy");
    expect(hook.result.current.selectedProfile?.name).toBe("Edited copy");
    expect(hook.result.current.savedRevision).toBe(3);
    expect(hook.result.current.isDirty).toBe(true);
  });

  it("never restores saved authority from localStorage, even with forged revision fields", async () => {
    const local = createPersonaStudioSeedState();
    local.activeTab = "Tools";
    local.draftProfilesById["profile-1"].name = "Recovered work";
    localStorage.setItem(PERSONA_STUDIO_STORAGE_KEY, JSON.stringify({ ...local, savedManifestsById: { "profile-1": manifest }, savedRevision: 999 }));
    personaStudioApiMock.fetchPersonaProfiles.mockRejectedValueOnce(new Error("offline"));
    const hook = renderHook(usePersonaStudioLocalDraftState);
    await act(async () => {});
    expect(hook.result.current.selectedProfile?.name).toBe("Recovered work");
    expect(hook.result.current.activeTab).toBe("Tools");
    expect(hook.result.current.selectedSavedProfile).toBeNull();
    expect(hook.result.current.selectedSavedManifest).toBeNull();
    expect(hook.result.current.savedRevision).toBeNull();
    expect(hook.result.current.hasSavedVersion).toBe(false);
    expect(hook.result.current.isDirty).toBe(true);
    act(() => hook.result.current.resetSelectedProfile());
    expect(hook.result.current.selectedProfile?.name).toBe("Recovered work");
  });

  it("preserves recovered drafts even when they matched the old local cache", async () => {
    persistPersonaStudioLocalState(createPersonaStudioSeedState());
    const hook = await hydrated();
    expect(hook.result.current.selectedSavedManifest).toEqual(manifest);
    expect(hook.result.current.selectedProfile?.name).toBe("Guardian Default");
    expect(hook.result.current.isDirty).toBe(true);
    act(() => hook.result.current.resetSelectedProfile());
    expect(hook.result.current.selectedProfile?.name).toBe("Canonical Persona");
    expect(hook.result.current.isDirty).toBe(false);
  });

  it("preserves edits during list hydration and ignores list revisions older than a write", async () => {
    const pendingList = deferred<PersonaStudioBackendProfile[]>();
    personaStudioApiMock.fetchPersonaProfiles.mockReturnValueOnce(pendingList.promise);
    const hook = renderHook(usePersonaStudioLocalDraftState);
    rename(hook, "Edited before list");
    await act(async () => pendingList.resolve([response()]));
    expect(hook.result.current.selectedProfile?.name).toBe("Edited before list");
    expect(hook.result.current.savedRevision).toBe(17);
    expect(hook.result.current.isDirty).toBe(true);
    hook.unmount();
    localStorage.clear();
    const lateList = deferred<PersonaStudioBackendProfile[]>();
    personaStudioApiMock.fetchPersonaProfiles.mockReturnValueOnce(lateList.promise);
    const next = renderHook(usePersonaStudioLocalDraftState);
    personaStudioApiMock.createPersonaProfile.mockResolvedValueOnce(response({ ...manifest, revision: 31 }));
    await act(async () => next.result.current.saveSelectedProfile());
    await act(async () => lateList.resolve([response()]));
    expect(next.result.current.savedRevision).toBe(31);
    expect(next.result.current.selectedProfile?.name).toBe("Canonical Persona");
    expect(next.result.current.isDirty).toBe(false);
  });

  it.each(["revision", "identity"])("rejects incoherent %s acknowledgements without changing saved state", async (kind) => {
    const hook = await hydrated();
    rename(hook, "Draft");
    const invalid = response({ ...manifest, revision: 20 });
    if (kind === "revision") invalid.current_revision = 19;
    else { invalid.id = "other"; invalid.manifest.profileIdentity = "other"; }
    personaStudioApiMock.updatePersonaProfile.mockResolvedValueOnce(invalid);
    await act(async () => hook.result.current.saveSelectedProfile());
    expect(hook.result.current.savedRevision).toBe(17);
    expect(hook.result.current.selectedProfile?.name).toBe("Draft");
    expect(hook.result.current.isDirty).toBe(true);
  });
});
