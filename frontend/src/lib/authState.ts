import { useSyncExternalStore } from "react";

export type AuthStatus = "unknown" | "authenticated" | "unauthenticated";

export type AuthState = {
  status: AuthStatus;
  ready: boolean;
  token?: string;
};

const AUTH_TOKEN_STORAGE_KEY = "guardian.auth.token";

let authState: AuthState = { status: "unknown", ready: false };
const listeners = new Set<() => void>();
const gateSkipLogKeys = new Set<string>();
let loggedFirstUnauthorized = false;

function emit(): void {
  for (const listener of listeners) {
    listener();
  }
}

function normalizeAuthToken(token: string | null | undefined): string | null {
  if (typeof token !== "string") return null;
  const trimmed = token.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function readRuntimeEnv(name: string, fallback = ""): string {
  const viteEnv =
    typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const nodeEnv =
    typeof process !== "undefined" ? ((process as any).env ?? {}) : {};
  const raw = viteEnv[name] ?? nodeEnv[name] ?? fallback;
  return String(raw ?? "");
}

function isDevRuntime(): boolean {
  const viteEnv =
    typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  if (typeof viteEnv.DEV === "boolean") return viteEnv.DEV;
  const raw = readRuntimeEnv("NODE_ENV", "development").trim().toLowerCase();
  return raw !== "production";
}

function resolveDevApiKey(): string {
  if (!isDevRuntime()) return "";
  const explicitDevKey = readRuntimeEnv("VITE_GUARDIAN_DEV_API_KEY").trim();
  if (explicitDevKey) return explicitDevKey;
  return readRuntimeEnv("VITE_GUARDIAN_API_KEY").trim();
}

function readStoredAuthToken(): string | null {
  if (typeof window === "undefined") return null;
  try {
    return normalizeAuthToken(
      window.sessionStorage.getItem(AUTH_TOKEN_STORAGE_KEY)
    );
  } catch {
    return null;
  }
}

function deriveAuthState(): AuthState {
  const token = readStoredAuthToken();
  const devApiKey = resolveDevApiKey();
  if (token || devApiKey) {
    return {
      status: "authenticated",
      ready: true,
      token: token ?? undefined,
    };
  }
  return { status: "unauthenticated", ready: true };
}

function sameAuthState(a: AuthState, b: AuthState): boolean {
  return (
    a.status === b.status &&
    a.ready === b.ready &&
    (a.token ?? null) === (b.token ?? null)
  );
}

function setAuthState(next: AuthState): void {
  const normalized: AuthState = {
    status: next.status,
    ready: Boolean(next.ready),
    token: normalizeAuthToken(next.token) ?? undefined,
  };
  if (sameAuthState(authState, normalized)) return;
  authState = normalized;
  emit();
}

function logGateSkipOnce(scope: string, reason: string): void {
  const key = `${scope}:${reason}`;
  if (gateSkipLogKeys.has(key)) return;
  gateSkipLogKeys.add(key);
  console.debug(`[auth-gate] skipped ${scope} (${reason})`);
}

export function getAuthState(): AuthState {
  return authState;
}

export function subscribeAuthState(listener: () => void): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

export function useAuthState(): AuthState {
  return useSyncExternalStore(subscribeAuthState, getAuthState, getAuthState);
}

export function resolveAuthStateOnBoot(): AuthState {
  const next = deriveAuthState();
  setAuthState(next);
  return next;
}

export function syncAuthStateFromCredentials(): AuthState {
  const next = deriveAuthState();
  setAuthState(next);
  return next;
}

export function markAuthUnauthenticatedFrom401(): void {
  const current = getAuthState();
  if (current.ready && current.status === "unauthenticated") return;
  if (typeof window !== "undefined") {
    try {
      window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    } catch {
      // ignore storage failures
    }
  }
  setAuthState({ status: "unauthenticated", ready: true });
  if (!loggedFirstUnauthorized) {
    loggedFirstUnauthorized = true;
    console.info("[auth] received 401; transitioned to unauthenticated state");
  }
}

export function checkAuthGate(
  state: AuthState,
  scope: string,
  options: { requireAuthenticated?: boolean } = {}
): boolean {
  const requireAuthenticated = options.requireAuthenticated ?? true;
  if (!state.ready) {
    logGateSkipOnce(scope, "auth not ready");
    return false;
  }
  if (requireAuthenticated && state.status !== "authenticated") {
    logGateSkipOnce(scope, "unauthenticated");
    return false;
  }
  return true;
}

export function requireAuthReady(
  scope: string,
  options: { requireAuthenticated?: boolean } = {}
): boolean {
  return checkAuthGate(getAuthState(), scope, options);
}

export function __resetAuthStateForTests(): void {
  authState = { status: "unknown", ready: false };
  gateSkipLogKeys.clear();
  loggedFirstUnauthorized = false;
  emit();
}

export function __setAuthStateForTests(next: AuthState): void {
  setAuthState(next);
}
