export type {
  PersonaConfig,
  VoiceSettings,
} from "./personaStudioStore";

export const PERSONA_VOICE_PROVIDER_CLASSIFICATION = {
  LOCAL: "local",
  CLOUD: "cloud",
} as const;

export type PersonaVoiceProviderClassification =
  (typeof PERSONA_VOICE_PROVIDER_CLASSIFICATION)[keyof typeof PERSONA_VOICE_PROVIDER_CLASSIFICATION];

export const PERSONA_VOICE_PROVIDER_STATE = {
  AVAILABLE: "available",
  DEGRADED: "degraded",
  UNAVAILABLE: "unavailable",
} as const;

export type PersonaVoiceProviderState =
  (typeof PERSONA_VOICE_PROVIDER_STATE)[keyof typeof PERSONA_VOICE_PROVIDER_STATE];

export type PersonaVoiceProviderCapabilities = {
  presetVoices: boolean;
  cloning: boolean;
  promptDefinedVoice: boolean;
  preview: boolean;
};

export type PersonaVoiceProviderRecord = {
  providerId: string;
  label: string;
  classification: PersonaVoiceProviderClassification;
  state: PersonaVoiceProviderState;
  statusDetail: string;
  capabilities: PersonaVoiceProviderCapabilities;
};

export type PersonaVoiceProviderRegistryEnvelope = {
  providers: PersonaVoiceProviderRecord[];
};

export type PersonaVoiceSelectableVoice = {
  voiceId: string;
  label: string;
  kind: string;
  previewSupported: boolean;
  bindingSupported: boolean;
  summary: string | null;
};

export type PersonaVoiceSelectableVoiceEnvelope = {
  providerId: string;
  state: PersonaVoiceProviderState;
  statusDetail: string;
  voices: PersonaVoiceSelectableVoice[];
};

export type PersonaVoicePreviewArtifact = {
  contentType: string;
  playbackUrl: string;
  expiresInSeconds: number;
  durationMs: number | null;
};

export type PersonaVoicePreviewRequest = {
  provider: string;
  voice_id?: string;
  preset_id?: string;
  sample_text: string;
  output_format?: string;
  speed?: number;
  style?: string;
};

export type PersonaVoicePreviewResponse = {
  providerId: string;
  voiceId: string;
  state: PersonaVoiceProviderState;
  preview: PersonaVoicePreviewArtifact | null;
  appliedRuntimeOptions: Record<string, unknown>;
  ephemeral: boolean;
  persistsPersonaState: boolean;
  linksMessageHistory: boolean;
  statusDetail: string;
};
