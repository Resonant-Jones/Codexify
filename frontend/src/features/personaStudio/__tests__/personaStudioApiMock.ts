import { vi } from "vitest";

import type { PersonaStudioBackendProfile } from "../personaStudioApi";

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function nowIso(): string {
  return new Date().toISOString();
}

function normalizeProfile(
  profile: Partial<PersonaStudioBackendProfile> & Pick<PersonaStudioBackendProfile, "id">
): PersonaStudioBackendProfile {
  const timestamp = nowIso();
  return {
    id: profile.id,
    name: String(profile.name ?? "Persona").trim() || "Persona",
    system_prompt: String(profile.system_prompt ?? ""),
    model_provider: String(profile.model_provider ?? "openai")
      .trim()
      .toLowerCase(),
    model_id: String(profile.model_id ?? "gpt-4o").trim() || "gpt-4o",
    temperature: Number(profile.temperature ?? 0.7),
    created_at: profile.created_at ?? timestamp,
    updated_at: profile.updated_at ?? timestamp,
  };
}

let backendProfiles: PersonaStudioBackendProfile[] = [];

function upsertProfile(
  profile: Partial<PersonaStudioBackendProfile> & Pick<PersonaStudioBackendProfile, "id">
): PersonaStudioBackendProfile {
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

export const personaStudioApiMock = {
  fetchPersonaProfiles: vi.fn(async () => clone(backendProfiles)),
  fetchPersonaProfile: vi.fn(async (profileId: string) => {
    const profile = backendProfiles.find((candidate) => candidate.id === profileId);
    if (!profile) {
      throw new Error(`persona_profile_missing:${profileId}`);
    }
    return clone(profile);
  }),
  createPersonaProfile: vi.fn(async (body: any) => {
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
  updatePersonaProfile: vi.fn(async (profileId: string, body: any) => {
    const profile = upsertProfile({
      id: profileId,
      name: body.name ?? backendProfiles.find((candidate) => candidate.id === profileId)?.name ?? "Persona",
      system_prompt:
        body.system_prompt ??
        backendProfiles.find((candidate) => candidate.id === profileId)?.system_prompt ??
        "",
      model_provider:
        body.model_provider ??
        backendProfiles.find((candidate) => candidate.id === profileId)?.model_provider ??
        "openai",
      model_id:
        body.model_id ??
        backendProfiles.find((candidate) => candidate.id === profileId)?.model_id ??
        "gpt-4o",
      temperature:
        body.temperature ??
        backendProfiles.find((candidate) => candidate.id === profileId)?.temperature ??
        0.7,
    });
    return clone(profile);
  }),
};

export function resetPersonaStudioApiMock(
  profiles: PersonaStudioBackendProfile[] = []
): void {
  backendProfiles = clone(profiles);
  personaStudioApiMock.fetchPersonaProfiles.mockClear();
  personaStudioApiMock.fetchPersonaProfile.mockClear();
  personaStudioApiMock.createPersonaProfile.mockClear();
  personaStudioApiMock.updatePersonaProfile.mockClear();
}
