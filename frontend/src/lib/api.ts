import axios from "axios";

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
  return readRuntimeEnv("VITE_GUARDIAN_DEV_API_KEY").trim();
}

function toHeaderRecord(headers?: HeadersInit): Record<string, string> {
  const normalized: Record<string, string> = {};
  if (!headers) return normalized;

  if (headers instanceof Headers) {
    headers.forEach((value, key) => {
      normalized[key] = value;
    });
    return normalized;
  }

  if (Array.isArray(headers)) {
    for (const [key, value] of headers) {
      normalized[key] = value;
    }
    return normalized;
  }

  return { ...headers };
}

function hasHeader(
  headers: Record<string, string>,
  key: string
): boolean {
  const target = key.toLowerCase();
  return Object.keys(headers).some((k) => k.toLowerCase() === target);
}

const AUTH_TOKEN_STORAGE_KEY = "guardian.auth.token";
let cachedAuthToken: string | null = null;
let loadedAuthToken = false;

function normalizeAuthToken(token: string | null | undefined): string | null {
  if (typeof token !== "string") return null;
  const trimmed = token.trim();
  return trimmed.length > 0 ? trimmed : null;
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

export function getAuthToken(): string | null {
  if (!loadedAuthToken) {
    cachedAuthToken = readStoredAuthToken();
    loadedAuthToken = true;
  }
  return cachedAuthToken;
}

export function setAuthToken(token: string | null): void {
  const normalized = normalizeAuthToken(token);
  cachedAuthToken = normalized;
  loadedAuthToken = true;

  if (typeof window === "undefined") return;
  try {
    if (normalized) {
      window.sessionStorage.setItem(AUTH_TOKEN_STORAGE_KEY, normalized);
    } else {
      window.sessionStorage.removeItem(AUTH_TOKEN_STORAGE_KEY);
    }
  } catch {
    // Ignore storage failures (private mode / SSR fallback).
  }
}

function applyAuthHeaders(headers: Record<string, string>): void {
  const token = getAuthToken();
  if (token && !hasHeader(headers, "Authorization")) {
    headers.Authorization = `Bearer ${token}`;
    return;
  }

  const devApiKey = resolveDevApiKey();
  if (!token && devApiKey && !hasHeader(headers, "X-API-Key")) {
    headers["X-API-Key"] = devApiKey;
  }
}

export function buildAuthenticatedFetchInit(
  init: RequestInit = {},
  options: { forceApiKey?: boolean } = {}
): RequestInit {
  void options;
  const headers = toHeaderRecord(init.headers);
  applyAuthHeaders(headers);

  return {
    ...init,
    ...(Object.keys(headers).length ? { headers } : {}),
    credentials: init.credentials ?? "include",
  };
}

function resolveTimeoutMs(): number {
  const candidates = [
    import.meta.env.VITE_HTTP_TIMEOUT_MS,
    import.meta.env.VITE_API_TIMEOUT_MS,
    import.meta.env.VITE_AXIOS_TIMEOUT_MS,
  ];
  for (const raw of candidates) {
    if (raw == null || raw === "") continue;
    const parsed = Number(raw);
    if (Number.isFinite(parsed) && parsed >= 0) {
      return parsed;
    }
  }
  return 15000;
}

const DEFAULT_TIMEOUT_MS = resolveTimeoutMs();

/**
 * Central Axios instance for the frontend.
 * Reads `VITE_API_BASE_URL` at build time; defaults to "/api".
 */
const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL ?? "/api",
  withCredentials: true,
  timeout: DEFAULT_TIMEOUT_MS,
});

api.interceptors.request.use((config) => {
  const headers = config.headers ?? {};
  const getHeader =
    typeof (headers as { get?: (key: string) => string | undefined }).get ===
    "function"
      ? (key: string) =>
          (headers as { get: (key: string) => string | undefined }).get(key)
      : undefined;
  const setHeader =
    typeof (headers as { set?: (key: string, value: string) => void }).set ===
    "function"
      ? (key: string, value: string) =>
          (headers as { set: (key: string, value: string) => void }).set(
            key,
            value
          )
      : (key: string, value: string) => {
          (headers as Record<string, string>)[key] = value;
        };

  const existingAuthorization =
    getHeader?.("Authorization") ??
    getHeader?.("authorization") ??
    (headers as Record<string, string | undefined>)["Authorization"] ??
    (headers as Record<string, string | undefined>)["authorization"];
  const existingApiKey =
    getHeader?.("X-API-Key") ??
    getHeader?.("x-api-key") ??
    (headers as Record<string, string | undefined>)["X-API-Key"] ??
    (headers as Record<string, string | undefined>)["x-api-key"];

  const token = getAuthToken();
  if (token && !existingAuthorization) {
    setHeader("Authorization", `Bearer ${token}`);
  } else if (!token) {
    const devApiKey = resolveDevApiKey();
    if (devApiKey && !existingAuthorization && !existingApiKey) {
      setHeader("X-API-Key", devApiKey);
    }
  }
  config.headers = headers;

  const baseURL = String(
    config.baseURL ?? api.defaults.baseURL ?? ""
  ).replace(/\/+$/, "");
  if (
    baseURL.endsWith("/api") &&
    typeof config.url === "string" &&
    config.url.startsWith("/api/")
  ) {
    config.url = config.url.replace(/^\/api/, "");
  }
  return config;
});

export default api;
