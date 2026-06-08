import api from "@/lib/api";
import type {
  TtsBackendListResponse,
  TtsOutputFormat,
  TtsPreviewResponse,
  TtsProfileListResponse,
  TtsVoiceProfile,
  TtsVoiceProfileDraft,
} from "./types";

export async function fetchTtsBackends(): Promise<TtsBackendListResponse> {
  const response = await api.get<TtsBackendListResponse>("/api/tts/backends");
  return response.data;
}

export async function fetchTtsProfiles(): Promise<TtsProfileListResponse> {
  const response = await api.get<TtsProfileListResponse>("/api/tts/profiles");
  return response.data;
}

export async function createTtsProfile(
  profile: Partial<TtsVoiceProfileDraft> & { name: string }
): Promise<TtsVoiceProfile> {
  const response = await api.post<TtsVoiceProfile>("/api/tts/profiles", profile);
  return response.data;
}

export async function updateTtsProfile(
  profileId: string,
  patch: Partial<TtsVoiceProfileDraft>
): Promise<TtsVoiceProfile> {
  const response = await api.patch<TtsVoiceProfile>(
    `/api/tts/profiles/${encodeURIComponent(profileId)}`,
    patch
  );
  return response.data;
}

export async function deleteTtsProfile(profileId: string): Promise<void> {
  await api.delete(`/api/tts/profiles/${encodeURIComponent(profileId)}`);
}

export async function setDefaultTtsProfile(
  profileId: string
): Promise<TtsVoiceProfile> {
  const response = await api.post<TtsVoiceProfile>(
    `/api/tts/profiles/${encodeURIComponent(profileId)}/set-default`
  );
  return response.data;
}

export async function previewTtsProfile(
  profileId: string,
  payload: { text: string; format?: TtsOutputFormat | null }
): Promise<TtsPreviewResponse> {
  const response = await api.post<TtsPreviewResponse>(
    `/api/tts/profiles/${encodeURIComponent(profileId)}/preview`,
    payload
  );
  return response.data;
}
