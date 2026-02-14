import api from "@/lib/api";
import type { SessionState } from "@/state/session/types";
import { SESSION_TTL_SECONDS } from "@/state/session/types";

export interface SessionStateStore {
  getSessionState(userId: string, deviceId: string): Promise<SessionState | null>;
  setSessionState(
    userId: string,
    deviceId: string,
    state: SessionState,
    ttlSeconds?: number
  ): Promise<void>;
  patchSessionState(
    userId: string,
    deviceId: string,
    patch: Partial<SessionState>,
    ttlSeconds?: number
  ): Promise<SessionState | null>;
  deleteSessionState(userId: string, deviceId: string): Promise<void>;
}

type SessionEnvelope = {
  ok?: boolean;
  state?: SessionState | null;
};

function coerceSessionState(value: unknown): SessionState | null {
  if (!value || typeof value !== "object") return null;
  const candidate = value as SessionState;
  if (!candidate.userId || !candidate.deviceId) return null;
  if (!Array.isArray(candidate.tabs) || !candidate.activeTabId) return null;
  if (typeof candidate.version !== "number") return null;
  if (typeof candidate.updatedAt !== "string") return null;
  return candidate;
}

function makeSessionKey(userId: string, deviceId: string): string {
  return `${userId}:${deviceId}`;
}

export class InMemorySessionStateStore implements SessionStateStore {
  private readonly map = new Map<string, SessionState>();

  async getSessionState(
    userId: string,
    deviceId: string
  ): Promise<SessionState | null> {
    const key = makeSessionKey(userId, deviceId);
    const state = this.map.get(key);
    return state ? structuredClone(state) : null;
  }

  async setSessionState(
    userId: string,
    deviceId: string,
    state: SessionState,
    _ttlSeconds = SESSION_TTL_SECONDS
  ): Promise<void> {
    const key = makeSessionKey(userId, deviceId);
    this.map.set(key, structuredClone(state));
  }

  async patchSessionState(
    userId: string,
    deviceId: string,
    patch: Partial<SessionState>,
    ttlSeconds = SESSION_TTL_SECONDS
  ): Promise<SessionState | null> {
    const existing = await this.getSessionState(userId, deviceId);
    if (!existing) return null;
    const merged = { ...existing, ...patch } as SessionState;
    await this.setSessionState(userId, deviceId, merged, ttlSeconds);
    return merged;
  }

  async deleteSessionState(userId: string, deviceId: string): Promise<void> {
    const key = makeSessionKey(userId, deviceId);
    this.map.delete(key);
  }
}

export class RedisSessionStateStore implements SessionStateStore {
  async getSessionState(
    userId: string,
    deviceId: string
  ): Promise<SessionState | null> {
    const response = await api.get<SessionEnvelope>("/ui/session", {
      params: {
        user_id: userId,
        device_id: deviceId,
      },
    });
    return coerceSessionState(response?.data?.state ?? null);
  }

  async setSessionState(
    userId: string,
    deviceId: string,
    state: SessionState,
    ttlSeconds = SESSION_TTL_SECONDS
  ): Promise<void> {
    await api.put("/ui/session", {
      user_id: userId,
      device_id: deviceId,
      state,
      ttl_seconds: ttlSeconds,
    });
  }

  async patchSessionState(
    userId: string,
    deviceId: string,
    patch: Partial<SessionState>,
    ttlSeconds = SESSION_TTL_SECONDS
  ): Promise<SessionState | null> {
    const response = await api.patch<SessionEnvelope>("/ui/session", {
      user_id: userId,
      device_id: deviceId,
      patch,
      ttl_seconds: ttlSeconds,
    });
    return coerceSessionState(response?.data?.state ?? null);
  }

  async deleteSessionState(userId: string, deviceId: string): Promise<void> {
    await api.delete("/ui/session", {
      params: {
        user_id: userId,
        device_id: deviceId,
      },
    });
  }
}
