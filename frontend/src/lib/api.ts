import axios from "axios";
import {
  markAuthUnauthenticatedFrom401,
  syncAuthStateFromCredentials,
} from "@/lib/authState";
import {
  getRuntimeConfigSync,
  resolveApiUrl,
} from "@/lib/runtimeConfig";
import type { SlashCommandIntentPayload } from "@/contracts/slashCommands";
import type { ThreadConfig } from "@/types/ui";
import {
  clearRuntimeApiKey as clearRuntimeApiKeyState,
  getRuntimeApiKey,
  setRuntimeApiKey as setRuntimeApiKeyState,
} from "@/lib/runtimeAuth";
import type {
  SlashCommandIntentPayload,
} from "@/contracts/slashCommands";

export type { SlashCommandIntentPayload };

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
const CHAT_COMPLETE_PATH_RE = /\/chat\/(\d+)\/complete$/i;
const UUID_V4ISH_RE =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;

let backendOutageUntil = 0;
let backendOutageFailures = 0;
let lastBackendOutageLogAt = 0;
let lastRequestGuardLogAt = 0;
const lastRequestByKey = new Map<string, number>();
const inFlightCompletionTurnByThread = new Map<number, string>();

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

export interface ChatCompletionRequest {
  depth_mode: string;
  provider?: string;
  model?: string;
  reasoning_mode?: string;
  source_mode?: string;
  slashIntent?: SlashCommandIntentPayload | null;
  slash_intent?: SlashCommandIntentPayload | null;
  [key: string]: unknown;
}

export type ChatCompletionRequestBody = ChatCompletionRequest;

export function buildLatestRagTracePath(threadId: string | number): string {
  return `/api/chat/debug/rag-trace/${normalizePathSegment(threadId)}/latest`;
}

export function buildLatestRetrievalPosturePath(threadId: string | number): string {
  return `/api/chat/debug/retrieval-posture/${normalizePathSegment(threadId)}/latest`;
}

export async function fetchLatestRetrievalPosture(
  threadId: number
): Promise<Record<string, unknown>> {
  const response = await api.get<Record<string, unknown>>(
    buildLatestRetrievalPosturePath(threadId)
  );
  return response.data;
}

export type ThreadConfigUpdate = {
  providerId?: string;
  modelId?: string;
  inferenceMode?: string;
  retrievalSource?: string;
  personaId?: string | null;
};

export type ThreadConfigUpdateResponse = {
  ok?: boolean;
  thread_id?: number;
  thread_config?: ThreadConfig;
  threadConfig?: ThreadConfig;
};

export type ThreadRecordResponse = {
  ok?: boolean;
  thread?: Record<string, unknown>;
};

export type ThreadMoveResponse = {
  ok?: boolean;
  thread?: Record<string, unknown>;
  move?: Record<string, unknown>;
};

export async function updateThreadConfig(
  threadId: string | number,
  patch: ThreadConfigUpdate
): Promise<ThreadConfigUpdateResponse> {
  const response = await api.patch(
    `/chat/threads/${normalizePathSegment(threadId)}/config`,
    patch
  );
  return response?.data ?? {};
}

export async function fetchChatThread(
  threadId: string | number
): Promise<ThreadRecordResponse> {
  const response = await api.get(
    `/chat/threads/${normalizePathSegment(threadId)}`
  );
  return response?.data ?? {};
}

export async function moveChatThread(
  threadId: string | number,
  toProjectId: string | number
): Promise<ThreadMoveResponse> {
  const response = await api.post(
    `/chat/threads/${normalizePathSegment(threadId)}/move`,
    { toProjectId }
  );
  return response?.data ?? {};
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

function extractTransportErrorSignal(error: any): string {
  const haystack = [
    error?.code,
    error?.message,
    error?.response?.statusText,
    errorBlob(error?.response?.data?.detail ?? error?.response?.data),
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

  const match = haystack.match(
    /(socket hang up|getaddrinfo enotfound|enotfound|econnrefused|network error|failed to fetch|proxy|upstream|connection refused|backend unavailable|backend outage fuse active)/i
  );
  return match?.[0] ?? "";
}

export function isBackendRuntimeUnavailableError(error: any): boolean {
  if (!error) return false;
  if (isBackendTransportError(error)) return true;
  if (isBackendProxyOutageResponse(error)) return true;
  return Boolean(extractTransportErrorSignal(error));
}

export function normalizeImportRuntimeError(
  error: any,
  options: { phase?: "preflight" | "upload" } = {}
): {
  isRuntimeUnavailable: boolean;
  message: string;
  technicalDetail?: string;
} {
  const phase = options.phase ?? "upload";
  const signal = extractTransportErrorSignal(error);

  if (isBackendRuntimeUnavailableError(error)) {
    const message =
      phase === "preflight"
        ? "ChatGPT import cannot start because the local backend runtime is unavailable. Restore the local stack and retry."
        : "ChatGPT import failed because the local backend runtime became unavailable during upload. Restore the local stack and retry.";
    return {
      isRuntimeUnavailable: true,
      message,
      technicalDetail: signal || undefined,
    };
  }

  const detail =
    error?.response?.data?.detail ??
    error?.response?.data?.error ??
    error?.message ??
    "Failed to migrate data";
  return {
    isRuntimeUnavailable: false,
    message: String(detail),
    technicalDetail: signal || undefined,
  };
}

function parseNonNegativeCount(value: unknown): number {
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return 0;
  return Math.max(0, Math.trunc(parsed));
}

export interface ChatGptImportStats {
  threads_imported: number;
  messages_imported: number;
  projects_created?: number;
  projects_reused?: number;
  messages_filtered?: number;
  embedding_candidates: number;
  embeddings_persisted: number;
  embeddings_failed: number;
  embedding_coverage_degraded: boolean;
}

export function normalizeChatGptImportStats(
  payload: any
): ChatGptImportStats {
  return {
    threads_imported: parseNonNegativeCount(payload?.threads_imported),
    messages_imported: parseNonNegativeCount(payload?.messages_imported),
    projects_created: parseNonNegativeCount(payload?.projects_created),
    projects_reused: parseNonNegativeCount(payload?.projects_reused),
    messages_filtered: parseNonNegativeCount(payload?.messages_filtered),
    embedding_candidates: parseNonNegativeCount(
      payload?.embedding_candidates
    ),
    embeddings_persisted: parseNonNegativeCount(
      payload?.embeddings_persisted
    ),
    embeddings_failed: parseNonNegativeCount(payload?.embeddings_failed),
    embedding_coverage_degraded: Boolean(
      payload?.embedding_coverage_degraded
    ),
  };
}

export async function preflightBackendAvailability(
  timeoutMs = 4000
): Promise<{
  ok: boolean;
  message?: string;
  technicalDetail?: string;
}> {
  try {
    // /api/health/llm is an existing lightweight route that still
    // exercises frontend->backend transport and proxy resolution.
    await api.get("/api/health/llm", { timeout: timeoutMs });
    return { ok: true };
  } catch (error: any) {
    if (error?.response) {
      // Non-transport HTTP failures still prove backend reachability.
      return { ok: true };
    }

    const normalized = normalizeImportRuntimeError(error, {
      phase: "preflight",
    });
    return {
      ok: false,
      message: normalized.message,
      technicalDetail: normalized.technicalDetail,
    };
  }
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

function normalizeCompletionTurnId(raw: unknown): string | null {
  if (typeof raw !== "string") return null;
  const trimmed = raw.trim();
  if (!trimmed) return null;
  return UUID_V4ISH_RE.test(trimmed) ? trimmed.toLowerCase() : null;
}

function generateCompletionTurnId(): string {
  const randomUUID = (globalThis as any)?.crypto?.randomUUID;
  if (typeof randomUUID === "function") {
    try {
      return String(randomUUID.call((globalThis as any).crypto));
    } catch {
      // Fall back below.
    }
  }
  const template = "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx";
  return template.replace(/[xy]/g, (char) => {
    const value = Math.floor(Math.random() * 16);
    const nibble = char === "x" ? value : (value & 0x3) | 0x8;
    return nibble.toString(16);
  });
}

function extractCompletionThreadId(url: unknown): number | null {
  const match = pathFromUrl(url).match(CHAT_COMPLETE_PATH_RE);
  if (!match || !match[1]) return null;
  const threadId = Number(match[1]);
  return Number.isFinite(threadId) ? threadId : null;
}

function readCompletionPayload(data: unknown): {
  payload: Record<string, unknown>;
  wasJsonString: boolean;
} {
  if (data && typeof data === "object" && !Array.isArray(data)) {
    return {
      payload: { ...(data as Record<string, unknown>) },
      wasJsonString: false,
    };
  }
  if (typeof data === "string" && data.trim()) {
    try {
      const parsed = JSON.parse(data);
      if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
        return {
          payload: { ...(parsed as Record<string, unknown>) },
          wasJsonString: true,
        };
      }
    } catch {
      // Ignore malformed payloads; we'll replace with an object below.
    }
  }
  return { payload: {}, wasJsonString: false };
}

function readCompletionMeta(config: unknown): {
  threadId: number;
  turnId: string | null;
} | null {
  const candidate = config as any;
  const threadId = Number(candidate?.__cfyCompletionThreadId);
  if (!Number.isFinite(threadId)) return null;
  return {
    threadId,
    turnId: normalizeCompletionTurnId(candidate?.__cfyCompletionTurnId),
  };
}

function completionErrorDetail(error: any): string {
  const detail = error?.response?.data?.detail;
  if (typeof detail === "string") return detail.toLowerCase();
  if (!detail || typeof detail !== "object") return "";
  return [
    detail?.error,
    detail?.reason,
    detail?.message,
    detail?.code,
  ]
    .filter(Boolean)
    .map((value) => String(value).toLowerCase())
    .join(" ");
}

export function getInFlightCompletionTurnId(
  threadId: number | null | undefined
): string | null {
  if (threadId == null) return null;
  const normalizedThreadId = Number(threadId);
  if (!Number.isFinite(normalizedThreadId)) return null;
  return inFlightCompletionTurnByThread.get(normalizedThreadId) ?? null;
}

export function clearInFlightCompletionTurnId(
  threadId: number | null | undefined,
  expectedTurnId?: string | null
): void {
  if (threadId == null) return;
  const normalizedThreadId = Number(threadId);
  if (!Number.isFinite(normalizedThreadId)) return;
  if (expectedTurnId) {
    const current = inFlightCompletionTurnByThread.get(normalizedThreadId);
    if (current !== expectedTurnId) return;
  }
  inFlightCompletionTurnByThread.delete(normalizedThreadId);
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
  // Chat-critical reads must never be dropped by client-side throttling.
  if (/\/chat\/\d+\/messages$/.test(path)) return 0;
  if (/\/chat\/\d+\/profile$/.test(path)) return 0;
  if (/\/chat\/threads$/.test(path)) return 0;
  if (/\/health\/llm$/.test(path)) return 0;
  // Catalog fetches can be intentionally triggered by menu open + refresh polling.
  if (/\/llm\/catalog$/.test(path)) return 0;
  if (/\/ui\/session$/.test(path)) return 0;
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

  const isPostCompletionRequest =
    String(config.method ?? "get").toLowerCase() === "post";
  const completionThreadId = isPostCompletionRequest
    ? extractCompletionThreadId(config.url)
    : null;
  if (completionThreadId != null) {
    const { payload, wasJsonString } = readCompletionPayload(config.data);
    const requestedTurnId = normalizeCompletionTurnId(payload.turn_id ?? payload.turnId);
    // Use per-request turn ids by default; do not carry stale ids between requests.
    const turnId = requestedTurnId || generateCompletionTurnId();
    payload.turn_id = turnId;
    config.data = wasJsonString ? JSON.stringify(payload) : payload;
    inFlightCompletionTurnByThread.set(completionThreadId, turnId);
    (config as any).__cfyCompletionThreadId = completionThreadId;
    (config as any).__cfyCompletionTurnId = turnId;
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
    const completionMeta = readCompletionMeta(response?.config);
    if (completionMeta) {
      const returnedTurnId = normalizeCompletionTurnId(response?.data?.turn_id);
      if (returnedTurnId) {
        inFlightCompletionTurnByThread.set(completionMeta.threadId, returnedTurnId);
      }
    }
    clearBackendOutage();
    return response;
  },
  (error) => {
    const completionMeta = readCompletionMeta(error?.config);
    if (completionMeta) {
      clearInFlightCompletionTurnId(
        completionMeta.threadId,
        completionMeta.turnId
      );
    }

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

(api as any).getInFlightCompletionTurnId = getInFlightCompletionTurnId;
(api as any).clearInFlightCompletionTurnId = clearInFlightCompletionTurnId;

export async function fetchLatestRagTrace(
  threadId: number
): Promise<Record<string, unknown>> {
  const response = await api.get<Record<string, unknown>>(
    buildLatestRagTracePath(threadId)
  );
  return response.data;
}

export type PersonalFactRecord = {
  id: number;
  user_id: string;
  key: string;
  value: string;
  status: string;
  confidence: number;
  is_active: boolean;
  last_confirmed_at: string | null;
  created_at: string | null;
  updated_at: string | null;
};

export type PersonalFactEvidenceRecord = {
  id: number;
  fact_id: number;
  source_message_id: number | null;
  excerpt: string | null;
  modality: string;
  confidence: number;
  source_type: string;
  evidence_meta: Record<string, unknown> | null;
  created_at: string | null;
};

export type PersonalFactRevisionRecord = {
  id: number;
  fact_id: number;
  actor: string;
  action: string;
  field_changed: string | null;
  old_value: string | null;
  new_value: string | null;
  reason: string | null;
  created_at: string | null;
};

type PersonalFactsListResponse = {
  ok?: boolean;
  facts?: PersonalFactRecord[];
};

type PersonalFactDetailResponse = {
  ok?: boolean;
  fact?: PersonalFactRecord | null;
  evidence?: PersonalFactEvidenceRecord[];
};

type PersonalFactEvidenceResponse = {
  ok?: boolean;
  evidence?: PersonalFactEvidenceRecord[];
};

type PersonalFactRevisionsResponse = {
  ok?: boolean;
  revisions?: PersonalFactRevisionRecord[];
};

type PersonalFactUpdateResponse = {
  ok?: boolean;
  fact?: PersonalFactRecord | null;
};

type PersonalFactUpdateBody = {
  confidence?: number;
  reason?: string;
  status?: string;
  value?: string;
};

const PERSONAL_FACTS_BASE_PATH = "/api/personal-facts";

function personalFactPath(factId: number | string): string {
  return `${PERSONAL_FACTS_BASE_PATH}/${normalizePathSegment(factId)}`;
}

function buildPersonalFactUpdateBody(
  body: PersonalFactUpdateBody
): PersonalFactUpdateBody {
  return {
    ...(body.value !== undefined ? { value: body.value } : {}),
    ...(body.status !== undefined ? { status: body.status } : {}),
    ...(body.confidence !== undefined ? { confidence: body.confidence } : {}),
    ...(body.reason !== undefined ? { reason: body.reason } : {}),
  };
}

export async function fetchPersonalFacts(params: {
  activeOnly?: boolean;
  limit?: number;
  status?: string | null;
} = {}): Promise<PersonalFactRecord[]> {
  const response = await api.get<PersonalFactsListResponse>(
    PERSONAL_FACTS_BASE_PATH,
    {
      params: {
        ...(params.status ? { status: params.status } : {}),
        active_only: params.activeOnly ?? true,
        ...(params.limit !== undefined ? { limit: params.limit } : {}),
      },
    }
  );
  return Array.isArray(response.data?.facts) ? response.data.facts : [];
}

export async function fetchPersonalFact(
  factId: number
): Promise<{ evidence: PersonalFactEvidenceRecord[]; fact: PersonalFactRecord | null }> {
  const response = await api.get<PersonalFactDetailResponse>(
    personalFactPath(factId)
  );
  return {
    fact: response.data?.fact ?? null,
    evidence: Array.isArray(response.data?.evidence)
      ? response.data.evidence
      : [],
  };
}

export async function updatePersonalFact(
  factId: number,
  body: PersonalFactUpdateBody
): Promise<PersonalFactRecord | null> {
  const response = await api.patch<PersonalFactUpdateResponse>(
    personalFactPath(factId),
    buildPersonalFactUpdateBody(body)
  );
  return response.data?.fact ?? null;
}

export async function archivePersonalFact(
  factId: number,
  reason?: string
): Promise<PersonalFactRecord | null> {
  return updatePersonalFact(factId, {
    reason,
    status: "archived",
  });
}

export async function confirmPersonalFact(
  factId: number,
  reason?: string
): Promise<PersonalFactRecord | null> {
  const response = await api.post<PersonalFactUpdateResponse>(
    `${personalFactPath(factId)}/confirm`,
    reason !== undefined ? { reason } : {}
  );
  return response.data?.fact ?? null;
}

export async function disputePersonalFact(
  factId: number,
  reason?: string
): Promise<PersonalFactRecord | null> {
  const response = await api.post<PersonalFactUpdateResponse>(
    `${personalFactPath(factId)}/dispute`,
    reason !== undefined ? { reason } : {}
  );
  return response.data?.fact ?? null;
}

export async function fetchPersonalFactEvidence(
  factId: number
): Promise<PersonalFactEvidenceRecord[]> {
  const response = await api.get<PersonalFactEvidenceResponse>(
    `${personalFactPath(factId)}/evidence`
  );
  return Array.isArray(response.data?.evidence) ? response.data.evidence : [];
}

export async function fetchPersonalFactRevisions(
  factId: number
): Promise<PersonalFactRevisionRecord[]> {
  const response = await api.get<PersonalFactRevisionsResponse>(
    `${personalFactPath(factId)}/revisions`
  );
  return Array.isArray(response.data?.revisions) ? response.data.revisions : [];
}

export default api;
