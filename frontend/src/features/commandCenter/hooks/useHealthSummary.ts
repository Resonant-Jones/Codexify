import * as React from "react";

import {
  buildAuthenticatedFetchInit,
  getBackendOutageRemainingMs,
} from "@/lib/api";
import {
  getRuntimeConfigSync,
  resolveApiUrl,
  resolveBackendUrl,
} from "@/lib/runtimeConfig";

import type {
  CommandCenterHealthItem,
  CommandCenterHealthStatus,
} from "@/features/commandCenter/types";

const POLL_INTERVAL_MS = 5_000;

type UseHealthSummaryOptions = {
  enabled: boolean;
};

type UseHealthSummaryResult = {
  healthItems: CommandCenterHealthItem[];
  lastCheckedAt: number | null;
  loading: boolean;
  refresh: () => Promise<void>;
};

type HealthDefinition = {
  key: CommandCenterHealthItem["key"];
  label: string;
  paths: Array<{
    path: string;
    resolver: "api" | "backend";
  }>;
};

type HealthInterpretation = {
  details: Record<string, unknown> | null;
  error: string | null;
  raw: string | null;
  status: CommandCenterHealthStatus;
};

const HEALTH_DEFINITIONS: HealthDefinition[] = [
  {
    key: "core",
    label: "Core",
    paths: [{ path: "/health", resolver: "backend" }],
  },
  {
    key: "llm",
    label: "LLM",
    paths: [
      { path: "/health/llm", resolver: "backend" },
      { path: "/api/health/llm", resolver: "api" },
    ],
  },
  {
    key: "deps",
    label: "Deps",
    paths: [{ path: "/health/deps", resolver: "backend" }],
  },
  {
    key: "vector",
    label: "Vector",
    paths: [{ path: "/health/vector", resolver: "backend" }],
  },
  {
    key: "memory",
    label: "Memory",
    paths: [{ path: "/health/memory", resolver: "backend" }],
  },
];

function resolveHealthUrl(definition: HealthDefinition, index: number): string {
  const item = definition.paths[index];
  return item.resolver === "api"
    ? resolveApiUrl(item.path)
    : resolveBackendHealthUrl(item.path);
}

function resolveBackendHealthUrl(path: string): string {
  const runtimeConfig = getRuntimeConfigSync();
  const normalizedPath = path.startsWith("/") ? path : `/${path}`;
  if (
    runtimeConfig.backendBaseUrl &&
    /^https?:\/\//i.test(runtimeConfig.backendBaseUrl)
  ) {
    return resolveBackendUrl(normalizedPath, runtimeConfig);
  }

  const viteEnv =
    typeof import.meta !== "undefined" ? ((import.meta as any).env ?? {}) : {};
  const candidate = String(
    viteEnv.VITE_PROXY_TARGET ?? viteEnv.VITE_BACKEND_URL ?? ""
  ).trim();
  if (/^https?:\/\//i.test(candidate)) {
    return `${candidate.replace(/\/+$/, "")}${normalizedPath}`;
  }

  return `http://127.0.0.1:8888${normalizedPath}`;
}

function toRaw(value: unknown): string | null {
  if (value == null) return null;
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || null;
  }
  try {
    return JSON.stringify(value, null, 2);
  } catch {
    return String(value);
  }
}

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function normalizeHealthStatus(
  rawStatus: string | null | undefined
): CommandCenterHealthStatus {
  const token = String(rawStatus ?? "")
    .trim()
    .toLowerCase();
  if (!token) return "UNKNOWN";
  if (["ok", "healthy", "online"].includes(token)) {
    return "OK";
  }
  if (["degraded", "warning", "stale", "unknown"].includes(token)) {
    return "DEGRADED";
  }
  if (
    [
      "down",
      "offline",
      "unhealthy",
      "error",
      "fail",
      "failed",
      "misconfigured",
      "dependency_unavailable",
    ].includes(token)
  ) {
    return "DOWN";
  }
  return "UNKNOWN";
}

function readHealthStatus(data: Record<string, unknown> | null): string | null {
  if (!data) return null;
  return firstString(
    data.status,
    asRecord(data.details)?.status,
    asRecord(data.health)?.status
  );
}

function classifyStatus(
  data: Record<string, unknown> | null
): CommandCenterHealthStatus {
  if (!data) return "UNKNOWN";
  const directStatus = readHealthStatus(data);
  const normalized = normalizeHealthStatus(directStatus);
  if (normalized !== "UNKNOWN") {
    return normalized;
  }

  if (data.ok === true || asRecord(data.details)?.ok === true) {
    return "OK";
  }
  if (data.ok === false || asRecord(data.details)?.ok === false) {
    return "DOWN";
  }

  return "UNKNOWN";
}

export function interpretHealthPayload(rawText: string): HealthInterpretation {
  const trimmed = rawText.trim();
  if (!trimmed) {
    return {
      details: null,
      error: "Invalid health response",
      raw: null,
      status: "UNKNOWN",
    };
  }

  if (/^<!doctype html>/i.test(trimmed) || /^<html[\s>]/i.test(trimmed)) {
    return {
      details: null,
      error: "Invalid health response",
      raw: trimmed,
      status: "UNKNOWN",
    };
  }

  const parsed = asRecord(parseJson(trimmed));
  if (!parsed) {
    return {
      details: null,
      error: "Invalid health response",
      raw: trimmed,
      status: "UNKNOWN",
    };
  }

  return {
    details: parsed,
    error: null,
    raw: JSON.stringify(parsed, null, 2),
    status: classifyStatus(parsed),
  };
}

function parseJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return null;
  }
}

function createDefaultItems(): CommandCenterHealthItem[] {
  return HEALTH_DEFINITIONS.map((definition) => ({
    checkedAt: null,
    endpoint: resolveHealthUrl(definition, 0),
    error: null,
    httpStatus: null,
    key: definition.key,
    label: definition.label,
    details: null,
    raw: null,
    status: "UNKNOWN",
  }));
}

async function fetchHealthItem(
  definition: HealthDefinition
): Promise<CommandCenterHealthItem> {
  const authInit = buildAuthenticatedFetchInit({
    headers: {
      Accept: "application/json, text/plain, */*",
      "Cache-Control": "no-cache",
    },
  });

  for (let index = 0; index < definition.paths.length; index += 1) {
    const url = resolveHealthUrl(definition, index);
    try {
      const response = await fetch(url, {
        ...authInit,
        method: "GET",
      });

      const rawText = await response.text().catch(() => "");
      const interpretation = interpretHealthPayload(rawText);

      if (response.status === 404 && index < definition.paths.length - 1) {
        continue;
      }

      if (
        interpretation.status === "UNKNOWN" &&
        interpretation.error &&
        index < definition.paths.length - 1
      ) {
        continue;
      }

      return {
        checkedAt: Date.now(),
        endpoint: url,
        details: interpretation.details,
        error: interpretation.error ?? (response.ok ? null : `HTTP ${response.status}`),
        httpStatus: response.status,
        key: definition.key,
        label: definition.label,
        raw: interpretation.raw ?? toRaw(rawText),
        status: interpretation.status,
      };
    } catch (error) {
      if (index < definition.paths.length - 1) {
        continue;
      }
      const message =
        error instanceof Error && error.message.trim()
          ? error.message
          : "Request failed";
      return {
        checkedAt: Date.now(),
        endpoint: url,
        error: message,
        httpStatus: null,
        key: definition.key,
        label: definition.label,
        details: null,
        raw: toRaw(message),
        status: "DOWN",
      };
    }
  }

  return {
    checkedAt: Date.now(),
    endpoint: resolveHealthUrl(definition, definition.paths.length - 1),
    error: "Request failed",
    httpStatus: null,
    key: definition.key,
    label: definition.label,
    details: null,
    raw: null,
    status: "DOWN",
  };
}

export function useHealthSummary(
  options: UseHealthSummaryOptions
): UseHealthSummaryResult {
  const { enabled } = options;
  const [healthItems, setHealthItems] = React.useState<CommandCenterHealthItem[]>(
    () => createDefaultItems()
  );
  const [lastCheckedAt, setLastCheckedAt] = React.useState<number | null>(null);
  const [loading, setLoading] = React.useState(false);

  const refresh = React.useCallback(async () => {
    if (!enabled) {
      setHealthItems(createDefaultItems());
      setLastCheckedAt(null);
      setLoading(false);
      return;
    }

    if (getBackendOutageRemainingMs() > 0) {
      setHealthItems((previous) =>
        previous.map((item) => ({
          ...item,
          checkedAt: Date.now(),
          error: "Backend outage fuse active",
          raw: "Backend outage fuse active",
          status: "DOWN",
        }))
      );
      setLastCheckedAt(Date.now());
      return;
    }

    setLoading(true);
    try {
      const nextItems = await Promise.all(
        HEALTH_DEFINITIONS.map((definition) => fetchHealthItem(definition))
      );
      setHealthItems(nextItems);
      setLastCheckedAt(Date.now());
    } finally {
      setLoading(false);
    }
  }, [enabled]);

  React.useEffect(() => {
    void refresh();
    if (!enabled) return;
    const timer = window.setInterval(() => {
      void refresh();
    }, POLL_INTERVAL_MS);
    return () => {
      window.clearInterval(timer);
    };
  }, [enabled, refresh]);

  return {
    healthItems,
    lastCheckedAt,
    loading,
    refresh,
  };
}

export default useHealthSummary;
