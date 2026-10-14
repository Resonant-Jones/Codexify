import { useCallback } from "react";

import api, { getAuthToken, setAuthToken } from "@/lib/api";
import { useAuthState } from "@/lib/authState";

export type AuthCredentials = {
  username: string;
  password: string;
};

export function useAuth() {
  const authState = useAuthState();

  const login = useCallback(async (credentials: AuthCredentials, scoutAttempt?: string) => {
    const correlation = scoutAttempt && /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(scoutAttempt)
      ? { headers: { "X-Scout-Auth-Attempt": scoutAttempt } } : undefined;
    const response = correlation
      ? await api.post("/auth/login", credentials, correlation)
      : await api.post("/auth/login", credentials);
    const token = String(response?.data?.token ?? "").trim();
    if (!token) {
      throw new Error("Auth login did not return a session token");
    }
    setAuthToken(token);
    return response.data as {
      token: string;
      user_id: string;
      expires_at: number;
    };
  }, []);

  const logout = useCallback(async () => {
    const token = getAuthToken();
    try {
      if (token) {
        await api.post("/auth/logout");
      }
    } finally {
      setAuthToken(null);
    }
  }, []);

  return {
    ...authState,
    isAuthenticated: authState.status === "authenticated",
    login,
    logout,
  };
}
