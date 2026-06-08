export type TtsOutputFormat = "wav" | "mp3";

export type TtsVoiceProfile = {
  id: string;
  name: string;
  backend_id: string;
  is_default: boolean;
  description: string | null;
  voice_mode: string;
  speaker: string | null;
  voice_prompt: string | null;
  style_instructions: string | null;
  language: string | null;
  speed: number | null;
  temperature: number | null;
  top_k: number | null;
  top_p: number | null;
  repetition_penalty: number | null;
  max_new_tokens: number | null;
  do_sample: boolean | null;
  backend_params: Record<string, unknown>;
  reference_audio_asset_id: string | null;
  reference_text: string | null;
  x_vector_only_mode: boolean | null;
  sample_rate: number | null;
  output_format: TtsOutputFormat | null;
  loudness_normalization: boolean | null;
  pause_profile: Record<string, unknown> | null;
  created_at: string | null;
  updated_at: string | null;
};

export type TtsBackendControl = {
  id: string;
  label: string;
  type: "asset" | "boolean" | "number" | "select" | "text" | "textarea";
  group: "common" | "advanced" | "conditional";
  backend_native: boolean;
  delivery_control: boolean;
  backend_param?: boolean;
  backend_parameter?: string | null;
  preview_supported?: boolean;
  min?: number;
  max?: number;
  step?: number;
};

export type TtsBackendInfo = {
  backend_id: string;
  display_name: string;
  local_only: boolean;
  active: boolean;
  controls: TtsBackendControl[];
  health?: Record<string, unknown>;
};

export type TtsProfileListResponse = {
  items: TtsVoiceProfile[];
  default_profile_id: string | null;
};

export type TtsBackendListResponse = {
  active_backend_id: string;
  local_only: boolean;
  items: TtsBackendInfo[];
};

export type TtsPreviewResponse = {
  profile: TtsVoiceProfile;
  preview: Record<string, unknown>;
  artifact: {
    output_path: string | null;
    media_url: string | null;
    format: TtsOutputFormat;
    bytes_written: number | null;
  };
};

export type TtsVoiceProfileDraft = Omit<
  TtsVoiceProfile,
  "created_at" | "updated_at"
> & {
  created_at?: string | null;
  updated_at?: string | null;
};
