import api from "@/lib/api";

export type UserProfileRecord = {
  user_id: string;
  display_name: string | null;
  avatar_url: string | null;
  timezone: string | null;
  created_at: string | null;
  updated_at: string | null;
};

type UserProfileEnvelope = {
  ok?: boolean;
  profile?: UserProfileRecord | null;
};

export type UserProfileUpdateRequest = {
  display_name?: string | null;
  avatar_url?: string | null;
  timezone?: string | null;
};

function normalizeOptionalText(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function normalizeProfile(
  profile: UserProfileRecord | null | undefined
): UserProfileRecord {
  const userId = String(profile?.user_id ?? "").trim();
  if (!userId) {
    throw new Error("user_profile_missing");
  }

  return {
    user_id: userId,
    display_name: normalizeOptionalText(profile?.display_name),
    avatar_url: normalizeOptionalText(profile?.avatar_url),
    timezone: normalizeOptionalText(profile?.timezone),
    created_at:
      typeof profile?.created_at === "string" ? profile.created_at : null,
    updated_at:
      typeof profile?.updated_at === "string" ? profile.updated_at : null,
  };
}

function normalizeUpdateRequest(
  body: UserProfileUpdateRequest
): UserProfileUpdateRequest {
  const request: UserProfileUpdateRequest = {};

  if (body.display_name !== undefined) {
    request.display_name = body.display_name;
  }
  if (body.avatar_url !== undefined) {
    request.avatar_url = body.avatar_url;
  }
  if (body.timezone !== undefined) {
    request.timezone = body.timezone;
  }

  return request;
}

export async function getUserProfile(): Promise<UserProfileRecord> {
  const response = await api.get<UserProfileEnvelope>("/api/user/profile");
  return normalizeProfile(response.data?.profile ?? null);
}

export async function updateUserProfile(
  body: UserProfileUpdateRequest
): Promise<UserProfileRecord> {
  const response = await api.patch<UserProfileEnvelope>(
    "/api/user/profile",
    normalizeUpdateRequest(body)
  );
  return normalizeProfile(response.data?.profile ?? null);
}
