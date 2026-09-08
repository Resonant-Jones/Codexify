import { beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/api", () => ({
  default: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn(),
  },
}));

import api from "@/lib/api";

import {
  createPersonaProfile,
  fetchPersonaProfile,
  fetchPersonaProfiles,
  PERSONA_PROFILE_API_VERSION,
  updatePersonaProfile,
  type PersonaProfileManifest,
  type PersonaStudioBackendProfile,
  type PersonaStudioProfileCreateBody,
} from "../personaStudioApi";

const apiMock = vi.mocked(api);

function makeManifest(
  overrides: Partial<PersonaProfileManifest> = {}
): PersonaProfileManifest {
  const manifest: PersonaProfileManifest = {
    apiVersion: PERSONA_PROFILE_API_VERSION,
    profileIdentity: "profile-1",
    revision: 7,
    identity: {
      name: "Canonical Persona",
      description: "Full authored identity description",
    },
    prompt: {
      systemPrompt: "Canonical system prompt",
      styleNotes: "Use precise language",
      directives: "Do not invent authority",
    },
    model: {
      provider: "local_openai_compatible",
      model: "qwen3",
      temperature: 0.35,
      topK: 24,
      topP: 0.92,
      maxTokens: 4096,
    },
    voice: {
      enabled: true,
      provider: "local_openai_compatible",
      voicePreset: "alloy",
      speed: 1.05,
      wakeWord: "Hey Guardian",
      interruptible: true,
    },
    capabilities: {
      pinnedTools: ["calculator"],
      allowedTools: ["calculator", "web-search"],
      skills: ["critical-thinking"],
      permissions: {
        web: true,
        email: false,
        calendar: false,
        cli: false,
        filesystem: true,
      },
    },
    retrieval: {
      enabled: true,
      mode: "hybrid",
      topK: 12,
      rerank: true,
    },
  };

  return {
    ...manifest,
    ...overrides,
    identity: { ...manifest.identity, ...overrides.identity },
    prompt: { ...manifest.prompt, ...overrides.prompt },
    model: { ...manifest.model, ...overrides.model },
  };
}

function makeProfile(
  overrides: Partial<PersonaStudioBackendProfile> = {}
): PersonaStudioBackendProfile {
  const id = overrides.id ?? "profile-1";
  const manifest =
    overrides.manifest ??
    makeManifest({
      profileIdentity: id,
      revision: overrides.current_revision ?? 7,
    });

  return {
    id,
    name: manifest.identity.name,
    system_prompt: manifest.prompt.systemPrompt,
    model_provider: manifest.model.provider,
    model_id: manifest.model.model,
    temperature: manifest.model.temperature,
    api_version: manifest.apiVersion,
    current_revision: manifest.revision,
    manifest,
    created_at: "2026-09-06T00:00:00.000Z",
    updated_at: "2026-09-06T00:00:00.000Z",
    ...overrides,
  };
}

function responseFor(profile: PersonaStudioBackendProfile) {
  return { data: { ok: true, profile } } as never;
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Persona Studio canonical manifest API", () => {
  it("normalizes canonical list responses without dropping manifest fields", async () => {
    const profile = makeProfile();
    apiMock.get.mockResolvedValueOnce({
      data: { ok: true, profiles: [profile] },
    } as never);

    const result = await fetchPersonaProfiles();

    expect(result).toEqual([profile]);
    expect(result[0]).toMatchObject({
      id: profile.id,
      api_version: PERSONA_PROFILE_API_VERSION,
      current_revision: 7,
      manifest: profile.manifest,
    });
    expect(result[0]?.manifest.voice).toEqual(profile.manifest.voice);
    expect(result[0]?.manifest.capabilities).toEqual(
      profile.manifest.capabilities
    );
    expect(result[0]?.manifest.retrieval).toEqual(profile.manifest.retrieval);
  });

  it("normalizes a canonical single-profile response", async () => {
    const profile = makeProfile({ id: "profile-single" });
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    const result = await fetchPersonaProfile("profile/single");

    expect(apiMock.get).toHaveBeenCalledWith(
      "/api/persona-profiles/profile%2Fsingle"
    );
    expect(result).toEqual(profile);
  });

  it("preserves a manifest with optional sections absent", async () => {
    const completeManifest = makeManifest();
    const { voice, capabilities, retrieval, ...manifestWithoutOptional } =
      completeManifest;
    void voice;
    void capabilities;
    void retrieval;
    const profile = makeProfile({
      manifest: manifestWithoutOptional,
    });
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    const result = await fetchPersonaProfile(profile.id);

    expect(result.manifest).toEqual(manifestWithoutOptional);
    expect(result.manifest).not.toHaveProperty("voice");
    expect(result.manifest).not.toHaveProperty("capabilities");
    expect(result.manifest).not.toHaveProperty("retrieval");
  });

  it.each([
    ["current revision zero", { current_revision: 0 }, "current_revision_invalid"],
    ["current revision fractional", { current_revision: 1.5 }, "current_revision_invalid"],
    [
      "manifest revision zero",
      { current_revision: 2, manifest: makeManifest({ revision: 0 }) },
      "manifest_revision_invalid",
    ],
  ])("rejects %s", async (_label, overrides, errorCode) => {
    const profile = makeProfile(overrides);
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    await expect(fetchPersonaProfile(profile.id)).rejects.toThrow(
      `persona_profile_${errorCode}`
    );
  });

  it("rejects a revision pointer that disagrees with the manifest snapshot", async () => {
    const profile = makeProfile({
      current_revision: 8,
      manifest: makeManifest({ revision: 7 }),
    });
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    await expect(fetchPersonaProfile(profile.id)).rejects.toThrow(
      "persona_profile_revision_mismatch"
    );
  });

  it("rejects a manifest profile identity mismatch", async () => {
    const profile = makeProfile({
      manifest: makeManifest({ profileIdentity: "different-profile" }),
    });
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    await expect(fetchPersonaProfile(profile.id)).rejects.toThrow(
      "persona_profile_identity_mismatch"
    );
  });

  it("rejects a manifest and profile API-version mismatch", async () => {
    const profile = makeProfile({ api_version: "codexify.persona/v2" });
    apiMock.get.mockResolvedValueOnce(responseFor(profile));

    await expect(fetchPersonaProfile(profile.id)).rejects.toThrow(
      "persona_profile_api_version_mismatch"
    );
  });

  it("fails closed when the canonical manifest is missing", async () => {
    const profile = makeProfile();
    const response = {
      ...profile,
      manifest: undefined,
    } as unknown as PersonaStudioBackendProfile;
    apiMock.get.mockResolvedValueOnce(responseFor(response));

    await expect(fetchPersonaProfile(profile.id)).rejects.toThrow(
      "persona_profile_manifest_missing"
    );
  });

  it("sends a canonical create request without persisted revision", async () => {
    const persistedManifest = makeManifest({ revision: 19 });
    const { revision: _revision, ...authoredManifest } = persistedManifest;
    apiMock.post.mockResolvedValueOnce(
      responseFor(makeProfile({ manifest: persistedManifest }))
    );

    await createPersonaProfile({ manifest: persistedManifest });

    expect(apiMock.post).toHaveBeenCalledWith("/api/persona-profiles", {
      manifest: authoredManifest,
    });
    const sentBody = apiMock.post.mock.calls[0]?.[1] as {
      manifest: Record<string, unknown>;
    };
    expect(sentBody.manifest).not.toHaveProperty("revision");
  });

  it("sends a canonical update request without persisted revision", async () => {
    const persistedManifest = makeManifest({
      profileIdentity: "profile-update",
      revision: 23,
    });
    const { revision: _revision, ...authoredManifest } = persistedManifest;
    apiMock.patch.mockResolvedValueOnce(
      responseFor(
        makeProfile({ id: "profile-update", manifest: persistedManifest })
      )
    );

    await updatePersonaProfile("profile-update", { manifest: persistedManifest });

    expect(apiMock.patch).toHaveBeenCalledWith(
      "/api/persona-profiles/profile-update",
      { manifest: authoredManifest }
    );
    const sentBody = apiMock.patch.mock.calls[0]?.[1] as {
      manifest: Record<string, unknown>;
    };
    expect(sentBody.manifest).not.toHaveProperty("revision");
  });

  it("rejects mixed canonical and legacy create fields before sending", async () => {
    const mixed = {
      manifest: makeManifest(),
      name: "legacy field",
    } as unknown as PersonaStudioProfileCreateBody;

    await expect(createPersonaProfile(mixed)).rejects.toThrow(
      "persona_profile_manifest_legacy_mixed"
    );
    expect(apiMock.post).not.toHaveBeenCalled();
  });

  it("keeps legacy create and update request bodies operational", async () => {
    const legacyCreate = {
      id: "legacy-profile",
      name: "Legacy Persona",
      system_prompt: "Legacy prompt",
      model_provider: "OpenAI",
      model_id: "gpt-4o",
      temperature: 0.7,
    };
    const legacyUpdate = {
      name: "Updated Legacy Persona",
      temperature: 0.4,
    };
    apiMock.post.mockResolvedValueOnce(
      responseFor(
        makeProfile({
          id: "legacy-profile",
          name: "Legacy Persona",
          system_prompt: "Legacy prompt",
          model_provider: "openai",
          model_id: "gpt-4o",
          temperature: 0.7,
        })
      )
    );
    apiMock.patch.mockResolvedValueOnce(
      responseFor(
        makeProfile({
          id: "legacy-profile",
          name: "Updated Legacy Persona",
          temperature: 0.4,
        })
      )
    );

    await createPersonaProfile(legacyCreate);
    await updatePersonaProfile("legacy-profile", legacyUpdate);

    expect(apiMock.post).toHaveBeenCalledWith(
      "/api/persona-profiles",
      legacyCreate
    );
    expect(apiMock.patch).toHaveBeenCalledWith(
      "/api/persona-profiles/legacy-profile",
      legacyUpdate
    );
  });
});
