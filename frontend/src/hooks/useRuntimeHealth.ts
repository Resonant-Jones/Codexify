import { useCallback, useEffect, useRef, useState } from "react";
import api, { getAuthToken, getDevApiKey, readRuntimeApiKey } from "@/lib/api";
import { useLiveEvents } from "@/hooks/useLiveEvents";
import {
  getDesktopRuntimeAuthConfig,
  getRuntimeConfigHydrationFailureKind,
  getRuntimeConfigHydrationState,
  getRuntimeConfigVersion,
  getRuntimeConfigSync,
  isTauriRuntime,
  subscribeRuntimeConfigState,
} from "@/lib/runtimeConfig";
import { useSyncExternalStore } from "react";
import {
  resolveRuntimeAuthSource,
  type RuntimeAuthSource,
} from "@/lib/runtimeAuth";
import {
  LIVE_EVENT_CONNECTION_STATES,
  LiveEventConnectionState,
  RUNTIME_HEALTH_FAILURE_KINDS,
  RUNTIME_HEALTH_STATUSES,
  RuntimeHealthFailureKindToken,
  RuntimeHealthStatusToken,
} from "@/contracts/runtimeTokens";
import type { LiveEventsDiagnostics } from "@/hooks/useLiveEvents";

const POLL_INTERVAL_MS = 15000;
const STALE_THRESHOLD_MS = 45000;
const CHAT_HEALTH_ENDPOINT = "/health/chat";
const LLM_HEALTH_ENDPOINT = "/api/health/llm";

export type RuntimeFailureKind = RuntimeHealthFailureKindToken;
export type RuntimeHealthAuthSource =
  | "runtime-desktop"
  | "vite-dev"
  | "bearer-only"
  | "none"
  | "unknown";

export type RuntimeHealthStateSource =
  | "live-poll"
  | "cached"
  | "fallback"
  | "unknown";

export type RuntimeHealthEndpointObservation = {
  endpoint: string;
  httpStatus: number | null;
  transportErrorClass: string | null;
  parsedStatus: string | null;
  parsedOk: boolean | null;
  detailsStatus?: string | null;
  detailsOk?: boolean | null;
  provider?: string | null;
  model?: string | null;
  providerRuntimeAvailable?: boolean | null;
  endpointResolutionState?: string | null;
  failureReason?: string | null;
};

export type RuntimeHealthDiagnostics = {
  resolvedApiBaseUrl: string | null;
  resolvedApiBaseUrlSource:
    | "runtime-desktop"
    | "vite-dev"
    | "local-storage-override"
    | "fallback"
    | "unknown";
  apiKeyPresent: boolean;
  apiKeySource: RuntimeHealthAuthSource;
  hydrationState: "pending" | "ready" | "failed";
  nativeCommandStatus: string | null;
  authSource: RuntimeHealthAuthSource;
  chat: RuntimeHealthEndpointObservation;
  llm: RuntimeHealthEndpointObservation;
  liveEvents: LiveEventsDiagnostics;
  failureKind: RuntimeFailureKind | null;
  lastSuccessAt: number | null;
  lastFailedAt: number | null;
  lastCheckedAt: number | null;
  currentComputedStateSource: RuntimeHealthStateSource;
};

export type RuntimeHealthStatus = {
  status: RuntimeHealthStatusToken;
  failureKind: RuntimeFailureKind | null;
  llmDetail: string | null;
  backendReachable: boolean | null;
  chatHealthy: boolean | null;
  llmHealthy: boolean | null;
  liveEventsStatus: LiveEventConnectionState;
  lastSuccessAt: number | null;
  lastCheckedAt: number | null;
  lastFailedAt: number | null;
  stale: boolean;
  diagnostics: RuntimeHealthDiagnostics;
};

type HealthSnapshot = {
  backendReachable: boolean | null;
  healthEndpointMissing: boolean | null;
  chat: RuntimeHealthEndpointObservation & {
    derivedHealthy: boolean | null;
    reachable: boolean;
    missing: boolean;
    payload: unknown | null;
  };
  llm: RuntimeHealthEndpointObservation & {
    derivedHealthy: boolean | null;
    reachable: boolean;
    missing: boolean;
    payload: unknown | null;
  };
  llmDetail: string | null;
  lastSuccessAt: number | null;
  lastFailedAt: number | null;
  lastCheckedAt: number | null;
};

const INITIAL_SNAPSHOT: HealthSnapshot = {
  backendReachable: null,
  healthEndpointMissing: null,
  chat: {
    endpoint: CHAT_HEALTH_ENDPOINT,
    httpStatus: null,
    transportErrorClass: null,
    parsedStatus: null,
    parsedOk: null,
    derivedHealthy: null,
    reachable: false,
    missing: false,
    payload: null,
  },
  llm: {
    endpoint: LLM_HEALTH_ENDPOINT,
    httpStatus: null,
    transportErrorClass: null,
    parsedStatus: null,
    parsedOk: null,
    derivedHealthy: null,
    reachable: false,
    missing: false,
    payload: null,
  },
  llmDetail: null,
  lastSuccessAt: null,
  lastFailedAt: null,
  lastCheckedAt: null,
};

function isHealthStatusToken(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim().toLowerCase();
  return trimmed.length > 0 ? trimmed : null;
}

function isGreenStatusToken(value: string | null): boolean {
  return Boolean(value && ["ok", "healthy", "online"].includes(value));
}

function isRedStatusToken(value: string | null): boolean {
  return Boolean(
    value &&
      ["offline", "degraded", "error", "unavailable", "red", "failed"].includes(
        value
      )
  );
}

function readPayloadValue(payload: unknown, path: string[]): unknown {
  let current: unknown = payload;
  for (const key of path) {
    if (!current || typeof current !== "object") {
      return undefined;
    }
    current = (current as Record<string, unknown>)[key];
  }
  return current;
}

type HealthResult = {
  reachable: boolean;
  ok: boolean | null;
  missing: boolean;
};

function responseStatusFromResult(
  result: PromiseSettledResult<{ data?: unknown }>
): number | null {
  if (result.status !== "rejected") return null;
  const reason = result.reason as { response?: { status?: number } } | null;
  const status = reason?.response?.status;
  return typeof status === "number" ? status : null;
}

function getTransportErrorClass(error: unknown): string | null {
  if (!error || typeof error !== "object") return null;
  const candidate = error as { name?: unknown; code?: unknown };
  const name =
    typeof candidate.name === "string" && candidate.name.trim()
      ? candidate.name.trim()
      : null;
  if (name) return name;
  const code =
    typeof candidate.code === "string" && candidate.code.trim()
      ? candidate.code.trim()
      : null;
  return code;
}

function readParsedStatus(payload: unknown): string | null {
  const topLevel = isHealthStatusToken(readPayloadValue(payload, ["status"]));
  if (topLevel) return topLevel;
  return isHealthStatusToken(readPayloadValue(payload, ["details", "status"]));
}

function readParsedOk(payload: unknown): boolean | null {
  const topLevel = readPayloadValue(payload, ["ok"]);
  if (typeof topLevel === "boolean") return topLevel;
  const nested = readPayloadValue(payload, ["details", "ok"]);
  return typeof nested === "boolean" ? nested : null;
}

function readPayloadString(
  payload: unknown,
  path: string[]
): string | null {
  const value = readPayloadValue(payload, path);
  return typeof value === "string" && value.trim() ? value.trim() : null;
}

function readPayloadBoolean(
  payload: unknown,
  path: string[]
): boolean | null {
  const value = readPayloadValue(payload, path);
  return typeof value === "boolean" ? value : null;
}

function deriveHealthySignal(payload: unknown, httpStatus: number | null): boolean | null {
  const parsedOk = readParsedOk(payload);
  if (parsedOk !== null) return parsedOk;
  const parsedStatus = readParsedStatus(payload);
  if (parsedStatus) {
    return isGreenStatusToken(parsedStatus);
  }
  if (httpStatus == null) return null;
  return httpStatus >= 200 && httpStatus < 300;
}

function deriveLlmHealthySignal(
  payload: unknown,
  httpStatus: number | null
): boolean | null {
  const parsedOk = readParsedOk(payload);
  const parsedStatus = readParsedStatus(payload);
  const detailsOk = readPayloadBoolean(payload, ["details", "ok"]);
  const providerRuntimeAvailable =
    readPayloadBoolean(payload, ["details", "provider_runtime", "available"]) ??
    readPayloadBoolean(payload, ["provider_runtime", "available"]);
  const endpointResolutionState =
    readPayloadString(payload, ["details", "endpoint_resolution", "state"]) ??
    readPayloadString(payload, ["endpoint_resolution", "state"]);

  const positiveSignals = [
    parsedOk === true,
    isGreenStatusToken(parsedStatus),
    detailsOk === true,
    providerRuntimeAvailable === true,
    endpointResolutionState === "available",
  ].some(Boolean);

  const negativeSignals = [
    parsedOk === false,
    isRedStatusToken(parsedStatus),
    detailsOk === false,
    providerRuntimeAvailable === false,
    endpointResolutionState != null &&
      endpointResolutionState.toLowerCase() !== "available",
    ].some(Boolean);

  if (negativeSignals) {
    return false;
  }
  if (positiveSignals) {
    return true;
  }
  if (httpStatus == null) return null;
  return httpStatus >= 200 && httpStatus < 300;
}

function summarizeHealthResult(
  endpoint: string,
  result: PromiseSettledResult<{ data?: unknown }>
): HealthResult & RuntimeHealthEndpointObservation & {
  derivedHealthy: boolean | null;
  payload: unknown | null;
} {
  if (result.status === "fulfilled") {
    const payload = result.value?.data ?? null;
    const isLlmEndpoint = endpoint === LLM_HEALTH_ENDPOINT;
    const derivedHealthy = isLlmEndpoint
      ? deriveLlmHealthySignal(payload, 200)
      : deriveHealthySignal(payload, 200);
    return {
      endpoint,
      reachable: true,
      ok: derivedHealthy,
      derivedHealthy,
      missing: false,
      httpStatus: 200,
      transportErrorClass: null,
      parsedStatus: readParsedStatus(payload),
      parsedOk: readParsedOk(payload),
      detailsStatus: readPayloadString(payload, ["details", "status"]),
      detailsOk: readPayloadBoolean(payload, ["details", "ok"]),
      provider: isLlmEndpoint ? readPayloadString(payload, ["provider"]) : null,
      model: isLlmEndpoint ? readPayloadString(payload, ["model"]) : null,
      providerRuntimeAvailable: isLlmEndpoint
        ? readPayloadBoolean(payload, ["details", "provider_runtime", "available"]) ??
          readPayloadBoolean(payload, ["provider_runtime", "available"])
        : null,
      endpointResolutionState: isLlmEndpoint
        ? readPayloadString(payload, ["details", "endpoint_resolution", "state"]) ??
          readPayloadString(payload, ["endpoint_resolution", "state"])
        : null,
      failureReason: isLlmEndpoint
        ? deriveLlmFailureReason(payload)
        : null,
      payload,
    };
  }

  const status = responseStatusFromResult(result);
  const payload =
    (result.reason as { response?: { data?: unknown } } | null)?.response?.data ??
    null;
  const missing = status === 404;
  const reachable = status != null;
  const isLlmEndpoint = endpoint === LLM_HEALTH_ENDPOINT;
  return {
    endpoint,
    reachable,
    ok: missing
      ? false
      : isLlmEndpoint
        ? deriveLlmHealthySignal(payload, status)
        : deriveHealthySignal(payload, status),
    derivedHealthy: missing
      ? false
      : isLlmEndpoint
        ? deriveLlmHealthySignal(payload, status)
        : deriveHealthySignal(payload, status),
    missing,
    httpStatus: status,
    transportErrorClass: status == null ? getTransportErrorClass(result.reason) : null,
    parsedStatus: readParsedStatus(payload),
    parsedOk: readParsedOk(payload),
    detailsStatus: readPayloadString(payload, ["details", "status"]),
    detailsOk: readPayloadBoolean(payload, ["details", "ok"]),
    provider: isLlmEndpoint ? readPayloadString(payload, ["provider"]) : null,
    model: isLlmEndpoint ? readPayloadString(payload, ["model"]) : null,
    providerRuntimeAvailable: isLlmEndpoint
      ? readPayloadBoolean(payload, ["details", "provider_runtime", "available"]) ??
        readPayloadBoolean(payload, ["provider_runtime", "available"])
      : null,
    endpointResolutionState: isLlmEndpoint
      ? readPayloadString(payload, ["details", "endpoint_resolution", "state"]) ??
        readPayloadString(payload, ["endpoint_resolution", "state"])
      : null,
    failureReason: isLlmEndpoint ? deriveLlmFailureReason(payload) : null,
    payload,
  };
}

function deriveLlmFailureReason(payload: unknown): string | null {
  const parsedStatus = readParsedStatus(payload);
  const parsedOk = readParsedOk(payload);
  const detailsStatus = readPayloadString(payload, ["details", "status"]);
  const detailsOk = readPayloadBoolean(payload, ["details", "ok"]);
  const provider = readPayloadString(payload, ["provider"]);
  const providerRuntimeAvailable =
    readPayloadBoolean(payload, ["details", "provider_runtime", "available"]) ??
    readPayloadBoolean(payload, ["provider_runtime", "available"]);
  const endpointResolutionState =
    readPayloadString(payload, ["details", "endpoint_resolution", "state"]) ??
    readPayloadString(payload, ["endpoint_resolution", "state"]);

  if (provider && provider.trim().toLowerCase() !== "local") {
    return `provider=${provider}`;
  }
  if (parsedOk === false) return "ok=false";
  if (detailsOk === false) return "details.ok=false";
  if (providerRuntimeAvailable === false) {
    return "provider_runtime.available=false";
  }
  if (
    endpointResolutionState &&
    endpointResolutionState.trim().toLowerCase() !== "available"
  ) {
    return `endpoint_resolution.state=${endpointResolutionState}`;
  }
  if (isRedStatusToken(detailsStatus)) {
    return `details.status=${detailsStatus}`;
  }
  if (isRedStatusToken(parsedStatus)) {
    return `status=${parsedStatus}`;
  }
  return null;
}

function resolveRuntimeHealthAuthSource(): RuntimeHealthAuthSource {
  const desktopAuthConfig = getDesktopRuntimeAuthConfig();
  const runtimeDesktopKeyPresent = Boolean(
    desktopAuthConfig?.apiKeyPresent || readRuntimeApiKey()
  );
  const devKeyPresent = Boolean(getDevApiKey().trim());
  const bearerPresent = Boolean(getAuthToken());
  return resolveRuntimeAuthSource({
    isTauriRuntime: isTauriRuntime(),
    runtimeDesktopKeyPresent,
    devKeyPresent,
    bearerPresent,
    desktopAuthConfigKnown: Boolean(desktopAuthConfig),
  });
}

function resolveRuntimeBaseUrlSource(
  hydrationState: "pending" | "ready" | "failed",
  runtimeConfigMode: "web" | "tauri",
  desktopAuthConfig: ReturnType<typeof getDesktopRuntimeAuthConfig>
): RuntimeHealthDiagnostics["resolvedApiBaseUrlSource"] {
  if (hydrationState === "pending" || hydrationState === "failed") {
    return "fallback";
  }
  if (desktopAuthConfig && runtimeConfigMode === "tauri") {
    try {
      if (
        typeof window !== "undefined" &&
        window.localStorage.getItem("cfy.desktop.backendBaseUrl")
      ) {
        return "local-storage-override";
      }
    } catch {
      // Ignore localStorage access failures and fall back to the native source.
    }
    return "runtime-desktop";
  }
  if (runtimeConfigMode === "tauri") {
    return "fallback";
  }
  if (getDevApiKey().trim()) {
    return "vite-dev";
  }
  return "unknown";
}

function formatTimestamp(value: number | null): string {
  return value == null ? "<none>" : new Date(value).toISOString();
}

export function formatRuntimeHealthDiagnostics(
  diagnostics: RuntimeHealthDiagnostics
): string[] {
  return [
    `resolved api base url=${diagnostics.resolvedApiBaseUrl ?? "<unresolved>"}`,
    `resolved api base url source=${diagnostics.resolvedApiBaseUrlSource}`,
    `apiKeyPresent=${diagnostics.apiKeyPresent ? "true" : "false"}`,
    `api key source=${diagnostics.apiKeySource}`,
    `hydration state=${diagnostics.hydrationState}`,
    `native command status=${diagnostics.nativeCommandStatus ?? "<unknown>"}`,
    `authSource=${diagnostics.authSource}`,
    `chat endpoint called=${diagnostics.chat.endpoint}`,
    diagnostics.chat.httpStatus != null
      ? `chat HTTP status=${diagnostics.chat.httpStatus}`
      : `chat transport error class=${diagnostics.chat.transportErrorClass ?? "<none>"}`,
    `parsed chat health status=${diagnostics.chat.parsedStatus ?? "<none>"}`,
    `parsed chat health ok=${
      diagnostics.chat.parsedOk == null
        ? "<unknown>"
        : diagnostics.chat.parsedOk
          ? "true"
          : "false"
    }`,
    `llm endpoint called=${diagnostics.llm.endpoint}`,
    diagnostics.llm.httpStatus != null
      ? `llm HTTP status=${diagnostics.llm.httpStatus}`
      : `llm transport error class=${diagnostics.llm.transportErrorClass ?? "<none>"}`,
    `parsed llm health status=${diagnostics.llm.parsedStatus ?? "<none>"}`,
    `parsed llm health ok=${
      diagnostics.llm.parsedOk == null
        ? "<unknown>"
        : diagnostics.llm.parsedOk
          ? "true"
          : "false"
    }`,
    `parsed llm details status=${diagnostics.llm.detailsStatus ?? "<none>"}`,
    `parsed llm details ok=${
      diagnostics.llm.detailsOk == null
        ? "<unknown>"
        : diagnostics.llm.detailsOk
          ? "true"
          : "false"
    }`,
    `parsed llm provider=${diagnostics.llm.provider ?? "<none>"}`,
    `parsed llm model=${diagnostics.llm.model ?? "<none>"}`,
    `parsed llm provider runtime available=${
      diagnostics.llm.providerRuntimeAvailable == null
        ? "<unknown>"
        : diagnostics.llm.providerRuntimeAvailable
          ? "true"
          : "false"
    }`,
    `parsed llm endpoint resolution state=${
      diagnostics.llm.endpointResolutionState ?? "<none>"
    }`,
    `parsed llm failure reason=${diagnostics.llm.failureReason ?? "<none>"}`,
    `live events endpoint called=${diagnostics.liveEvents.endpoint ?? "<unresolved>"}`,
    `live events connection state=${diagnostics.liveEvents.connectionState}`,
    `live events last event=${formatTimestamp(diagnostics.liveEvents.lastEventAt)}`,
    `live events last ping=${formatTimestamp(diagnostics.liveEvents.lastPingAt)}`,
    diagnostics.liveEvents.lastHttpStatus != null
      ? `live events HTTP status=${diagnostics.liveEvents.lastHttpStatus}`
      : `live events transport error class=${diagnostics.liveEvents.transportErrorClass ?? "<none>"}`,
    `live events authSource=${diagnostics.liveEvents.authSource}`,
    `live events apiKeyPresent=${diagnostics.liveEvents.apiKeyPresent ? "true" : "false"}`,
    `live events reconnect attempts=${diagnostics.liveEvents.reconnectAttempts}`,
    `live events status updated=${formatTimestamp(diagnostics.liveEvents.statusUpdatedAt)}`,
    `failureKind=${diagnostics.failureKind ?? "none"}`,
    `last successful health poll=${formatTimestamp(diagnostics.lastSuccessAt)}`,
    `last failed health poll=${formatTimestamp(diagnostics.lastFailedAt)}`,
    `current health poll=${formatTimestamp(diagnostics.lastCheckedAt)}`,
    `current computed state source=${diagnostics.currentComputedStateSource}`,
  ];
}

function normalizeDetail(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed.length > 0 ? trimmed : null;
}

function extractLlmDetail(payload: unknown): string | null {
  if (!payload || typeof payload !== "object") return null;
  const candidate = payload as Record<string, unknown>;
  const providerRuntime = candidate.provider_runtime;
  if (providerRuntime && typeof providerRuntime === "object") {
    const modelIndex = (
      providerRuntime as Record<string, unknown>
    ).model_index;
    if (modelIndex && typeof modelIndex === "object") {
      const index = modelIndex as Record<string, unknown>;
      return (
        normalizeDetail(index.reason) ??
        normalizeDetail(index.failure_kind) ??
        normalizeDetail(index.state)
      );
    }
    const runtimeReason = providerRuntime as Record<string, unknown>;
    return (
      normalizeDetail(runtimeReason.reason) ??
      normalizeDetail(runtimeReason.failure_kind) ??
      normalizeDetail(runtimeReason.status_reason)
    );
  }
  return (
    normalizeDetail(candidate.error) ??
    normalizeDetail(candidate.status_reason) ??
    null
  );
}

export function useRuntimeHealth(): RuntimeHealthStatus {
  const liveEvents = useLiveEvents({ passive: true });
  const connectionStatus =
    liveEvents.connectionStatus ?? LIVE_EVENT_CONNECTION_STATES.DISCONNECTED;
  const statusUpdatedAt = liveEvents.statusUpdatedAt ?? null;
  const liveEventsDiagnostics = liveEvents.diagnostics;
  const runtimeConfigVersion = useSyncExternalStore(
    subscribeRuntimeConfigState,
    getRuntimeConfigVersion,
    getRuntimeConfigVersion
  );
  const runtimeConfigHydrationState = useSyncExternalStore(
    subscribeRuntimeConfigState,
    getRuntimeConfigHydrationState,
    getRuntimeConfigHydrationState
  );
  const [snapshot, setSnapshot] = useState<HealthSnapshot>(INITIAL_SNAPSHOT);
  const inFlightRef = useRef(false);
  const firstCheckAtRef = useRef<number | null>(null);

  const poll = useCallback(async () => {
    if (inFlightRef.current) return;
    inFlightRef.current = true;
    const startedAt = Date.now();
    if (!firstCheckAtRef.current) {
      firstCheckAtRef.current = startedAt;
    }
    try {
      const [llmResult, chatResult] =
        await Promise.allSettled([
          api.get("/api/health/llm"),
          api.get("/health/chat"),
        ]);
      const llmHealth = summarizeHealthResult(LLM_HEALTH_ENDPOINT, llmResult);
      const chatHealth = summarizeHealthResult(CHAT_HEALTH_ENDPOINT, chatResult);
      const backendReachable = llmHealth.reachable || chatHealth.reachable;
      const chatHealthy = chatHealth.ok;
      const llmHealthy = llmHealth.ok;
      const llmDetail = extractLlmDetail(llmHealth.payload);
      const healthEndpointMissing = llmHealth.missing || chatHealth.missing;
      const success =
        backendReachable && chatHealthy === true && llmHealthy === true;

      setSnapshot((prev) => ({
        backendReachable,
        healthEndpointMissing,
        chat: chatHealth,
        llm: llmHealth,
        llmDetail,
        lastCheckedAt: startedAt,
        lastFailedAt: success ? prev.lastFailedAt : startedAt,
        lastSuccessAt: success ? startedAt : prev.lastSuccessAt,
      }));
    } finally {
      inFlightRef.current = false;
    }
  }, [runtimeConfigVersion]);

  useEffect(() => {
    if (runtimeConfigHydrationState === "pending") {
      return;
    }
    if (runtimeConfigHydrationState === "failed") {
      return;
    }
    void poll();
    const timer = setInterval(() => {
      void poll();
    }, POLL_INTERVAL_MS);
    return () => clearInterval(timer);
  }, [poll, runtimeConfigHydrationState, runtimeConfigVersion]);

  const now = Date.now();
  const hasChecked = snapshot.lastCheckedAt != null;
  const lastSuccessAt = snapshot.lastSuccessAt;
  const lastFailedAt = snapshot.lastFailedAt;
  const firstCheckAt = firstCheckAtRef.current;
  const stale =
    lastSuccessAt != null
      ? now - lastSuccessAt > STALE_THRESHOLD_MS
      : firstCheckAt != null
        ? now - firstCheckAt > STALE_THRESHOLD_MS
        : false;
  let failureKind: RuntimeFailureKind | null = null;
  if (hasChecked && snapshot.backendReachable === false) {
    failureKind = RUNTIME_HEALTH_FAILURE_KINDS.BACKEND_UNREACHABLE;
  } else if (hasChecked && snapshot.healthEndpointMissing) {
    failureKind = RUNTIME_HEALTH_FAILURE_KINDS.HEALTH_ENDPOINT_MISSING;
  } else if (hasChecked && snapshot.chat.derivedHealthy === false) {
    failureKind = RUNTIME_HEALTH_FAILURE_KINDS.CHAT_UNHEALTHY;
  } else if (hasChecked && snapshot.llm.derivedHealthy === false) {
    failureKind = RUNTIME_HEALTH_FAILURE_KINDS.LLM_UNHEALTHY;
  } else if (stale) {
    failureKind = RUNTIME_HEALTH_FAILURE_KINDS.STALE;
  }

  const currentComputedStateSource: RuntimeHealthStateSource = hasChecked
    ? stale
      ? "cached"
      : "live-poll"
    : "fallback";
  const desktopRuntimeAuthConfig = getDesktopRuntimeAuthConfig();
  const runtimeConfig = getRuntimeConfigSync();
  const resolvedApiBaseUrl = runtimeConfig.apiBaseUrl || null;
  const hydrationState = runtimeConfigHydrationState;
  const nativeCommandStatus =
    hydrationState === "failed"
      ? getRuntimeConfigHydrationFailureKind() ?? "failed"
      : hydrationState;
  const runtimeDesktopKeyPresent = Boolean(
    desktopRuntimeAuthConfig?.apiKeyPresent || readRuntimeApiKey()
  );
  const apiKeyPresent = Boolean(runtimeDesktopKeyPresent || getDevApiKey().trim());
  const authSource = resolveRuntimeHealthAuthSource();
  const resolvedApiBaseUrlSource = resolveRuntimeBaseUrlSource(
    hydrationState,
    runtimeConfig.mode,
    desktopRuntimeAuthConfig
  );
  const apiKeySource = authSource;
  const diagnostics: RuntimeHealthDiagnostics = {
    resolvedApiBaseUrl,
    resolvedApiBaseUrlSource,
    apiKeyPresent,
    apiKeySource,
    hydrationState,
    nativeCommandStatus,
    authSource,
    chat: {
      endpoint: snapshot.chat.endpoint,
      httpStatus: snapshot.chat.httpStatus,
      transportErrorClass: snapshot.chat.transportErrorClass,
      parsedStatus: snapshot.chat.parsedStatus,
      parsedOk: snapshot.chat.parsedOk,
    },
    llm: {
      endpoint: snapshot.llm.endpoint,
      httpStatus: snapshot.llm.httpStatus,
      transportErrorClass: snapshot.llm.transportErrorClass,
      parsedStatus: snapshot.llm.parsedStatus,
      parsedOk: snapshot.llm.parsedOk,
      detailsStatus: snapshot.llm.detailsStatus,
      detailsOk: snapshot.llm.detailsOk,
      provider: snapshot.llm.provider,
      model: snapshot.llm.model,
      providerRuntimeAvailable: snapshot.llm.providerRuntimeAvailable,
      endpointResolutionState: snapshot.llm.endpointResolutionState,
      failureReason: snapshot.llm.failureReason,
    },
    liveEvents: {
      endpoint: liveEventsDiagnostics.endpoint,
      connectionState: liveEventsDiagnostics.connectionState,
      lastEventAt: liveEventsDiagnostics.lastEventAt,
      lastPingAt: liveEventsDiagnostics.lastPingAt,
      statusUpdatedAt,
      lastHttpStatus: liveEventsDiagnostics.lastHttpStatus,
      transportErrorClass: liveEventsDiagnostics.transportErrorClass,
      authSource: liveEventsDiagnostics.authSource,
      apiKeyPresent: liveEventsDiagnostics.apiKeyPresent,
      hydrationState: liveEventsDiagnostics.hydrationState,
      nativeCommandStatus: liveEventsDiagnostics.nativeCommandStatus,
      reconnectAttempts: liveEventsDiagnostics.reconnectAttempts,
      retryMs: liveEventsDiagnostics.retryMs,
      subscribers: liveEventsDiagnostics.subscribers,
      readyState: liveEventsDiagnostics.readyState,
      lastErrorAt: liveEventsDiagnostics.lastErrorAt,
      lastEventId: liveEventsDiagnostics.lastEventId,
    },
    failureKind,
    lastSuccessAt,
    lastFailedAt,
    lastCheckedAt: snapshot.lastCheckedAt,
    currentComputedStateSource,
  };

  return {
    status: failureKind
      ? RUNTIME_HEALTH_STATUSES.DEGRADED
      : RUNTIME_HEALTH_STATUSES.HEALTHY,
    failureKind,
    backendReachable: snapshot.backendReachable,
    chatHealthy: snapshot.chat.derivedHealthy,
    llmHealthy: snapshot.llm.derivedHealthy,
    llmDetail: snapshot.llmDetail,
    liveEventsStatus: connectionStatus,
    lastSuccessAt,
    lastFailedAt,
    lastCheckedAt: snapshot.lastCheckedAt,
    stale,
    diagnostics,
  };
}

export default useRuntimeHealth;
