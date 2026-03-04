import axios from "axios";
import {
  markAuthUnauthenticatedFrom401,
  syncAuthStateFromCredentials,
} from "@/lib/authState";
import {
  getRuntimeConfigSync,
  resolveApiUrl,
} from "@/lib/runtimeConfig";
import {
  clearRuntimeApiKey as clearRuntimeApiKeyState,
  getRuntimeApiKey,
  setRuntimeApiKey as setRuntimeApiKeyState,
} from "@/lib/runtimeAuth";

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
  // Backward-compat: existing local setups may still use VITE_GUARDIAN_API_KEY.
  return readRuntimeEnv("VITE_GUARDIAN_API_KEY").trim();
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

export function getDevApiKey(): string {
  return resolveDevApiKey();
}

export function setRuntimeApiKey(apiKey: string | null): void {
  setRuntimeApiKeyState(apiKey);
  syncAuthStateFromCredentials();
}

export function clearRuntimeApiKey(): void {
  clearRuntimeApiKeyState();
  syncAuthStateFromCredentials();
}

export function readRuntimeApiKey(): string | null {
  return getRuntimeApiKey();
}

function applyAuthToken(
  normalized: string | null,
  options: { syncAuthState?: boolean } = {}
): void {
  const syncAuthState = options.syncAuthState ?? true;
  cachedAuthToken = normalized;
  loadedAuthToken = true;

  if (typeof window !== "undefined") {
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

  if (syncAuthState) {
    // Keep auth gate state synchronized with credential changes.
    syncAuthStateFromCredentials();
  }
}

export function setAuthToken(token: string | null): void {
  const normalized = normalizeAuthToken(token);
  applyAuthToken(normalized, { syncAuthState: true });
}

function clearAuthTokenAfterUnauthorized(): void {
  applyAuthToken(null, { syncAuthState: false });
}

function applyAuthHeaders(
  headers: Record<string, string>,
  options: { forceApiKey?: boolean } = {}
): void {
  const forceApiKey = options.forceApiKey ?? false;
  const token = getAuthToken();
  const runtimeApiKey = getRuntimeApiKey();
  const devApiKey = resolveDevApiKey();
  const apiKey = runtimeApiKey || devApiKey;
  const hasAuthorization = hasHeader(headers, "Authorization");
  const hasApiKey = hasHeader(headers, "X-API-Key");

  if (!forceApiKey && token && !hasAuthorization) {
    headers.Authorization = `Bearer ${token}`;
    return;
  }

  if (apiKey && !hasApiKey) {
    headers["X-API-Key"] = apiKey;
    return;
  }

  if (token && !hasAuthorization) {
    headers.Authorization = `Bearer ${token}`;
  }
}

export function buildAuthenticatedFetchInit(
  init: RequestInit = {},
  options: { forceApiKey?: boolean } = {}
): RequestInit {
  const headers = toHeaderRecord(init.headers);
  applyAuthHeaders(headers, options);

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
const BACKEND_OUTAGE_BASE_MS = 1000;
const BACKEND_OUTAGE_MAX_MS = 30000;
const BACKEND_OUTAGE_LOG_TTL_MS = 5000;
const REQUEST_GUARD_LOG_TTL_MS = 4000;

let backendOutageUntil = 0;
let backendOutageFailures = 0;
let lastBackendOutageLogAt = 0;
let lastRequestGuardLogAt = 0;
const lastRequestByKey = new Map<string, number>();

function normalizePathSegment(value: string | number): string {
  return encodeURIComponent(String(value).trim());
}

export function buildThreadDocumentsPath(threadId: string | number): string {
  return `/documents/threads/${normalizePathSegment(threadId)}/documents`;
}

export function buildLlmCatalogPath(): string {
  return "/llm/catalog";
}

export function buildChatCompletePath(threadId: string | number): string {
  return `/chat/${normalizePathSegment(threadId)}/complete`;
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function isBackendTransportError(error: any): boolean {
  if (!error) return false;
  if (error?.code === "ERR_BACKEND_OUTAGE_FUSE") return false;
  if (error?.code === "ERR_CLIENT_RATE_GUARD") return false;
  if (error?.response) return false;
  if (error?.code === "ERR_CANCELED") return false;
  return true;
}

function errorBlob(value: unknown): string {
  if (!value) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  if (Array.isArray(value)) {
    return value.map((entry) => errorBlob(entry)).join(" ");
  }
  if (typeof value === "object") {
    try {
      return JSON.stringify(value);
    } catch {
      return String(value);
    }
  }
  return "";
}

function isBackendProxyOutageResponse(error: any): boolean {
  const status = Number(error?.response?.status ?? 0);
  if (!Number.isFinite(status)) return false;
  if (status < 500 || status > 504) return false;
  if (!shouldApplyBackendOutageFuse(error?.config?.url)) return false;

  if (status >= 502) return true;

  const haystack = [
    error?.message,
    error?.response?.statusText,
    errorBlob(error?.response?.data?.detail ?? error?.response?.data),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  return /econnrefused|enotfound|proxy|upstream|connection refused|socket hang up|backend/.test(
    haystack
  );
}

function computeBackendOutageDelayMs(failures: number): number {
  const exp = Math.max(0, failures - 1);
  return Math.min(
    BACKEND_OUTAGE_MAX_MS,
    BACKEND_OUTAGE_BASE_MS * Math.pow(2, exp)
  );
}

function shouldApplyBackendOutageFuse(url: unknown): boolean {
  if (typeof url !== "string") return true;
  return !/\/assets\/|\.hot-update/i.test(url);
}

function applyBackendOutage(reason: string): void {
  backendOutageFailures += 1;
  const delayMs = computeBackendOutageDelayMs(backendOutageFailures);
  backendOutageUntil = Date.now() + delayMs;
  const now = Date.now();
  if (now - lastBackendOutageLogAt >= BACKEND_OUTAGE_LOG_TTL_MS) {
    lastBackendOutageLogAt = now;
    console.warn(
      `[api] backend unavailable (${reason}); throttling requests for ${delayMs}ms`
    );
  }
}

function clearBackendOutage(): void {
  backendOutageFailures = 0;
  backendOutageUntil = 0;
}

export function getBackendOutageRemainingMs(now = Date.now()): number {
  return Math.max(0, backendOutageUntil - now);
}

export function isBackendOutageActive(now = Date.now()): boolean {
  return getBackendOutageRemainingMs(now) > 0;
}

function pathFromUrl(value: unknown): string {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  if (!trimmed) return "";
  try {
    const parsed = isAbsoluteUrl(trimmed)
      ? new URL(trimmed)
      : new URL(trimmed, "http://localhost");
    return parsed.pathname.toLowerCase();
  } catch {
    return trimmed.split("?")[0]?.toLowerCase() ?? "";
  }
}

function requestGuardWindowMs(
  method: unknown,
  url: unknown
): number {
  const normalizedMethod = String(method ?? "get").toLowerCase();
  if (normalizedMethod !== "get") return 0;
  const path = pathFromUrl(url);
  if (!path) return 0;
  if (/\/api\/events$|\/events$/.test(path)) return 4000;
  // Allow normal polling, but still damp accidental duplicate bursts.
  if (/\/chat\/\d+\/messages$/.test(path)) return 500;
  if (/\/chat\/\d+\/profile$/.test(path)) return 5000;
  if (/\/health\/llm$/.test(path)) return 5000;
  // Catalog fetches can be intentionally triggered by menu open + refresh polling.
  if (/\/llm\/catalog$/.test(path)) return 0;
  if (/\/ui\/session$/.test(path)) return 10000;
  // Project cache and shell hydration may issue close-in-time reads.
  if (/\/projects$/.test(path) || /\/api\/projects$/.test(path)) return 0;
  return 0;
}

function shouldThrottleDuplicateRequest(
  method: unknown,
  url: unknown
): { throttled: boolean; waitMs: number; key: string } {
  const windowMs = requestGuardWindowMs(method, url);
  if (windowMs <= 0) {
    return { throttled: false, waitMs: 0, key: "" };
  }
  const key = `${String(method ?? "get").toLowerCase()}:${pathFromUrl(url)}`;
  const now = Date.now();
  const previous = lastRequestByKey.get(key) ?? 0;
  const delta = now - previous;
  if (delta < windowMs) {
    return { throttled: true, waitMs: windowMs - delta, key };
  }
  lastRequestByKey.set(key, now);
  return { throttled: false, waitMs: 0, key };
}

function isRequestGuardEnabled(): boolean {
  const raw = readRuntimeEnv("VITE_ENABLE_REQUEST_GUARD", "true")
    .trim()
    .toLowerCase();
  if (!raw) return true;
  return !["0", "false", "off", "no"].includes(raw);
}

export function refreshApiBaseUrl(): string {
  const runtimeConfig = getRuntimeConfigSync();
  api.defaults.baseURL = runtimeConfig.apiBaseUrl;
  return runtimeConfig.apiBaseUrl;
}

/**
 * Central Axios instance for the frontend.
 * Reads `VITE_API_BASE_URL` at build time; defaults to "/api".
 */
const api = axios.create({
  baseURL: getRuntimeConfigSync().apiBaseUrl,
  withCredentials: true,
  timeout: DEFAULT_TIMEOUT_MS,
});

api.interceptors.request.use((config) => {
  const now = Date.now();
  if (
    shouldApplyBackendOutageFuse(config.url) &&
    backendOutageUntil > now
  ) {
    const waitMs = backendOutageUntil - now;
    const fuseError = Object.assign(
      new Error(`backend outage fuse active (${waitMs}ms)`),
      { code: "ERR_BACKEND_OUTAGE_FUSE", waitMs }
    );
    return Promise.reject(fuseError);
  }

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
  const runtimeApiKey = getRuntimeApiKey();
  if (token && !existingAuthorization) {
    setHeader("Authorization", `Bearer ${token}`);
  } else if (!token) {
    if (runtimeApiKey && !existingAuthorization && !existingApiKey) {
      setHeader("X-API-Key", runtimeApiKey);
    } else {
      const devApiKey = resolveDevApiKey();
      if (devApiKey && !existingAuthorization && !existingApiKey) {
        setHeader("X-API-Key", devApiKey);
      }
    }
  } else if (runtimeApiKey && !existingApiKey) {
    setHeader("X-API-Key", runtimeApiKey);
  }
  config.headers = headers;

  const runtimeConfig = getRuntimeConfigSync();
  if (runtimeConfig.mode === "tauri" && runtimeConfig.apiBaseUrl) {
    config.baseURL = runtimeConfig.apiBaseUrl;
  }

  if (typeof config.url === "string" && !isAbsoluteUrl(config.url)) {
    const resolvedUrl = resolveApiUrl(config.url, runtimeConfig);
    if (isAbsoluteUrl(resolvedUrl)) {
      config.baseURL = undefined;
      config.url = resolvedUrl;
    } else {
      config.url = resolvedUrl;
    }
  }

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

  const guard = isRequestGuardEnabled()
    ? shouldThrottleDuplicateRequest(config.method, config.url)
    : { throttled: false, waitMs: 0, key: "" };
  if (guard.throttled) {
    const now = Date.now();
    if (now - lastRequestGuardLogAt >= REQUEST_GUARD_LOG_TTL_MS) {
      lastRequestGuardLogAt = now;
      console.warn(
        `[api] request guard throttled ${guard.key} for ${guard.waitMs}ms`
      );
    }
    const guardError = Object.assign(
      new Error(`request guard active (${guard.waitMs}ms)`),
      { code: "ERR_CLIENT_RATE_GUARD", waitMs: guard.waitMs }
    );
    return Promise.reject(guardError);
  }
  return config;
});

api.interceptors.response.use(
  (response) => {
    clearBackendOutage();
    return response;
  },
  (error) => {
    if (isBackendTransportError(error)) {
      applyBackendOutage("transport");
    } else if (isBackendProxyOutageResponse(error)) {
      applyBackendOutage(`proxy:${Number(error?.response?.status ?? 0)}`);
    } else if (error?.response) {
      // Any server response (even 4xx/5xx) means transport path is reachable.
      clearBackendOutage();
    }

    if (error?.response?.status === 401) {
      clearAuthTokenAfterUnauthorized();
      markAuthUnauthenticatedFrom401();
    }
    return Promise.reject(error);
  }
);

export default api;
