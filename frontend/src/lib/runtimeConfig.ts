import { combineBaseAndPath } from "@/lib/urlJoin";

export type RuntimeMode = "web" | "tauri";
export type AuthMode = "local" | "remote";

export interface RuntimeConfig {
  mode: RuntimeMode;
  backendBaseUrl: string;
  apiBaseUrl: string;
  sseUrl: string;
  sharePublicBaseUrl: string;
  authMode: AuthMode;
}

type TauriRuntimeConfig = Partial<RuntimeConfig>;

export type LauncherStartupHandoff = {
  shouldRunWizard: boolean;
  setupComplete: boolean;
  runtimeProfile: string;
  envPath: string | null;
  handoffTarget: string | null;
  detail: string;
};

export type DesktopStartupRoutingDecision = {
  shouldRunWizard: boolean;
  setupComplete: boolean;
  handoffTarget: string | null;
  detail: string;
};

const DESKTOP_BACKEND_STORAGE_KEY = "cfy.desktop.backendBaseUrl";
const DESKTOP_SHARE_STORAGE_KEY = "cfy.desktop.sharePublicBaseUrl";

let runtimeConfigCache: RuntimeConfig | null = null;
let runtimeConfigPromise: Promise<RuntimeConfig> | null = null;

type TauriCoreApi = {
  invoke: <T = unknown>(
    command: string,
    payload?: Record<string, unknown>
  ) => Promise<T>;
};

function readRuntimeEnv(name: string, fallback = ""): string {
  const viteEnv =
    typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const nodeEnv =
    typeof process !== "undefined" ? ((process as any).env ?? {}) : {};
  const raw = viteEnv[name] ?? nodeEnv[name] ?? fallback;
  return String(raw ?? "").trim();
}

function isAbsoluteUrl(value: string): boolean {
  return /^https?:\/\//i.test(value);
}

function normalizeBase(value: string, fallback: string): string {
  const trimmed = value.trim();
  if (!trimmed) return fallback;
  return trimmed.replace(/\/+$/, "");
}

function appendPath(base: string, path: string): string {
  const trimmedBase = base.replace(/\/+$/, "");
  const trimmedPath = path.replace(/^\/+/, "");
  if (!trimmedBase) return `/${trimmedPath}`;
  if (!trimmedPath) return trimmedBase;
  return `${trimmedBase}/${trimmedPath}`;
}

function coerceAuthMode(value: string): AuthMode {
  return value.trim().toLowerCase() === "remote" ? "remote" : "local";
}

function normalizeNullableText(value: unknown): string | null {
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function normalizeRuntimeProfile(value: unknown): string {
  return normalizeNullableText(value) ?? "unknown";
}

function normalizeLauncherHandoffTarget(value: unknown): string | null {
  const normalized = normalizeNullableText(value);
  if (!normalized) return null;
  return isAbsoluteUrl(normalized) ? normalized.replace(/\/+$/, "") : null;
}

export function isTauriRuntime(): boolean {
  if (typeof window === "undefined") return false;
  return (
    typeof (window as any).__TAURI_IPC__ !== "undefined" ||
    typeof (window as any).__TAURI_INTERNALS__ !== "undefined"
  );
}

function readInjectedTauriCore(): TauriCoreApi | null {
  if (typeof window === "undefined") return null;
  const candidate = (window as any).__CFY_TAURI_CORE__;
  if (!candidate || typeof candidate.invoke !== "function") return null;
  return candidate as TauriCoreApi;
}

async function loadTauriCore(): Promise<TauriCoreApi> {
  const injected = readInjectedTauriCore();
  if (injected) return injected;
  const imported = (await new Function(
    'return import("@tauri-apps/api/core")'
  )()) as TauriCoreApi;
  return imported;
}

function normalizeLauncherStartupHandoff(
  payload: unknown
): LauncherStartupHandoff | null {
  if (!payload || typeof payload !== "object") {
    return null;
  }

  const source = payload as Record<string, unknown>;
  const setupComplete = asBoolean(source.setupComplete);
  const handoffTarget = normalizeLauncherHandoffTarget(source.handoffTarget);
  const shouldRunWizard =
    asBoolean(source.shouldRunWizard) || !setupComplete || !handoffTarget;
  const detail = normalizeNullableText(source.detail);

  return {
    shouldRunWizard,
    setupComplete,
    runtimeProfile: normalizeRuntimeProfile(source.runtimeProfile),
    envPath: normalizeNullableText(source.envPath),
    handoffTarget,
    detail:
      detail ??
      (shouldRunWizard
        ? "launcher startup state favors wizard/recovery"
        : "launcher startup state resolved"),
  };
}

export async function readDesktopLauncherStartupHandoff(): Promise<LauncherStartupHandoff | null> {
  if (!isTauriRuntime()) return null;
  try {
    const core = await loadTauriCore();
    const payload = await core.invoke<unknown>(
      "desktop_get_launcher_startup_handoff"
    );
    return normalizeLauncherStartupHandoff(payload);
  } catch {
    return null;
  }
}

export async function readDesktopStartupRoutingDecision(): Promise<DesktopStartupRoutingDecision | null> {
  const handoff = await readDesktopLauncherStartupHandoff();
  if (!handoff) return null;

  return {
    shouldRunWizard: handoff.shouldRunWizard,
    setupComplete: handoff.setupComplete,
    handoffTarget: handoff.handoffTarget,
    detail:
      normalizeNullableText(handoff.detail) ??
      "desktop launcher startup routing resolved",
  };
}

function readDesktopStorage(key: string): string {
  if (typeof window === "undefined") return "";
  try {
    return String(window.localStorage.getItem(key) ?? "").trim();
  } catch {
    return "";
  }
}

function writeDesktopStorage(key: string, value: string | null): void {
  if (typeof window === "undefined") return;
  try {
    if (value && value.trim()) {
      window.localStorage.setItem(key, value.trim());
    } else {
      window.localStorage.removeItem(key);
    }
  } catch {
    // Ignore write failures for private mode or locked storage contexts.
  }
}

function defaultMode(): RuntimeMode {
  return isTauriRuntime() ? "tauri" : "web";
}

function defaultBackendBaseUrl(mode: RuntimeMode): string {
  const envBackend = readRuntimeEnv("VITE_GUARDIAN_API_BASE") || readRuntimeEnv("GUARDIAN_API_BASE");
  if (isAbsoluteUrl(envBackend)) {
    return normalizeBase(envBackend, "http://127.0.0.1:8888");
  }
  if (mode === "tauri") {
    return "http://127.0.0.1:8888";
  }
  return envBackend || "";
}

function resolveDesktopBackendBaseUrl(
  mode: RuntimeMode,
  tauriConfig: TauriRuntimeConfig | null,
  launcherStartup: LauncherStartupHandoff | null
): string {
  const launcherTarget = launcherStartup?.handoffTarget ?? null;
  if (mode === "tauri" && launcherTarget) {
    return normalizeBase(launcherTarget, "");
  }

  const desktopBackendOverride =
    mode === "tauri" ? readDesktopStorage(DESKTOP_BACKEND_STORAGE_KEY) : "";
  if (desktopBackendOverride) {
    return normalizeBase(desktopBackendOverride, "");
  }

  const tauriBackend = tauriConfig?.backendBaseUrl?.trim() || "";
  if (tauriBackend) {
    return normalizeBase(tauriBackend, mode === "tauri" ? "" : defaultBackendBaseUrl(mode));
  }

  return mode === "tauri" ? "" : defaultBackendBaseUrl(mode);
}

function resolveApiBaseUrl(mode: RuntimeMode, backendBaseUrl: string, explicit: string): string {
  const candidate = explicit.trim();
  if (isAbsoluteUrl(candidate)) {
    return normalizeBase(candidate, combineBaseAndPath(backendBaseUrl, "/api"));
  }
  if (candidate.startsWith("/")) {
    return normalizeBase(candidate, "/api");
  }
  if (candidate) {
    return normalizeBase(`/${candidate}`, "/api");
  }
  if (mode === "tauri" && !backendBaseUrl) {
    return "/api";
  }
  if (mode === "tauri") {
    return normalizeBase(combineBaseAndPath(backendBaseUrl, "/api"), "http://127.0.0.1:8888/api");
  }
  return "/api";
}

function resolveSseUrl(mode: RuntimeMode, backendBaseUrl: string, apiBaseUrl: string, explicit: string): string {
  const candidate = explicit.trim();
  if (isAbsoluteUrl(candidate)) {
    return normalizeBase(candidate, combineBaseAndPath(apiBaseUrl, "/events"));
  }
  if (candidate.startsWith("/")) {
    if (mode === "tauri") {
      return normalizeBase(combineBaseAndPath(backendBaseUrl, candidate), combineBaseAndPath(apiBaseUrl, "/events"));
    }
    return normalizeBase(candidate, "/api/events");
  }
  if (candidate) {
    const normalized = candidate.startsWith("/") ? candidate : `/${candidate}`;
    if (mode === "tauri") {
      return normalizeBase(combineBaseAndPath(backendBaseUrl, normalized), combineBaseAndPath(apiBaseUrl, "/events"));
    }
    return normalizeBase(normalized, "/api/events");
  }
  return normalizeBase(appendPath(apiBaseUrl, "events"), "/api/events");
}

function defaultSharePublicBaseUrl(mode: RuntimeMode): string {
  const envShare = readRuntimeEnv("VITE_SHARE_PUBLIC_BASE_URL");
  if (isAbsoluteUrl(envShare)) {
    return normalizeBase(envShare, "http://127.0.0.1:5173");
  }
  if (mode === "tauri") {
    return "http://127.0.0.1:5173";
  }
  if (typeof window !== "undefined" && window.location?.origin) {
    return normalizeBase(window.location.origin, "");
  }
  return "";
}

async function readTauriRuntimeConfig(): Promise<TauriRuntimeConfig | null> {
  if (!isTauriRuntime()) return null;
  try {
    const core = await loadTauriCore();
    const payload = await core.invoke<any>("desktop_get_runtime_config");
    if (!payload || typeof payload !== "object") return null;
    return {
      mode: "tauri",
      backendBaseUrl: String(payload.backendBaseUrl ?? "").trim(),
      apiBaseUrl: String(payload.apiBaseUrl ?? "").trim(),
      sseUrl: String(payload.sseUrl ?? "").trim(),
      sharePublicBaseUrl: String(payload.sharePublicBaseUrl ?? "").trim(),
      authMode: String(payload.authMode ?? "").trim().toLowerCase() === "remote" ? "remote" : "local",
    };
  } catch {
    return null;
  }
}

function buildRuntimeConfig(
  mode: RuntimeMode,
  tauriConfig: TauriRuntimeConfig | null,
  launcherStartup: LauncherStartupHandoff | null
): RuntimeConfig {
  const desktopBackendOverride = mode === "tauri" ? readDesktopStorage(DESKTOP_BACKEND_STORAGE_KEY) : "";
  const desktopShareOverride = mode === "tauri" ? readDesktopStorage(DESKTOP_SHARE_STORAGE_KEY) : "";

  const backendBaseUrl = resolveDesktopBackendBaseUrl(mode, tauriConfig, launcherStartup);

  // If a desktop backend override is present, derive API/SSE from it unless explicitly overridden in env.
  const explicitApiBase =
    launcherStartup?.handoffTarget || desktopBackendOverride
      ? readRuntimeEnv("VITE_API_BASE_URL")
      : tauriConfig?.apiBaseUrl || readRuntimeEnv("VITE_API_BASE_URL") || readRuntimeEnv("VITE_API_BASE");

  const apiBaseUrl = resolveApiBaseUrl(mode, backendBaseUrl, explicitApiBase || "");

  const explicitSse =
    launcherStartup?.handoffTarget || desktopBackendOverride
      ? readRuntimeEnv("VITE_SSE_PATH")
      : tauriConfig?.sseUrl || readRuntimeEnv("VITE_SSE_PATH");

  const sseUrl = resolveSseUrl(mode, backendBaseUrl, apiBaseUrl, explicitSse || "");

  const sharePublicBaseUrl = normalizeBase(
    desktopShareOverride || tauriConfig?.sharePublicBaseUrl || defaultSharePublicBaseUrl(mode),
    mode === "tauri" ? "http://127.0.0.1:5173" : ""
  );

  const authMode = coerceAuthMode(
    tauriConfig?.authMode || readRuntimeEnv("GUARDIAN_AUTH_MODE", "local")
  );

  return {
    mode,
    backendBaseUrl,
    apiBaseUrl,
    sseUrl,
    sharePublicBaseUrl,
    authMode,
  };
}

function buildSyncRuntimeConfig(): RuntimeConfig {
  return buildRuntimeConfig(defaultMode(), null, null);
}

export function getRuntimeConfigSync(): RuntimeConfig {
  return runtimeConfigCache ?? buildSyncRuntimeConfig();
}

export async function initRuntimeConfig(options: { force?: boolean } = {}): Promise<RuntimeConfig> {
  const force = options.force ?? false;
  if (!force && runtimeConfigCache) {
    return runtimeConfigCache;
  }
  if (!force && runtimeConfigPromise) {
    return runtimeConfigPromise;
  }

  const mode = defaultMode();
  runtimeConfigPromise = (async () => {
    const [launcherStartup, tauriConfig] = await Promise.all([
      readDesktopLauncherStartupHandoff(),
      readTauriRuntimeConfig(),
    ]);
    const config = buildRuntimeConfig(mode, tauriConfig, launcherStartup);
    runtimeConfigCache = config;
    runtimeConfigPromise = null;
    return config;
  })();

  return runtimeConfigPromise;
}

function isApiBaseSuffix(base: string): boolean {
  const normalized = base.toLowerCase().replace(/\/+$/, "");
  return normalized.endsWith("/api");
}

export function resolveApiUrl(path: string, config: RuntimeConfig = getRuntimeConfigSync()): string {
  if (isAbsoluteUrl(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;

  if (
    !isAbsoluteUrl(config.apiBaseUrl) &&
    config.apiBaseUrl === "/api" &&
    normalizedPath.startsWith("/api/")
  ) {
    return normalizedPath;
  }

  if (isAbsoluteUrl(config.apiBaseUrl) && isApiBaseSuffix(config.apiBaseUrl)) {
    const pathSegment = normalizedPath.startsWith("/api/")
      ? normalizedPath.replace(/^\/api\//, "")
      : normalizedPath.replace(/^\/+/, "");
    return appendPath(config.apiBaseUrl, pathSegment);
  }

  if (!isAbsoluteUrl(config.apiBaseUrl) && config.apiBaseUrl === "/api") {
    const pathSegment = normalizedPath.startsWith("/api/")
      ? normalizedPath.replace(/^\/api\//, "")
      : normalizedPath.replace(/^\/+/, "");
    return appendPath(config.apiBaseUrl, pathSegment);
  }

  return combineBaseAndPath(config.apiBaseUrl, normalizedPath);
}

export function resolveBackendUrl(path: string, config: RuntimeConfig = getRuntimeConfigSync()): string {
  if (isAbsoluteUrl(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return combineBaseAndPath(config.backendBaseUrl, normalizedPath);
}

export function resolveSseEndpoint(config: RuntimeConfig = getRuntimeConfigSync()): string {
  return config.sseUrl;
}

export function resolveSharePublicUrl(path: string, config: RuntimeConfig = getRuntimeConfigSync()): string {
  if (isAbsoluteUrl(path)) return path;
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  return combineBaseAndPath(config.sharePublicBaseUrl, normalizedPath);
}

export function getDesktopConnectionSettings(): {
  backendBaseUrl: string;
  sharePublicBaseUrl: string;
} {
  const config = getRuntimeConfigSync();
  return {
    backendBaseUrl: config.backendBaseUrl,
    sharePublicBaseUrl: config.sharePublicBaseUrl,
  };
}

export async function saveDesktopConnectionSettings(settings: {
  backendBaseUrl?: string | null;
  sharePublicBaseUrl?: string | null;
}): Promise<RuntimeConfig> {
  if (settings.backendBaseUrl !== undefined) {
    const value = settings.backendBaseUrl?.trim() || null;
    writeDesktopStorage(DESKTOP_BACKEND_STORAGE_KEY, value);
  }
  if (settings.sharePublicBaseUrl !== undefined) {
    const value = settings.sharePublicBaseUrl?.trim() || null;
    writeDesktopStorage(DESKTOP_SHARE_STORAGE_KEY, value);
  }
  return initRuntimeConfig({ force: true });
}

export async function openExternalUrl(url: string): Promise<boolean> {
  const trimmed = String(url || "").trim();
  if (!trimmed) return false;

  if (isTauriRuntime()) {
    try {
      const core = await loadTauriCore();
      await core.invoke("desktop_open_external", { url: trimmed });
      return true;
    } catch {
      return false;
    }
  }

  if (typeof window !== "undefined") {
    window.open(trimmed, "_blank", "noopener,noreferrer");
    return true;
  }
  return false;
}

export async function invokeTauriCommand<T = unknown>(
  command: string,
  payload?: Record<string, unknown>
): Promise<T> {
  if (!isTauriRuntime()) {
    throw new Error("Tauri command invocation requested outside desktop runtime");
  }
  const core = await loadTauriCore();
  return core.invoke<T>(command, payload);
}
