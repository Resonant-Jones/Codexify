import * as React from "react";

import {
  buildAuthenticatedFetchInit,
  getBackendOutageRemainingMs,
} from "@/lib/api";
import {
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
    : resolveBackendUrl(item.path);
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

function classifyStatus(data: Record<string, unknown> | null): CommandCenterHealthStatus {
  if (!data) return "UNKNOWN";
  const status = String(data.status ?? "")
    .trim()
    .toLowerCase();
  if (data.ok === true || status === "ok" || status === "online") {
    return "OK";
  }
  if (
    data.ok === false ||
    ["error", "offline", "misconfigured", "fail", "failed"].includes(status)
  ) {
    return "FAIL";
  }
  return "UNKNOWN";
}

function createDefaultItems(): CommandCenterHealthItem[] {
  return HEALTH_DEFINITIONS.map((definition) => ({
    checkedAt: null,
    endpoint: resolveHealthUrl(definition, 0),
    error: null,
    httpStatus: null,
    key: definition.key,
    label: definition.label,
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

      const contentType = response.headers.get("content-type") || "";
      const body = contentType.includes("application/json")
        ? await response.json().catch(() => null)
        : await response.text().catch(() => null);
      const record = asRecord(body);
      const status = response.ok ? classifyStatus(record) : "FAIL";

      if (response.status === 404 && index < definition.paths.length - 1) {
        continue;
      }

      return {
        checkedAt: Date.now(),
        endpoint: url,
        error: response.ok ? null : `HTTP ${response.status}`,
        httpStatus: response.status,
        key: definition.key,
        label: definition.label,
        raw: toRaw(body),
        status,
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
        raw: toRaw(message),
        status: "FAIL",
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
    raw: null,
    status: "FAIL",
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
          status: "FAIL",
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
