import api from "@/lib/api";

export type IdentitySettings = {
  memory_mode: "none" | "light" | "deep";
  diary_requires_unlock: boolean;
  allow_sensitive_modeling: boolean;
};

export async function fetchIdentitySettings(userId?: string): Promise<IdentitySettings> {
  const res = await api.get<IdentitySettings>("/api/iddb/settings", { params: { user_id: userId } });
  return res.data;
}

export async function saveIdentitySettings(settings: Partial<IdentitySettings> & { user_id?: string }) {
  const res = await api.post<IdentitySettings>("/api/iddb/settings", settings);
  return res.data;
}
