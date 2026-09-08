import { vi } from "vitest";

import type {
  PersonaProfileManifest,
  PersonaProfileManifestWrite,
  PersonaStudioBackendProfile,
  PersonaStudioProfileCreateBody,
  PersonaStudioProfileUpdateBody,
} from "../personaStudioApi";

const PERSONA_PROFILE_API_VERSION = "codexify.persona/v1" as const;

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function nowIso(): string {
  return new Date().toISOString();
}

type PersonaStudioProfileSeed = Partial<PersonaStudioBackendProfile> &
  Pick<PersonaStudioBackendProfile, "id">;

function createLegacyManifest(
  id: string,
  name: string,
  systemPrompt: string,
  modelProvider: string,
  modelId: string,
  temperature: number,
  revision: number
): PersonaProfileManifest {
  return {
    apiVersion: PERSONA_PROFILE_API_VERSION,
    profileIdentity: id,
    identity: { name },
    prompt: { systemPrompt },
    model: {
      provider: modelProvider,
      model: modelId,
      temperature,
    },
    revision,
  };
}

export function normalizeProfile(profile: PersonaStudioProfileSeed): PersonaStudioBackendProfile {
  const timestamp = nowIso();
  const suppliedManifest = profile.manifest ? clone(profile.manifest) : null;
  const suppliedRevision = profile.current_revision ?? suppliedManifest?.revision ?? 1;
  const revision = Number.isInteger(suppliedRevision) && suppliedRevision > 0
    ? suppliedRevision
    : 1;

  const legacyName = String(profile.name ?? "Persona").trim() || "Persona";
  const legacySystemPrompt = String(profile.system_prompt ?? "");
  const legacyModelProvider = String(profile.model_provider ?? "openai")
    .trim()
    .toLowerCase();
  const legacyModelId = String(profile.model_id ?? "gpt-4o").trim() || "gpt-4o";
  const legacyTemperature = Number(profile.temperature ?? 0.7);
  const manifest = suppliedManifest ?? createLegacyManifest(
    profile.id,
    legacyName,
    legacySystemPrompt,
    legacyModelProvider,
    legacyModelId,
    legacyTemperature,
    revision
  );

  return {
    id: profile.id,
    name: manifest.identity.name,
    system_prompt: manifest.prompt.systemPrompt,
    model_provider: manifest.model.provider,
    model_id: manifest.model.model,
    temperature: manifest.model.temperature,
    api_version: manifest.apiVersion,
    current_revision: manifest.revision,
    manifest,
    created_at: profile.created_at ?? timestamp,
    updated_at: profile.updated_at ?? timestamp,
  };
}

let backendProfiles: PersonaStudioBackendProfile[] = [];

function upsertProfile(profile: PersonaStudioProfileSeed): PersonaStudioBackendProfile {
  const nextProfile = normalizeProfile(profile);
  const existingIndex = backendProfiles.findIndex(
    (candidate) => candidate.id === nextProfile.id
  );
  if (existingIndex >= 0) {
    const existing = backendProfiles[existingIndex];
    const merged: PersonaStudioBackendProfile = {
      ...existing,
      ...nextProfile,
      created_at: existing.created_at ?? nextProfile.created_at,
      updated_at: nowIso(),
    };
    backendProfiles = backendProfiles.map((candidate, index) =>
      index === existingIndex ? merged : candidate
    );
    return merged;
  }

  const created: PersonaStudioBackendProfile = {
    ...nextProfile,
    created_at: nextProfile.created_at ?? nowIso(),
    updated_at: nowIso(),
  };
  backendProfiles = [...backendProfiles, created];
  return created;
}

function existingProfile(profileId: string): PersonaStudioBackendProfile | undefined {
  return backendProfiles.find((candidate) => candidate.id === profileId);
}

function mergeLegacyUpdateIntoManifest(
  profileId: string,
  body: Exclude<PersonaStudioProfileUpdateBody, { manifest: unknown }>
): PersonaProfileManifest {
  const existing = existingProfile(profileId);
  const base = existing?.manifest ?? createLegacyManifest(
    profileId,
    "Persona",
    "",
    "openai",
    "gpt-4o",
    0.7,
    1
  );
  const nextManifest: PersonaProfileManifest = {
    ...clone(base),
    identity: { ...base.identity },
    prompt: { ...base.prompt },
    model: { ...base.model },
    revision: existing ? existing.current_revision + 1 : base.revision,
  };

  if (body.name !== undefined) nextManifest.identity.name = body.name;
  if (body.system_prompt !== undefined) {
    nextManifest.prompt.systemPrompt = body.system_prompt;
  }
  if (body.model_provider !== undefined) {
    nextManifest.model.provider = body.model_provider.toLowerCase();
  }
  if (body.model_id !== undefined) nextManifest.model.model = body.model_id;
  if (body.temperature !== undefined) {
    nextManifest.model.temperature = body.temperature;
  }

  return nextManifest;
}

export const personaStudioApiMock = {
  PERSONA_PROFILE_API_VERSION,
  fetchPersonaProfiles: vi.fn(async () => clone(backendProfiles)),
  fetchPersonaProfile: vi.fn(async (profileId: string) => {
    const profile = existingProfile(profileId);
    if (!profile) {
      throw new Error(`persona_profile_missing:${profileId}`);
    }
    return clone(profile);
  }),
  createPersonaProfile: vi.fn(async (body: PersonaStudioProfileCreateBody) => {
    if ("manifest" in body) {
      const manifest = body.manifest as PersonaProfileManifestWrite;
      const profile = upsertProfile({
        id: manifest.profileIdentity,
        manifest: {
          ...clone(manifest),
          revision: 1,
        },
      });
      return clone(profile);
    }

    const profile = upsertProfile({
      id: String(body.id ?? `profile-${backendProfiles.length + 1}`),
      name: body.name,
      system_prompt: body.system_prompt,
      model_provider: body.model_provider,
      model_id: body.model_id,
      temperature: body.temperature,
    });
    return clone(profile);
  }),
  updatePersonaProfile: vi.fn(async (
    profileId: string,
    body: PersonaStudioProfileUpdateBody
  ) => {
    if ("manifest" in body) {
      const existing = existingProfile(profileId);
      const manifest = body.manifest as PersonaProfileManifestWrite;
      const profile = upsertProfile({
        id: profileId,
        manifest: {
          ...clone(manifest),
          revision: existing ? existing.current_revision + 1 : 1,
        },
      });
      return clone(profile);
    }

    const profile = upsertProfile({
      id: profileId,
      manifest: mergeLegacyUpdateIntoManifest(profileId, body),
    });
    return clone(profile);
  }),
};

export function resetPersonaStudioApiMock(
  profiles: PersonaStudioProfileSeed[] = []
): void {
  backendProfiles = profiles.map((profile) => normalizeProfile(profile));
  personaStudioApiMock.fetchPersonaProfiles.mockClear();
  personaStudioApiMock.fetchPersonaProfile.mockClear();
  personaStudioApiMock.createPersonaProfile.mockClear();
  personaStudioApiMock.updatePersonaProfile.mockClear();
}
