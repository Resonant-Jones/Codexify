import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import {
  createPersonaProfile as createPersonaProfileOnBackend,
  fetchPersonaProfiles,
  PERSONA_PROFILE_API_VERSION,
  type PersonaProfileManifest,
  type PersonaProfileManifestWrite,
  updatePersonaProfile as updatePersonaProfileOnBackend,
  type PersonaStudioBackendProfile,
} from "@/features/personaStudio/personaStudioApi";

export type PersonaCapabilityPermissions = {
  web: boolean;
  email: boolean;
  calendar: boolean;
  cli: boolean;
  filesystem: boolean;
};

export type ModelSettings = {
  provider: string;
  model: string;
  temperature: number;
  topK: number;
  topP: number;
  maxTokens: number;
};

export type VoiceSettings = {
  enabled: boolean;
  provider: string;
  voicePreset: string;
  speed: number;
  wakeWord: string;
  interruptible: boolean;
};

export type PromptSettings = {
  systemPrompt: string;
  styleNotes: string;
  directives: string;
};

export type ToolsSettings = {
  pinnedTools: string[];
  allowedTools: string[];
  skills: string[];
  permissions: PersonaCapabilityPermissions;
};

export type RetrievalSettings = {
  enabled: boolean;
  mode: string;
  topK: number;
  rerank: boolean;
};

export type PersonaConfig = {
  identity: {
    name: string;
    description: string;
  };
  model: ModelSettings;
  voice: VoiceSettings;
  prompt: PromptSettings;
  tools: ToolsSettings;
  retrieval: RetrievalSettings;
};

export type PersonaProfile = {
  id: string;
  name: string;
  description: string;
  isDefault?: boolean;
};

export type PersonaProfileDraft = PersonaProfile & {
  config: PersonaConfig;
};

export type EditorTab =
  | "Identity"
  | "Model"
  | "Voice"
  | "Prompt"
  | "Tools"
  | "Retrieval"
  | "Truth Matrix";

export type PersonaStudioLocalState = {
  profiles: PersonaProfileDraft[];
  draftProfilesById: Record<string, PersonaProfileDraft>;
  selectedProfileId: string;
  activeTab: EditorTab;
};

export const PERSONA_STUDIO_STORAGE_KEY = "cfy.personaStudio.localState.v1";

const PERSONA_STUDIO_SEED_PROFILES: PersonaProfileDraft[] = [
  {
    id: "profile-1",
    name: "Guardian Default",
    description: "Default guardian persona for general assistance",
    isDefault: true,
    config: {
      identity: {
        name: "Guardian Default",
        description: "Default guardian persona for general assistance",
      },
      model: {
        provider: "openai",
        model: "gpt-4o",
        temperature: 0.7,
        topK: 40,
        topP: 0.95,
        maxTokens: 4096,
      },
      voice: {
        enabled: true,
        provider: "elevenlabs",
        voicePreset: "rachel",
        speed: 1.0,
        wakeWord: "Hey Guardian",
        interruptible: true,
      },
      prompt: {
        systemPrompt:
          "You are a Guardian, a partner in thought. Your primary goal is to foster the user's autonomy and creativity.",
        styleNotes:
          "Use a warm, encouraging tone. Favor questions over statements when appropriate.",
        directives:
          "Always prioritize user privacy. Never share sensitive information without explicit permission.",
      },
      tools: {
        pinnedTools: ["web-search", "calculator", "code-interpreter"],
        allowedTools: [
          "web-search",
          "calculator",
          "code-interpreter",
          "file-reader",
        ],
        skills: ["critical-thinking", "creative-brainstorming"],
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
        topK: 10,
        rerank: true,
      },
    },
  },
  {
    id: "profile-2",
    name: "Code Assistant",
    description: "Specialized for code review and programming tasks",
    config: {
      identity: {
        name: "Code Assistant",
        description: "Specialized for code review and programming tasks",
      },
      model: {
        provider: "anthropic",
        model: "claude-sonnet-4-20250514",
        temperature: 0.3,
        topK: 20,
        topP: 0.9,
        maxTokens: 8192,
      },
      voice: {
        enabled: false,
        provider: "elevenlabs",
        voicePreset: "matt",
        speed: 1.0,
        wakeWord: "",
        interruptible: true,
      },
      prompt: {
        systemPrompt:
          "You are an expert code assistant. Provide clear, concise, and accurate code solutions with explanation.",
        styleNotes: "Be precise and technical. Include code examples where helpful.",
        directives:
          "Always verify code syntax before presenting. Flag potential security issues.",
      },
      tools: {
        pinnedTools: ["code-interpreter", "git", "terminal"],
        allowedTools: ["code-interpreter", "git", "terminal", "web-search", "file-reader"],
        skills: ["code-review", "debugging", "architecture-design"],
        permissions: {
          web: true,
          email: false,
          calendar: false,
          cli: true,
          filesystem: true,
        },
      },
      retrieval: {
        enabled: true,
        mode: "semantic",
        topK: 5,
        rerank: false,
      },
    },
  },
  {
    id: "profile-3",
    name: "Research Partner",
    description: "Focused on research and information synthesis",
    config: {
      identity: {
        name: "Research Partner",
        description: "Focused on research and information synthesis",
      },
      model: {
        provider: "openai",
        model: "gpt-4-turbo",
        temperature: 0.5,
        topK: 60,
        topP: 0.97,
        maxTokens: 16384,
      },
      voice: {
        enabled: true,
        provider: "elevenlabs",
        voicePreset: "aria",
        speed: 0.9,
        wakeWord: "Hey Research",
        interruptible: true,
      },
      prompt: {
        systemPrompt:
          "You are a research partner specializing in information synthesis and critical analysis.",
        styleNotes:
          "Present information in organized, cited format. Distinguish between facts and interpretations.",
        directives:
          "Cite sources when available. Clearly state uncertainty when information is incomplete.",
      },
      tools: {
        pinnedTools: ["web-search", "academic-search", "note-taking"],
        allowedTools: ["web-search", "academic-search", "note-taking", "calculator"],
        skills: ["literature-review", "meta-analysis", "synthesis"],
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
        topK: 20,
        rerank: true,
      },
    },
  },
];

function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeEditorTab(value: unknown): EditorTab | null {
  if (typeof value !== "string") return null;

  switch (value.trim().toLowerCase()) {
    case "identity":
      return "Identity";
    case "model":
      return "Model";
    case "voice":
      return "Voice";
    case "prompt":
      return "Prompt";
    case "tools":
      return "Tools";
    case "retrieval":
      return "Retrieval";
    case "truth matrix":
    case "truth-matrix":
    case "truth_matrix":
    case "truthmatrix":
      return "Truth Matrix";
    default:
      return null;
  }
}

function normalizeStringArray(value: unknown, fallback: string[]): string[] {
  if (!Array.isArray(value)) return clone(fallback);
  return value.filter((item): item is string => typeof item === "string");
}

function normalizePersonaCapabilityPermissions(
  value: unknown,
  fallback: PersonaCapabilityPermissions
): PersonaCapabilityPermissions {
  if (!isRecord(value)) return clone(fallback);

  return {
    web: typeof value.web === "boolean" ? value.web : fallback.web,
    email: typeof value.email === "boolean" ? value.email : fallback.email,
    calendar:
      typeof value.calendar === "boolean" ? value.calendar : fallback.calendar,
    cli: typeof value.cli === "boolean" ? value.cli : fallback.cli,
    filesystem:
      typeof value.filesystem === "boolean" ? value.filesystem : fallback.filesystem,
  };
}

function normalizePersonaConfig(
  value: unknown,
  fallback: PersonaConfig
): PersonaConfig {
  if (!isRecord(value)) return clone(fallback);

  const model = isRecord(value.model) ? value.model : null;
  const voice = isRecord(value.voice) ? value.voice : null;
  const prompt = isRecord(value.prompt) ? value.prompt : null;
  const tools = isRecord(value.tools) ? value.tools : null;
  const retrieval = isRecord(value.retrieval) ? value.retrieval : null;

  return {
    identity: {
      name: typeof value.identity === "object" && value.identity !== null && !Array.isArray(value.identity) && typeof (value.identity as Record<string, unknown>).name === "string"
        ? String((value.identity as Record<string, unknown>).name)
        : fallback.identity.name,
      description:
        typeof value.identity === "object" &&
        value.identity !== null &&
        !Array.isArray(value.identity) &&
        typeof (value.identity as Record<string, unknown>).description === "string"
          ? String((value.identity as Record<string, unknown>).description)
          : fallback.identity.description,
    },
    model: {
      provider: typeof model?.provider === "string" ? model.provider : fallback.model.provider,
      model: typeof model?.model === "string" ? model.model : fallback.model.model,
      temperature:
        typeof model?.temperature === "number"
          ? model.temperature
          : fallback.model.temperature,
      topK: typeof model?.topK === "number" ? model.topK : fallback.model.topK,
      topP: typeof model?.topP === "number" ? model.topP : fallback.model.topP,
      maxTokens:
        typeof model?.maxTokens === "number"
          ? model.maxTokens
          : fallback.model.maxTokens,
    },
    voice: {
      enabled:
        typeof voice?.enabled === "boolean" ? voice.enabled : fallback.voice.enabled,
      provider:
        typeof voice?.provider === "string" ? voice.provider : fallback.voice.provider,
      voicePreset:
        typeof voice?.voicePreset === "string"
          ? voice.voicePreset
          : fallback.voice.voicePreset,
      speed: typeof voice?.speed === "number" ? voice.speed : fallback.voice.speed,
      wakeWord:
        typeof voice?.wakeWord === "string" ? voice.wakeWord : fallback.voice.wakeWord,
      interruptible:
        typeof voice?.interruptible === "boolean"
          ? voice.interruptible
          : fallback.voice.interruptible,
    },
    prompt: {
      systemPrompt:
        typeof prompt?.systemPrompt === "string"
          ? prompt.systemPrompt
          : fallback.prompt.systemPrompt,
      styleNotes:
        typeof prompt?.styleNotes === "string"
          ? prompt.styleNotes
          : fallback.prompt.styleNotes,
      directives:
        typeof prompt?.directives === "string"
          ? prompt.directives
          : fallback.prompt.directives,
    },
    tools: {
      pinnedTools: normalizeStringArray(tools?.pinnedTools, fallback.tools.pinnedTools),
      allowedTools: normalizeStringArray(
        tools?.allowedTools,
        fallback.tools.allowedTools
      ),
      skills: normalizeStringArray(tools?.skills, fallback.tools.skills),
      permissions: normalizePersonaCapabilityPermissions(
        tools?.permissions,
        fallback.tools.permissions
      ),
    },
    retrieval: {
      enabled:
        typeof retrieval?.enabled === "boolean"
          ? retrieval.enabled
          : fallback.retrieval.enabled,
      mode: typeof retrieval?.mode === "string" ? retrieval.mode : fallback.retrieval.mode,
      topK: typeof retrieval?.topK === "number" ? retrieval.topK : fallback.retrieval.topK,
      rerank:
        typeof retrieval?.rerank === "boolean"
          ? retrieval.rerank
          : fallback.retrieval.rerank,
    },
  };
}

function createBlankPersonaProfileDraft(
  profileId: string
): PersonaProfileDraft {
  return {
    id: profileId,
    name: "Persona",
    description: "",
    config: {
      identity: {
        name: "Persona",
        description: "",
      },
      model: {
        provider: "openai",
        model: "gpt-4o",
        temperature: 0.7,
        topK: 40,
        topP: 0.95,
        maxTokens: 4096,
      },
      voice: {
        enabled: false,
        provider: "elevenlabs",
        voicePreset: "",
        speed: 1.0,
        wakeWord: "",
        interruptible: true,
      },
      prompt: {
        systemPrompt: "",
        styleNotes: "",
        directives: "",
      },
      tools: {
        pinnedTools: [],
        allowedTools: [],
        skills: [],
        permissions: {
          web: false,
          email: false,
          calendar: false,
          cli: false,
          filesystem: false,
        },
      },
      retrieval: {
        enabled: false,
        mode: "semantic",
        topK: 5,
        rerank: false,
      },
    },
  };
}

function normalizePersonaProfileDraft(
  value: unknown,
  fallback: PersonaProfileDraft
): PersonaProfileDraft {
  if (!isRecord(value)) return clone(fallback);

  const profileId = typeof value.id === "string" ? value.id : fallback.id;
  const normalizedFallback = fallback.id === profileId ? fallback : getPersonaStudioSeedProfile(profileId);

  return {
    id: profileId,
    name: typeof value.name === "string" ? value.name : normalizedFallback.name,
    description:
      typeof value.description === "string"
        ? value.description
        : normalizedFallback.description,
    ...(typeof value.isDefault === "boolean"
      ? { isDefault: value.isDefault }
      : normalizedFallback.isDefault != null
        ? { isDefault: normalizedFallback.isDefault }
        : {}),
    config: normalizePersonaConfig(value.config, normalizedFallback.config),
  };
}

function normalizePersonaProfileArray(
  value: unknown,
  fallbackProfiles: PersonaProfileDraft[]
): PersonaProfileDraft[] {
  if (!Array.isArray(value)) return clone(fallbackProfiles);

  const nextProfiles: PersonaProfileDraft[] = [];
  const seenProfileIds = new Set<string>();

  for (const profileValue of value) {
    const fallbackId =
      isRecord(profileValue) && typeof profileValue.id === "string"
        ? profileValue.id
        : fallbackProfiles[0]?.id ?? PERSONA_STUDIO_SEED_PROFILES[0]?.id ?? "";
    const normalized = normalizePersonaProfileDraft(
      profileValue,
      getSeedProfileReference(fallbackId)
    );

    if (seenProfileIds.has(normalized.id)) continue;
    seenProfileIds.add(normalized.id);
    nextProfiles.push(normalized);
  }

  return nextProfiles.length > 0 ? nextProfiles : clone(fallbackProfiles);
}

function getSeedProfileReference(profileId?: string | null): PersonaProfileDraft {
  const seedProfile =
    PERSONA_STUDIO_SEED_PROFILES.find((profile) => profile.id === profileId) ??
    PERSONA_STUDIO_SEED_PROFILES[0];
  if (seedProfile) {
    return seedProfile;
  }
  return createBlankPersonaProfileDraft(profileId ?? "profile-1");
}

function createPersonaProfileMap(
  profiles: PersonaProfileDraft[]
): Record<string, PersonaProfileDraft> {
  return Object.fromEntries(
    profiles.map((profile) => [profile.id, cloneProfile(profile)])
  );
}

function createDefaultCopyName(
  sourceName: string,
  existingProfiles: PersonaProfileDraft[]
): string {
  const baseName = sourceName.trim() || "Persona";
  const normalizedBase = baseName.replace(/\s+Copy(?:\s+\d+)?$/i, "");
  const existingNames = new Set(existingProfiles.map((profile) => profile.name));

  let candidate = `${normalizedBase} Copy`;
  let copyIndex = 2;

  while (existingNames.has(candidate)) {
    candidate = `${normalizedBase} Copy ${copyIndex}`;
    copyIndex += 1;
  }

  return candidate;
}

function normalizePersonaStudioLocalState(
  value: unknown
): PersonaStudioLocalState {
  if (!isRecord(value)) return createPersonaStudioSeedState();

  const rawProfiles = Array.isArray(value.profiles) ? value.profiles : [];
  const rawDraftProfilesById = isRecord(value.draftProfilesById)
    ? value.draftProfilesById
    : null;
  const rawLegacySavedProfiles = isRecord(value.lastSavedProfiles)
    ? value.lastSavedProfiles
    : null;

  const profileSource =
    rawProfiles.length > 0
      ? rawProfiles
      : rawDraftProfilesById && Object.keys(rawDraftProfilesById).length > 0
        ? Object.values(rawDraftProfilesById)
        : rawLegacySavedProfiles && Object.keys(rawLegacySavedProfiles).length > 0
          ? Object.values(rawLegacySavedProfiles)
          : PERSONA_STUDIO_SEED_PROFILES;

  const profiles = normalizePersonaProfileArray(
    profileSource,
    PERSONA_STUDIO_SEED_PROFILES
  );
  const profilesById = new Map(profiles.map((profile) => [profile.id, profile]));

  const selectedProfileId =
    typeof value.selectedProfileId === "string" && profilesById.has(value.selectedProfileId)
      ? value.selectedProfileId
      : profiles[0]?.id ?? PERSONA_STUDIO_SEED_PROFILES[0]?.id ?? "";

  if (rawDraftProfilesById) {
    const draftProfilesById: Record<string, PersonaProfileDraft> = {};

    for (const profile of profiles) {
      draftProfilesById[profile.id] = normalizePersonaProfileDraft(
        rawDraftProfilesById[profile.id],
        profile
      );
    }

    return {
      profiles,
      draftProfilesById,
      selectedProfileId,
      activeTab: normalizeEditorTab(value.activeTab) ?? "Identity",
    };
  }

  if (rawLegacySavedProfiles) {
    const draftProfilesById = createPersonaProfileMap(profiles);
    const savedProfiles = profiles.map((profile) => {
      const fallback = getSeedProfileReference(profile.id);
      return normalizePersonaProfileDraft(
        rawLegacySavedProfiles[profile.id] ?? fallback,
        fallback
      );
    });

    return {
      profiles: savedProfiles,
      draftProfilesById,
      selectedProfileId,
      activeTab: normalizeEditorTab(value.activeTab) ?? "Identity",
    };
  }

  return {
    profiles,
    draftProfilesById: createPersonaProfileMap(profiles),
    selectedProfileId,
    activeTab: normalizeEditorTab(value.activeTab) ?? "Identity",
  };
}

function cloneProfile(profile: PersonaProfileDraft): PersonaProfileDraft {
  return clone(profile);
}

// Session-only authority. None of these manifests/revisions are restored from storage.
type PersonaStudioSessionState = PersonaStudioLocalState & {
  savedManifestsById: Record<string, PersonaProfileManifest>;
  hydrationDraftsById: Record<string, PersonaProfileDraft>;
};

function manifestToDraft(
  manifest: PersonaProfileManifest,
  isDefault?: boolean
): PersonaProfileDraft {
  const defaults = createBlankPersonaProfileDraft(manifest.profileIdentity).config;
  return {
    id: manifest.profileIdentity,
    name: manifest.identity.name,
    description: manifest.identity.description ?? "",
    ...(isDefault != null ? { isDefault } : {}),
    config: {
      identity: {
        name: manifest.identity.name,
        description: manifest.identity.description ?? "",
      },
      prompt: {
        systemPrompt: manifest.prompt.systemPrompt,
        styleNotes: manifest.prompt.styleNotes ?? "",
        directives: manifest.prompt.directives ?? "",
      },
      model: {
        provider: manifest.model.provider,
        model: manifest.model.model,
        temperature: manifest.model.temperature,
        topK: manifest.model.topK ?? defaults.model.topK,
        topP: manifest.model.topP ?? defaults.model.topP,
        maxTokens: manifest.model.maxTokens ?? defaults.model.maxTokens,
      },
      voice: clone(manifest.voice ?? defaults.voice),
      tools: clone(manifest.capabilities ?? defaults.tools),
      retrieval: clone(manifest.retrieval ?? defaults.retrieval),
    },
  };
}

function acknowledgedManifest(
  backendProfile: PersonaStudioBackendProfile,
  expectedId = backendProfile.id
): PersonaProfileManifest {
  const manifest = backendProfile.manifest;
  // The API client validates coherence; also bind write acknowledgements to
  // the submitted profile so a response cannot save a different local draft.
  if (
    !manifest || backendProfile.id !== expectedId ||
    manifest.profileIdentity !== expectedId ||
    manifest.apiVersion !== PERSONA_PROFILE_API_VERSION ||
    backendProfile.api_version !== manifest.apiVersion ||
    !Number.isInteger(manifest.revision) || manifest.revision <= 0 ||
    manifest.revision !== backendProfile.current_revision
  ) {
    throw new Error("Invalid Persona acknowledgement");
  }
  return clone(manifest);
}

function acceptManifest(
  previous: PersonaStudioSessionState,
  manifest: PersonaProfileManifest,
  submittedDraft?: PersonaProfileDraft
): PersonaStudioSessionState {
  const id = manifest.profileIdentity;
  const priorManifest = previous.savedManifestsById[id];
  // A delayed list response must not roll back a write acknowledgement.
  if (priorManifest && (
    priorManifest.revision > manifest.revision ||
    (priorManifest.revision === manifest.revision && !submittedDraft)
  )) return previous;

  const cachedProfile = previous.profiles.find((profile) => profile.id === id);
  const savedProfile = manifestToDraft(manifest, cachedProfile?.isDefault);
  const draft = previous.draftProfilesById[id];
  const reconcileDraft = !draft || sameProfileDraft(
    draft,
    submittedDraft ?? previous.hydrationDraftsById[id]
  );

  return {
    ...previous,
    savedManifestsById: { ...previous.savedManifestsById, [id]: manifest },
    profiles: cachedProfile
      ? previous.profiles.map((profile) => profile.id === id ? savedProfile : profile)
      : [...previous.profiles, savedProfile],
    draftProfilesById: {
      ...previous.draftProfilesById,
      [id]: reconcileDraft ? cloneProfile(savedProfile) : draft,
    },
  };
}

function buildPersonaProfileWriteBody(
  profile: PersonaProfileDraft
): { manifest: PersonaProfileManifestWrite } {
  return {
    manifest: {
      apiVersion: PERSONA_PROFILE_API_VERSION,
      profileIdentity: profile.id,
      identity: clone(profile.config.identity),
      prompt: clone(profile.config.prompt),
      model: clone(profile.config.model),
      voice: clone(profile.config.voice),
      capabilities: clone(profile.config.tools),
      retrieval: clone(profile.config.retrieval),
    },
  };
}

export function getPersonaStudioSeedProfile(
  profileId?: string | null
): PersonaProfileDraft {
  return cloneProfile(getSeedProfileReference(profileId));
}

export function createPersonaStudioSeedState(): PersonaStudioLocalState {
  return {
    profiles: clone(PERSONA_STUDIO_SEED_PROFILES),
    draftProfilesById: createPersonaProfileMap(PERSONA_STUDIO_SEED_PROFILES),
    selectedProfileId: PERSONA_STUDIO_SEED_PROFILES[0]?.id ?? "",
    activeTab: "Identity",
  };
}

export function readPersonaStudioLocalState(): PersonaStudioLocalState {
  if (typeof window === "undefined") {
    return createPersonaStudioSeedState();
  }

  try {
    const raw = window.localStorage.getItem(PERSONA_STUDIO_STORAGE_KEY);
    if (!raw) return createPersonaStudioSeedState();
    return normalizePersonaStudioLocalState(JSON.parse(raw));
  } catch {
    return createPersonaStudioSeedState();
  }
}

export function persistPersonaStudioLocalState(state: PersonaStudioLocalState): void {
  if (typeof window === "undefined") return;

  try {
    // Explicitly serialize only draft/cache continuity, even for session state.
    const { profiles, draftProfilesById, selectedProfileId, activeTab } = state;
    window.localStorage.setItem(PERSONA_STUDIO_STORAGE_KEY, JSON.stringify({
      profiles, draftProfilesById, selectedProfileId, activeTab,
    }));
  } catch {
    // Ignore local-only storage failures.
  }
}

export function clearPersonaStudioLocalState(): void {
  if (typeof window === "undefined") return;

  try {
    window.localStorage.removeItem(PERSONA_STUDIO_STORAGE_KEY);
  } catch {
    // Ignore local-only storage failures.
  }
}

function createNextProfileId(profiles: PersonaProfileDraft[]): string {
  const existingIds = new Set(profiles.map((profile) => profile.id));
  let nextIndex = profiles.length + 1;
  let nextId = `profile-${nextIndex}`;

  while (existingIds.has(nextId)) {
    nextIndex += 1;
    nextId = `profile-${nextIndex}`;
  }

  return nextId;
}

function sameProfileDraft(
  left: PersonaProfileDraft | null | undefined,
  right: PersonaProfileDraft | null | undefined
): boolean {
  // Backend JSON and local normalization may order object keys differently.
  // Array ordering remains significant for authored lists.
  const orderedJson = (profile: PersonaProfileDraft | null | undefined) =>
    JSON.stringify(profile ?? null, (_key, value: unknown) => isRecord(value)
      ? Object.fromEntries(Object.keys(value).sort().map((key) => [key, value[key]]))
      : value);
  return orderedJson(left) === orderedJson(right);
}

export function usePersonaStudioLocalDraftState() {
  const [state, setState] = useState<PersonaStudioSessionState>(() => {
    const localState = readPersonaStudioLocalState();
    let hasStoredDrafts = false;
    try {
      hasStoredDrafts = typeof window !== "undefined" &&
        window.localStorage.getItem(PERSONA_STUDIO_STORAGE_KEY) != null;
    } catch {
      // Storage is optional; backend hydration still works.
    }
    return {
      ...localState,
      savedManifestsById: {},
      // Fresh seeds can hydrate automatically. Recovered local work is always
      // retained until explicit reset/save, even if it matched an old cache.
      hydrationDraftsById: hasStoredDrafts ? {} : clone(localState.draftProfilesById),
    };
  });
  const pendingWritesRef = useRef(new Set<string>());
  const sessionGenerationRef = useRef(0);

  useEffect(() => {
    persistPersonaStudioLocalState(state);
  }, [state]);

  useEffect(() => {
    let cancelled = false;
    const generation = sessionGenerationRef.current;
    void (async () => {
      try {
        const manifests = (await fetchPersonaProfiles()).map((profile) =>
          acknowledgedManifest(profile)
        );
        if (cancelled || generation !== sessionGenerationRef.current) return;
        setState((previous) => manifests.reduce(
          (next, manifest) => acceptManifest(next, manifest), previous
        ));
      } catch {
        // Local work remains recoverable but unconfirmed when hydration fails.
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const selectedProfile = useMemo(
    () =>
      state.draftProfilesById[state.selectedProfileId] ??
      state.profiles.find((profile) => profile.id === state.selectedProfileId) ??
      null,
    [state.draftProfilesById, state.profiles, state.selectedProfileId]
  );

  const selectedSavedManifest = state.savedManifestsById[state.selectedProfileId] ?? null;
  const selectedSavedProfile = useMemo(
    () => selectedSavedManifest
      ? manifestToDraft(selectedSavedManifest,
          state.profiles.find((profile) => profile.id === state.selectedProfileId)?.isDefault)
      : null,
    [selectedSavedManifest, state.profiles, state.selectedProfileId]
  );

  const seedProfile = useMemo(
    () => getPersonaStudioSeedProfile(state.selectedProfileId),
    [state.selectedProfileId]
  );

  const isDirty = selectedProfile
    ? !sameProfileDraft(selectedProfile, selectedSavedProfile)
    : false;

  const hasSavedVersion = Boolean(selectedSavedProfile);

  const setSelectedProfileId = useCallback((profileId: string) => {
    setState((previous) => {
      const nextSelectedProfile = previous.profiles.find(
        (profile) => profile.id === profileId
      );

      if (!nextSelectedProfile) {
        return previous;
      }

      if (previous.selectedProfileId === profileId) {
        return previous;
      }

      if (previous.draftProfilesById[profileId]) {
        return {
          ...previous,
          selectedProfileId: profileId,
        };
      }

      return {
        ...previous,
        draftProfilesById: {
          ...previous.draftProfilesById,
          [profileId]: cloneProfile(nextSelectedProfile),
        },
        selectedProfileId: profileId,
      };
    });
  }, []);

  const setActiveTab = useCallback((activeTab: EditorTab) => {
    setState((previous) =>
      previous.activeTab === activeTab
        ? previous
        : {
            ...previous,
            activeTab,
          }
    );
  }, []);

  const updateSelectedProfile = useCallback(
    (updater: (currentProfile: PersonaProfileDraft) => PersonaProfileDraft) => {
      setState((previous) => {
        const currentProfile = previous.profiles.find(
          (profile) => profile.id === previous.selectedProfileId
        );

        if (!currentProfile) return previous;

        const currentDraft =
          previous.draftProfilesById[currentProfile.id] ?? cloneProfile(currentProfile);
        const nextProfile = updater(cloneProfile(currentDraft));
        if (sameProfileDraft(nextProfile, currentDraft)) return previous;

        return {
          ...previous,
          draftProfilesById: {
            ...previous.draftProfilesById,
            [currentProfile.id]: nextProfile,
          },
        };
      });
    },
    []
  );

  const persistProfile = useCallback(async (
    submitted: PersonaProfileDraft,
    create: boolean
  ) => {
    const id = submitted.id;
    // Bound one request per profile in this editor; a second click cannot
    // introduce overlapping writes or locally predicted revision ordering.
    if (pendingWritesRef.current.has(id)) return;
    pendingWritesRef.current.add(id);
    const generation = sessionGenerationRef.current;
    try {
      const body = buildPersonaProfileWriteBody(submitted);
      const response = create
        ? await createPersonaProfileOnBackend(body)
        : await updatePersonaProfileOnBackend(id, body);
      const manifest = acknowledgedManifest(response, id);
      if (generation !== sessionGenerationRef.current) return;
      setState((previous) => acceptManifest(previous, manifest, submitted));
    } catch {
      // Neither failure nor request acceptance establishes saved state.
      // Preserve both the last acknowledged baseline and all draft work.
    } finally {
      pendingWritesRef.current.delete(id);
    }
  }, []);

  const saveSelectedProfile = useCallback(() => {
    if (!selectedProfile || !isDirty) return;
    void persistProfile(cloneProfile(selectedProfile), !selectedSavedManifest);
  }, [selectedProfile, selectedSavedManifest, isDirty, persistProfile]);

  const saveSelectedProfileAsNew = useCallback(() => {
    const currentProfile = state.profiles.find(
      (profile) => profile.id === state.selectedProfileId
    );

    if (!currentProfile) {
      return;
    }

    const nextId = createNextProfileId(state.profiles);
    const currentDraft =
      state.draftProfilesById[currentProfile.id] ?? cloneProfile(currentProfile);
    const nextProfile = cloneProfile(currentDraft);
    nextProfile.id = nextId;
    nextProfile.name = createDefaultCopyName(currentDraft.name, state.profiles);
    nextProfile.description = currentDraft.description;
    nextProfile.isDefault = false;
    nextProfile.config = {
      ...nextProfile.config,
      identity: {
        ...nextProfile.config.identity,
        name: nextProfile.name,
        description: nextProfile.description,
      },
    };

    setState((previous) => ({
      ...previous,
      profiles: [...previous.profiles, nextProfile],
      draftProfilesById: {
        ...previous.draftProfilesById,
        [nextId]: cloneProfile(nextProfile),
      },
      selectedProfileId: nextId,
    }));
    void persistProfile(cloneProfile(nextProfile), true);
  }, [state, persistProfile]);

  const resetSelectedProfile = useCallback(() => {
    setState((previous) => {
      const currentProfile = previous.profiles.find(
        (profile) => profile.id === previous.selectedProfileId
      );

      if (!currentProfile) return previous;

      const manifest = previous.savedManifestsById[currentProfile.id];
      if (!manifest) return previous;
      const nextProfile = manifestToDraft(manifest, currentProfile.isDefault);
      const currentDraft = previous.draftProfilesById[currentProfile.id];

      if (sameProfileDraft(currentDraft, nextProfile)) {
        return previous;
      }

      return {
        ...previous,
        draftProfilesById: {
          ...previous.draftProfilesById,
          [currentProfile.id]: nextProfile,
        },
      };
    });
  }, []);

  const resetAllLocalPersonaStudioData = useCallback(() => {
    sessionGenerationRef.current += 1;
    setState({
      ...createPersonaStudioSeedState(),
      savedManifestsById: {},
      hydrationDraftsById: {},
    });
  }, []);

  return {
    ...state,
    selectedProfile,
    selectedSavedProfile,
    selectedSavedManifest,
    savedRevision: selectedSavedManifest?.revision ?? null,
    seedProfile,
    isDirty,
    hasSavedVersion,
    setSelectedProfileId,
    setActiveTab,
    updateSelectedProfile,
    saveSelectedProfile,
    saveSelectedProfileAsNew,
    resetSelectedProfile,
    resetAllLocalPersonaStudioData,
  };
}
