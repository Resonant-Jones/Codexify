import api from "@/lib/api";

export type PersonaStudioBackendProfile = {
  id: string;
  name: string;
  system_prompt: string;
  model_provider: string;
  model_id: string;
  temperature: number;
  created_at: string | null;
  updated_at: string | null;
};

type PersonaStudioProfileListResponse = {
  ok?: boolean;
  profiles?: PersonaStudioBackendProfile[];
};

type PersonaStudioProfileResponse = {
  ok?: boolean;
  profile?: PersonaStudioBackendProfile | null;
};

type PersonaStudioProfileWriteBody = {
  id?: string;
  name: string;
  system_prompt: string;
  model_provider: string;
  model_id: string;
  temperature: number;
};

type PersonaStudioProfilePatchBody = Partial<
  Pick<
    PersonaStudioProfileWriteBody,
    "name" | "system_prompt" | "model_provider" | "model_id" | "temperature"
  >
>;

function normalizeBackendProfile(
  profile: PersonaStudioBackendProfile | null | undefined
): PersonaStudioBackendProfile {
  if (!profile) {
    throw new Error("persona_profile_missing");
  }

  return {
    id: String(profile.id ?? "").trim(),
    name: String(profile.name ?? "").trim(),
    system_prompt: String(profile.system_prompt ?? ""),
    model_provider: String(profile.model_provider ?? "").trim().toLowerCase(),
    model_id: String(profile.model_id ?? "").trim(),
    temperature: Number(profile.temperature ?? 0),
    created_at:
      typeof profile.created_at === "string" ? profile.created_at : null,
    updated_at:
      typeof profile.updated_at === "string" ? profile.updated_at : null,
  };
}

export async function fetchPersonaProfiles(): Promise<PersonaStudioBackendProfile[]> {
  const response = await api.get<PersonaStudioProfileListResponse>(
    "/api/persona-profiles"
  );
  return (response.data?.profiles ?? [])
    .map((profile) => {
      try {
        return normalizeBackendProfile(profile);
      } catch {
        return null;
      }
    })
    .filter((profile): profile is PersonaStudioBackendProfile => Boolean(profile));
}

export async function fetchPersonaProfile(
  profileId: string
): Promise<PersonaStudioBackendProfile> {
  const response = await api.get<PersonaStudioProfileResponse>(
    `/api/persona-profiles/${encodeURIComponent(profileId)}`
  );
  return normalizeBackendProfile(response.data?.profile ?? null);
}

export async function createPersonaProfile(
  body: PersonaStudioProfileWriteBody
): Promise<PersonaStudioBackendProfile> {
  const response = await api.post<PersonaStudioProfileResponse>(
    "/api/persona-profiles",
    body
  );
  return normalizeBackendProfile(response.data?.profile ?? null);
}

export async function updatePersonaProfile(
  profileId: string,
  body: PersonaStudioProfilePatchBody
): Promise<PersonaStudioBackendProfile> {
  const response = await api.patch<PersonaStudioProfileResponse>(
    `/api/persona-profiles/${encodeURIComponent(profileId)}`,
    body
  );
  return normalizeBackendProfile(response.data?.profile ?? null);
}
