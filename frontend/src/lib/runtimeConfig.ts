import { combineBaseAndPath } from "@/lib/urlJoin";
import {
  invokeTauriCommand as invokeNativeTauriCommand,
  NativeBridgeUnavailableError,
} from "@/lib/tauriBridge";
export { NativeBridgeUnavailableError, NATIVE_BRIDGE_FAILURE_KIND } from "@/lib/tauriBridge";

export type RuntimeMode = "web" | "tauri";
export type AuthMode = "local" | "remote";
export type RuntimeConfigHydrationState = "pending" | "ready" | "failed";

export interface RuntimeConfig {
  mode: RuntimeMode;
  backendBaseUrl: string;
  apiBaseUrl: string;
  sseUrl: string;
  sharePublicBaseUrl: string;
  authMode: AuthMode;
}

type TauriRuntimeConfig = Partial<RuntimeConfig>;

export type DesktopRuntimeAuthConfig = RuntimeConfig & {
  apiKeyPresent: boolean;
  apiKey: string | null;
  envPath: string | null;
  runtimeRoot: string | null;
  failureKind: string | null;
  runtimeContext: string | null;
};

export type LauncherStartupHandoff = {
  shouldRunWizard: boolean;
  setupComplete: boolean;
  runtimeProfile: string;
  envPath: string | null;
  handoffTarget: string | null;
  detail: string;
  setupReadiness: LauncherSetupReadiness | null;
};

export type LauncherSetupReadiness = {
  state: string;
  explanation: string;
  recommendedAction: string;
  details: string | null;
};

export type DesktopStartupRoutingStatus =
  | "setup-incomplete"
  | "runtime-unavailable"
  | "ready-handoff"
  | "launcher-unavailable";

export type DesktopStartupRoutingDecision = {
  status: DesktopStartupRoutingStatus;
  shouldRunWizard: boolean;
  setupComplete: boolean;
  handoffTarget: string | null;
  detail: string;
  setupReadiness: LauncherSetupReadiness | null;
};

const DESKTOP_BACKEND_STORAGE_KEY = "cfy.desktop.backendBaseUrl";
const DESKTOP_SHARE_STORAGE_KEY = "cfy.desktop.sharePublicBaseUrl";

let runtimeConfigCache: RuntimeConfig | null = null;
let runtimeConfigPromise: Promise<RuntimeConfig> | null = null;
let desktopRuntimeAuthConfigCache: DesktopRuntimeAuthConfig | null = null;
let runtimeConfigHydrationState: RuntimeConfigHydrationState = defaultMode() === "tauri" ? "pending" : "ready";
let runtimeConfigHydrationFailureKind: string | null = null;
let runtimeConfigVersion = 0;
const runtimeConfigListeners = new Set<() => void>();

function emitRuntimeConfigChange(): void {
  runtimeConfigVersion += 1;
  for (const listener of runtimeConfigListeners) {
    listener();
  }
}

function setRuntimeConfigHydrationState(
  state: RuntimeConfigHydrationState,
  failureKind: string | null = null
): void {
  runtimeConfigHydrationState = state;
  runtimeConfigHydrationFailureKind = failureKind;
}

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

function asBoolean(value: unknown): boolean {
  return value === true;
}

function normalizeRuntimeProfile(value: unknown): string {
  return normalizeNullableText(value) ?? "unknown";
}

function normalizeLauncherHandoffTarget(value: unknown): string | null {
  const normalized = normalizeNullableText(value);
  if (!normalized) return null;
  return isAbsoluteUrl(normalized) ? normalized.replace(/\/+$/, "") : null;
}

function resolveDesktopStartupRoutingStatus(
  handoff: LauncherStartupHandoff | null
): DesktopStartupRoutingStatus {
  if (!handoff) return "launcher-unavailable";
  if (!handoff.setupComplete) return "setup-incomplete";
  if (handoff.handoffTarget) return "ready-handoff";
  return "runtime-unavailable";
}

function resolveDesktopStartupRoutingDetail(
  status: DesktopStartupRoutingStatus,
  handoff: LauncherStartupHandoff | null
): string {
  const canonicalDetailByStatus: Record<DesktopStartupRoutingStatus, string> = {
    "setup-incomplete":
      "desktop launcher setup is incomplete; continue through setup",
    "runtime-unavailable":
      "desktop launcher is configured, but the local runtime is not ready",
    "ready-handoff": "desktop launcher handoff is ready",
    "launcher-unavailable":
      "Codexify could not read or refresh launcher setup readiness yet. Retry setup checks from the desktop launcher and review Docker, Ollama, config, backend, and frontend readiness.",
  };

  return (
    normalizeNullableText(handoff?.detail) ??
    canonicalDetailByStatus[status]
  );
}

function buildDesktopStartupRoutingDecision(
  handoff: LauncherStartupHandoff | null
): DesktopStartupRoutingDecision | null {
  if (!handoff) return null;

  const status = resolveDesktopStartupRoutingStatus(handoff);
  return {
    status,
    shouldRunWizard: status === "setup-incomplete",
    setupComplete: handoff.setupComplete,
    handoffTarget: handoff.handoffTarget,
    detail: resolveDesktopStartupRoutingDetail(status, handoff),
    setupReadiness: handoff.setupReadiness,
  };
}

export function isTauriRuntime(): boolean {
  if (typeof window === "undefined") return false;
  return (
    typeof (window as any).__TAURI_IPC__ !== "undefined" ||
    typeof (window as any).__TAURI_INTERNALS__ !== "undefined"
  );
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
  const readinessSource =
    source.setupReadiness && typeof source.setupReadiness === "object"
      ? (source.setupReadiness as Record<string, unknown>)
      : null;
  const setupReadiness = readinessSource
    ? {
        state: normalizeNullableText(readinessSource.state) ?? "unknown",
        explanation:
          normalizeNullableText(readinessSource.explanation) ??
          "Codexify is checking local setup readiness.",
        recommendedAction:
          normalizeNullableText(readinessSource.recommendedAction) ??
          "Retry setup after checking local services.",
        details: normalizeNullableText(readinessSource.details),
      }
    : null;

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
    setupReadiness,
  };
}

function normalizeDesktopRuntimeAuthConfig(
  payload: unknown
): DesktopRuntimeAuthConfig | null {
  if (!payload || typeof payload !== "object") return null;
  const source = payload as Record<string, unknown>;
  const backendBaseUrl = normalizeNullableText(source.backendBaseUrl);
  const apiBaseUrl = normalizeNullableText(source.apiBaseUrl);
  const sseUrl = normalizeNullableText(source.sseUrl);
  const sharePublicBaseUrl = normalizeNullableText(source.sharePublicBaseUrl);
  const authMode = coerceAuthMode(
    normalizeNullableText(source.authMode) ?? "local"
  );

  if (!backendBaseUrl || !apiBaseUrl || !sseUrl || !sharePublicBaseUrl) {
    return null;
  }

  return {
    mode: "tauri",
    backendBaseUrl,
    apiBaseUrl,
    sseUrl,
    sharePublicBaseUrl,
    authMode,
    apiKeyPresent: asBoolean(source.apiKeyPresent),
    apiKey: normalizeNullableText(source.apiKey),
    envPath: normalizeNullableText(source.envPath),
    runtimeRoot: normalizeNullableText(source.runtimeRoot),
    failureKind: normalizeNullableText(source.failureKind),
    runtimeContext: normalizeNullableText(source.runtimeContext),
  };
}

export async function readDesktopLauncherStartupHandoff(): Promise<LauncherStartupHandoff | null> {
  if (!isTauriRuntime()) return null;
  try {
    const payload = await invokeNativeTauriCommand<unknown>(
      "desktop_get_launcher_startup_handoff"
    );
    return normalizeLauncherStartupHandoff(payload);
  } catch (error) {
    if (error instanceof NativeBridgeUnavailableError) {
      throw error;
    }
    return null;
  }
}

export async function readDesktopStartupRoutingDecision(): Promise<DesktopStartupRoutingDecision | null> {
  if (!isTauriRuntime()) return null;

  const handoff = await readDesktopLauncherStartupHandoff();
  const decision = buildDesktopStartupRoutingDecision(handoff);
  if (!handoff || handoff.setupReadiness) {
    return decision;
  }

  const refreshedHandoff = await readDesktopLauncherStartupHandoff();
  const refreshedDecision = buildDesktopStartupRoutingDecision(refreshedHandoff);
  if (refreshedDecision?.setupReadiness) {
    return refreshedDecision;
  }

  return refreshedDecision ?? decision;
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

function isWebUiComposeBundle(): boolean {
  return readRuntimeEnv("VITE_WEBUI_COMPOSE_BUNDLE") === "1";
}

function defaultBackendBaseUrl(mode: RuntimeMode): string {
  const envBackend = readRuntimeEnv("VITE_GUARDIAN_API_BASE") || readRuntimeEnv("GUARDIAN_API_BASE");
  if (isAbsoluteUrl(envBackend)) {
    return normalizeBase(envBackend, "http://127.0.0.1:8888");
  }
  if (mode === "tauri") {
    return "http://127.0.0.1:8888";
  }
  if (isWebUiComposeBundle() && typeof window !== "undefined" && window.location?.origin) {
    // The standalone webUI bundle is same-origin behind nginx, so browser requests stay on the bundle host.
    return normalizeBase(window.location.origin, "");
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

  return mode === "tauri" ? defaultBackendBaseUrl(mode) : defaultBackendBaseUrl(mode);
}

function resolveApiBaseUrl(mode: RuntimeMode, backendBaseUrl: string, explicit: string): string {
  const candidate = explicit.trim();
  if (isAbsoluteUrl(candidate)) {
    return normalizeBase(candidate, combineBaseAndPath(backendBaseUrl, "/api"));
  }
  if (mode === "tauri") {
    return normalizeBase(
      combineBaseAndPath(backendBaseUrl, "/api"),
      "http://127.0.0.1:8888/api"
    );
  }
  if (candidate.startsWith("/")) {
    return normalizeBase(candidate, "/api");
  }
  if (candidate) {
    return normalizeBase(`/${candidate}`, "/api");
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
  if (!isTauriRuntime()) {
    desktopRuntimeAuthConfigCache = null;
    try {
      const { clearRuntimeApiKey } = await import("@/lib/runtimeAuth");
      clearRuntimeApiKey();
    } catch {
      // Ignore cache wiring failures; the web runtime can still proceed.
    }
    return null;
  }
  try {
    const payload = await invokeNativeTauriCommand<unknown>(
      "desktop_get_runtime_auth_config"
    );
    const authConfig = normalizeDesktopRuntimeAuthConfig(payload);
    desktopRuntimeAuthConfigCache = authConfig;
    if (authConfig?.apiKey) {
      try {
        const { setRuntimeApiKey } = await import("@/lib/runtimeAuth");
        setRuntimeApiKey(authConfig.apiKey);
      } catch {
        // Ignore auth cache wiring failures; the runtime config itself still resolves.
      }
    } else if (authConfig) {
      try {
        const { clearRuntimeApiKey } = await import("@/lib/runtimeAuth");
        clearRuntimeApiKey();
      } catch {
        // Ignore cache wiring failures; the runtime config itself still resolves.
      }
    }
    if (authConfig) {
      return {
        mode: authConfig.mode,
        backendBaseUrl: authConfig.backendBaseUrl,
        apiBaseUrl: authConfig.apiBaseUrl,
        sseUrl: authConfig.sseUrl,
        sharePublicBaseUrl: authConfig.sharePublicBaseUrl,
        authMode: authConfig.authMode,
      };
    }

    const legacyPayload = await invokeNativeTauriCommand<any>(
      "desktop_get_runtime_config"
    );
    if (!legacyPayload || typeof legacyPayload !== "object") return null;
    desktopRuntimeAuthConfigCache = {
      mode: "tauri",
      backendBaseUrl: String(legacyPayload.backendBaseUrl ?? "").trim(),
      apiBaseUrl: String(legacyPayload.apiBaseUrl ?? "").trim(),
      sseUrl: String(legacyPayload.sseUrl ?? "").trim(),
      sharePublicBaseUrl: String(legacyPayload.sharePublicBaseUrl ?? "").trim(),
      authMode:
        String(legacyPayload.authMode ?? "")
          .trim()
          .toLowerCase() === "remote"
          ? "remote"
          : "local",
      apiKeyPresent: false,
      apiKey: null,
      envPath: null,
      runtimeRoot: null,
      failureKind: null,
      runtimeContext: "packaged",
    };
    try {
      const { clearRuntimeApiKey } = await import("@/lib/runtimeAuth");
      clearRuntimeApiKey();
    } catch {
      // Ignore cache wiring failures; the runtime config itself still resolves.
    }
    return {
      mode: "tauri",
      backendBaseUrl: desktopRuntimeAuthConfigCache.backendBaseUrl,
      apiBaseUrl: desktopRuntimeAuthConfigCache.apiBaseUrl,
      sseUrl: desktopRuntimeAuthConfigCache.sseUrl,
      sharePublicBaseUrl: desktopRuntimeAuthConfigCache.sharePublicBaseUrl,
      authMode: desktopRuntimeAuthConfigCache.authMode,
    };
  } catch (error) {
    if (error instanceof NativeBridgeUnavailableError) {
      throw error;
    }
    return null;
  }
}

export function getDesktopRuntimeAuthConfig(): DesktopRuntimeAuthConfig | null {
  return desktopRuntimeAuthConfigCache;
}

export function getRuntimeConfigHydrationState(): RuntimeConfigHydrationState {
  if (runtimeConfigHydrationState === "pending" && !isTauriRuntime()) {
    return "ready";
  }
  return runtimeConfigHydrationState;
}

export function getRuntimeConfigHydrationFailureKind(): string | null {
  return runtimeConfigHydrationFailureKind;
}

export function getRuntimeConfigVersion(): number {
  return runtimeConfigVersion;
}

export function subscribeRuntimeConfigState(listener: () => void): () => void {
  runtimeConfigListeners.add(listener);
  return () => {
    runtimeConfigListeners.delete(listener);
  };
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
  if (mode === "tauri") {
    setRuntimeConfigHydrationState("pending");
  } else {
    setRuntimeConfigHydrationState("ready");
  }
  runtimeConfigPromise = (async () => {
    try {
      const [launcherStartup, tauriConfig] = await Promise.all([
        readDesktopLauncherStartupHandoff(),
        readTauriRuntimeConfig(),
      ]);
      const config = buildRuntimeConfig(mode, tauriConfig, launcherStartup);
      runtimeConfigCache = config;
      if (mode === "tauri") {
        setRuntimeConfigHydrationState(
          tauriConfig ? "ready" : "failed",
          tauriConfig ? null : (desktopRuntimeAuthConfigCache?.failureKind ?? null)
        );
      } else {
        setRuntimeConfigHydrationState("ready");
      }
      emitRuntimeConfigChange();
      return config;
    } catch (error) {
      const failureKind =
        error instanceof NativeBridgeUnavailableError
          ? error.code
          : "runtime-config-hydration-failed";
      setRuntimeConfigHydrationState("failed", failureKind);
      emitRuntimeConfigChange();
      throw error;
    } finally {
      runtimeConfigPromise = null;
    }
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
      await invokeNativeTauriCommand("desktop_open_external", { url: trimmed });
      return true;
    } catch (error) {
      if (error instanceof NativeBridgeUnavailableError) {
        return false;
      }
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
    throw new NativeBridgeUnavailableError(
      "Tauri native bridge is unavailable outside the desktop runtime."
    );
  }
  return invokeNativeTauriCommand<T>(command, payload);
}
