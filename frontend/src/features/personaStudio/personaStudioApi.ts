import api from "@/lib/api";

export const PERSONA_PROFILE_API_VERSION = "codexify.persona/v1" as const;

export type PersonaProfileIdentity = {
  name: string;
  description?: string | null;
};

export type PersonaProfilePrompt = {
  systemPrompt: string;
  styleNotes?: string | null;
  directives?: string | null;
};

export type PersonaProfileModel = {
  provider: string;
  model: string;
  temperature: number;
  topK?: number | null;
  topP?: number | null;
  maxTokens?: number | null;
};

export type PersonaProfileVoice = {
  enabled: boolean;
  provider: string;
  voicePreset: string;
  speed: number;
  wakeWord: string;
  interruptible: boolean;
};

export type PersonaProfileCapabilityPermissions = {
  web: boolean;
  email: boolean;
  calendar: boolean;
  cli: boolean;
  filesystem: boolean;
};

export type PersonaProfileCapabilities = {
  pinnedTools: string[];
  allowedTools: string[];
  skills: string[];
  permissions: PersonaProfileCapabilityPermissions;
};

export type PersonaProfileRetrieval = {
  enabled: boolean;
  mode: string;
  topK: number;
  rerank: boolean;
};

export type PersonaProfileManifestWrite = {
  apiVersion: typeof PERSONA_PROFILE_API_VERSION;
  profileIdentity: string;
  identity: PersonaProfileIdentity;
  prompt: PersonaProfilePrompt;
  model: PersonaProfileModel;
  voice?: PersonaProfileVoice | null;
  capabilities?: PersonaProfileCapabilities | null;
  retrieval?: PersonaProfileRetrieval | null;
};

export type PersonaProfileManifest = PersonaProfileManifestWrite & {
  revision: number;
};

export type PersonaStudioBackendProfile = {
  id: string;
  name: string;
  system_prompt: string;
  model_provider: string;
  model_id: string;
  temperature: number;
  api_version: string;
  current_revision: number;
  manifest: PersonaProfileManifest;
  created_at: string | null;
  updated_at: string | null;
};

export type PersonaStudioLegacyProfileWriteBody = {
  id?: string;
  name: string;
  system_prompt: string;
  model_provider: string;
  model_id: string;
  temperature: number;
};

export type PersonaStudioLegacyProfilePatchBody = Partial<
  Pick<
    PersonaStudioLegacyProfileWriteBody,
    "name" | "system_prompt" | "model_provider" | "model_id" | "temperature"
  >
>;

export type PersonaStudioManifestWriteBody = {
  manifest: PersonaProfileManifestWrite;
};

export type PersonaStudioProfileCreateBody =
  | PersonaStudioLegacyProfileWriteBody
  | PersonaStudioManifestWriteBody;

export type PersonaStudioProfileUpdateBody =
  | PersonaStudioLegacyProfilePatchBody
  | PersonaStudioManifestWriteBody;

type PersonaStudioProfileListResponse = {
  ok?: boolean;
  profiles?: PersonaStudioBackendProfile[];
};

type PersonaStudioProfileResponse = {
  ok?: boolean;
  profile?: PersonaStudioBackendProfile | null;
};

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function hasOwn(value: object, key: PropertyKey): boolean {
  return Object.prototype.hasOwnProperty.call(value, key);
}

function requireNonEmptyString(value: unknown, errorCode: string): string {
  if (typeof value !== "string" || value.trim() === "") {
    throw new Error(errorCode);
  }
  return value;
}

function isPositiveInteger(value: unknown): value is number {
  return typeof value === "number" && Number.isInteger(value) && value > 0;
}

function validateManifestCoherence(
  profile: Record<string, unknown>
): PersonaProfileManifest {
  const profileId = requireNonEmptyString(
    profile.id,
    "persona_profile_id_invalid"
  );
  const profileApiVersion = requireNonEmptyString(
    profile.api_version,
    "persona_profile_api_version_invalid"
  );

  if (!isPositiveInteger(profile.current_revision)) {
    throw new Error("persona_profile_current_revision_invalid");
  }

  if (!isRecord(profile.manifest)) {
    throw new Error("persona_profile_manifest_missing");
  }

  const manifest = profile.manifest;
  if (!isPositiveInteger(manifest.revision)) {
    throw new Error("persona_profile_manifest_revision_invalid");
  }
  if (manifest.revision !== profile.current_revision) {
    throw new Error("persona_profile_revision_mismatch");
  }
  if (manifest.profileIdentity !== profileId) {
    throw new Error("persona_profile_identity_mismatch");
  }
  if (manifest.apiVersion !== profileApiVersion) {
    throw new Error("persona_profile_api_version_mismatch");
  }
  if (manifest.apiVersion !== PERSONA_PROFILE_API_VERSION) {
    throw new Error("persona_profile_manifest_api_version_unsupported");
  }
  if (
    !isRecord(manifest.identity) ||
    !isRecord(manifest.prompt) ||
    !isRecord(manifest.model)
  ) {
    throw new Error("persona_profile_manifest_invalid");
  }

  return manifest as unknown as PersonaProfileManifest;
}

function normalizeBackendProfile(
  profile: PersonaStudioBackendProfile | null | undefined
): PersonaStudioBackendProfile {
  if (!isRecord(profile)) {
    throw new Error("persona_profile_missing");
  }

  const manifest = validateManifestCoherence(profile);
  const id = requireNonEmptyString(profile.id, "persona_profile_id_invalid");

  return {
    id: id.trim(),
    name: String(profile.name ?? "").trim(),
    system_prompt: String(profile.system_prompt ?? ""),
    model_provider: String(profile.model_provider ?? "")
      .trim()
      .toLowerCase(),
    model_id: String(profile.model_id ?? "").trim(),
    temperature: Number(profile.temperature ?? 0),
    api_version: String(profile.api_version),
    current_revision: profile.current_revision as number,
    manifest,
    created_at:
      typeof profile.created_at === "string" ? profile.created_at : null,
    updated_at:
      typeof profile.updated_at === "string" ? profile.updated_at : null,
  };
}

function copyOptionalProperty<T extends object, K extends keyof T>(
  target: Record<string, unknown>,
  source: T,
  key: K
): void {
  const value = source[key];
  if (value !== undefined) {
    target[String(key)] = value;
  }
}

function serializeManifestWrite(
  manifest: PersonaProfileManifestWrite
): PersonaProfileManifestWrite {
  const identity: PersonaProfileIdentity = {
    name: manifest.identity.name,
  };
  copyOptionalProperty(identity, manifest.identity, "description");

  const prompt: PersonaProfilePrompt = {
    systemPrompt: manifest.prompt.systemPrompt,
  };
  copyOptionalProperty(prompt, manifest.prompt, "styleNotes");
  copyOptionalProperty(prompt, manifest.prompt, "directives");

  const model: PersonaProfileModel = {
    provider: manifest.model.provider,
    model: manifest.model.model,
    temperature: manifest.model.temperature,
  };
  copyOptionalProperty(model, manifest.model, "topK");
  copyOptionalProperty(model, manifest.model, "topP");
  copyOptionalProperty(model, manifest.model, "maxTokens");

  const payload: PersonaProfileManifestWrite = {
    apiVersion: manifest.apiVersion,
    profileIdentity: manifest.profileIdentity,
    identity,
    prompt,
    model,
  };

  if (manifest.voice !== undefined) {
    payload.voice = manifest.voice
      ? {
          enabled: manifest.voice.enabled,
          provider: manifest.voice.provider,
          voicePreset: manifest.voice.voicePreset,
          speed: manifest.voice.speed,
          wakeWord: manifest.voice.wakeWord,
          interruptible: manifest.voice.interruptible,
        }
      : null;
  }
  if (manifest.capabilities !== undefined) {
    payload.capabilities = manifest.capabilities
      ? {
          pinnedTools: [...manifest.capabilities.pinnedTools],
          allowedTools: [...manifest.capabilities.allowedTools],
          skills: [...manifest.capabilities.skills],
          permissions: {
            web: manifest.capabilities.permissions.web,
            email: manifest.capabilities.permissions.email,
            calendar: manifest.capabilities.permissions.calendar,
            cli: manifest.capabilities.permissions.cli,
            filesystem: manifest.capabilities.permissions.filesystem,
          },
        }
      : null;
  }
  if (manifest.retrieval !== undefined) {
    payload.retrieval = manifest.retrieval
      ? {
          enabled: manifest.retrieval.enabled,
          mode: manifest.retrieval.mode,
          topK: manifest.retrieval.topK,
          rerank: manifest.retrieval.rerank,
        }
      : null;
  }

  return payload;
}

const CREATE_LEGACY_KEYS = [
  "id",
  "name",
  "system_prompt",
  "model_provider",
  "model_id",
  "temperature",
] as const;

const UPDATE_LEGACY_KEYS = [
  "name",
  "system_prompt",
  "model_provider",
  "model_id",
  "temperature",
] as const;

function serializeManifestBody(
  body: Record<string, unknown>,
  legacyKeys: readonly string[]
): PersonaStudioManifestWriteBody {
  const manifest = body.manifest;
  if (!isRecord(manifest)) {
    throw new Error("persona_profile_manifest_invalid");
  }
  if (
    legacyKeys.some(
      (key) => hasOwn(body, key) && body[key] !== undefined
    )
  ) {
    throw new Error("persona_profile_manifest_legacy_mixed");
  }
  return {
    manifest: serializeManifestWrite(
      manifest as unknown as PersonaProfileManifestWrite
    ),
  };
}

function serializeCreateBody(
  body: PersonaStudioProfileCreateBody
): PersonaStudioProfileCreateBody {
  if (isRecord(body) && hasOwn(body, "manifest")) {
    return serializeManifestBody(body, CREATE_LEGACY_KEYS);
  }
  return body;
}

function serializeUpdateBody(
  body: PersonaStudioProfileUpdateBody
): PersonaStudioProfileUpdateBody {
  if (isRecord(body) && hasOwn(body, "manifest")) {
    return serializeManifestBody(body, UPDATE_LEGACY_KEYS);
  }
  return body;
}

export async function fetchPersonaProfiles(): Promise<
  PersonaStudioBackendProfile[]
> {
  const response = await api.get<PersonaStudioProfileListResponse>(
    "/api/persona-profiles"
  );
  const profiles = response.data?.profiles;
  if (profiles == null) {
    return [];
  }
  if (!Array.isArray(profiles)) {
    throw new Error("persona_profile_list_invalid");
  }
  return profiles.map((profile) => normalizeBackendProfile(profile));
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
  body: PersonaStudioProfileCreateBody
): Promise<PersonaStudioBackendProfile> {
  const response = await api.post<PersonaStudioProfileResponse>(
    "/api/persona-profiles",
    serializeCreateBody(body)
  );
  return normalizeBackendProfile(response.data?.profile ?? null);
}

export async function updatePersonaProfile(
  profileId: string,
  body: PersonaStudioProfileUpdateBody
): Promise<PersonaStudioBackendProfile> {
  const response = await api.patch<PersonaStudioProfileResponse>(
    `/api/persona-profiles/${encodeURIComponent(profileId)}`,
    serializeUpdateBody(body)
  );
  return normalizeBackendProfile(response.data?.profile ?? null);
}
