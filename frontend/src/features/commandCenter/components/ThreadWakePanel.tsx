import * as React from "react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

/* ------------------------------------------------------------------ */
/*  Types                                                             */
/* ------------------------------------------------------------------ */

export type ThreadWakeStatus = "off" | "observing" | "ready" | "degraded" | "unavailable";

export interface ThreadWakeHealthSnapshot {
  status: ThreadWakeStatus;
  mode: string;
  entryCount: number;
  readyEntries: number;
  staleEntries: number;
  maxEntries: number;
  estimatedMemoryBytes: number;
  maxMemoryBytes: number;
  totalHits: number;
  totalMisses: number;
  totalEvictions: number;
  globalAllowed: boolean;
  backendCapabilities: Record<string, string>;
  entriesByStatus: Record<string, number>;
  entriesByScope: Record<string, number>;
  lastFetchedAt: number | null;
  fetchError: string | null;
}

/* ------------------------------------------------------------------ */
/*  Hook                                                              */
/* ------------------------------------------------------------------ */

const DEFAULT_SNAPSHOT: ThreadWakeHealthSnapshot = {
  status: "unavailable",
  mode: "",
  entryCount: 0,
  readyEntries: 0,
  staleEntries: 0,
  maxEntries: 0,
  estimatedMemoryBytes: 0,
  maxMemoryBytes: 0,
  totalHits: 0,
  totalMisses: 0,
  totalEvictions: 0,
  globalAllowed: false,
  backendCapabilities: {},
  entriesByStatus: {},
  entriesByScope: {},
  lastFetchedAt: null,
  fetchError: null,
};

export function useThreadWakeHealth(
  baseUrl: string | null,
  pollIntervalMs: number = 30_000,
): ThreadWakeHealthSnapshot {
  const [snapshot, setSnapshot] = React.useState<ThreadWakeHealthSnapshot>(DEFAULT_SNAPSHOT);

  React.useEffect(() => {
    if (!baseUrl) {
      setSnapshot((prev) => ({
        ...DEFAULT_SNAPSHOT,
        status: "unavailable",
        fetchError: "No local base URL configured",
        lastFetchedAt: prev.lastFetchedAt,
      }));
      return;
    }

    let cancelled = false;

    async function fetchHealth() {
      try {
        const resp = await fetch(`${baseUrl}/health/threadwake`, {
          signal: AbortSignal.timeout(5_000),
        });
        if (cancelled) return;

        if (!resp.ok) {
          setSnapshot((prev) => ({
            ...prev,
            status: "unavailable",
            fetchError: `HTTP ${resp.status}`,
            lastFetchedAt: Date.now(),
          }));
          return;
        }

        const data = await resp.json();
        if (cancelled) return;

        setSnapshot({
          status: mapStatus(data.status, data.mode),
          mode: data.mode ?? "",
          entryCount: data.entry_count ?? 0,
          readyEntries: data.ready_entries ?? 0,
          staleEntries: data.stale_entries ?? 0,
          maxEntries: data.max_entries ?? 0,
          estimatedMemoryBytes: data.estimated_memory_bytes ?? 0,
          maxMemoryBytes: data.max_memory_bytes ?? 0,
          totalHits: data.total_hits ?? 0,
          totalMisses: data.total_misses ?? 0,
          totalEvictions: data.total_evictions ?? 0,
          globalAllowed: data.global_allowed ?? false,
          backendCapabilities: data.backend_capabilities ?? {},
          entriesByStatus: data.entries_by_status ?? {},
          entriesByScope: data.entries_by_scope ?? {},
          lastFetchedAt: Date.now(),
          fetchError: null,
        });
      } catch {
        if (cancelled) return;
        setSnapshot((prev) => ({
          ...prev,
          status: "unavailable",
          fetchError: "Fetch failed",
          lastFetchedAt: Date.now(),
        }));
      }
    }

    fetchHealth();

    let interval: ReturnType<typeof setInterval> | undefined;
    if (pollIntervalMs > 0) {
      interval = setInterval(fetchHealth, pollIntervalMs);
    }

    return () => {
      cancelled = true;
      if (interval !== undefined) clearInterval(interval);
    };
  }, [baseUrl, pollIntervalMs]);

  return snapshot;
}

function mapStatus(raw: string | undefined, mode: string): ThreadWakeStatus {
  if (!raw || raw === "off") return "off";
  if (raw === "observing") return "observing";
  if (raw === "ready") return "ready";
  if (raw === "degraded") return "degraded";
  // Fallback: derive from mode
  if (mode === "observe") return "observing";
  if (mode === "ephemeral" || mode === "session") return "ready";
  return "off";
}

/* ------------------------------------------------------------------ */
/*  Formatting helpers                                                */
/* ------------------------------------------------------------------ */

function formatBytes(bytes: number): string {
  if (bytes <= 0) return "—";
  const mb = bytes / (1024 * 1024);
  if (mb >= 1024) return `${(mb / 1024).toFixed(1)} GB`;
  return `${mb.toFixed(0)} MB`;
}

function formatHitRate(hits: number, misses: number): string {
  const total = hits + misses;
  if (total === 0) return "—";
  return `${Math.round((hits / total) * 100)}%`;
}

function formatTokens(n: number): string {
  if (n <= 0) return "—";
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`;
  return `${n}`;
}

function statusTone(status: ThreadWakeStatus): "active" | "attention" | "danger" | "subtle" {
  switch (status) {
    case "ready":
      return "active";
    case "observing":
      return "attention";
    case "degraded":
      return "attention";
    case "off":
      return "subtle";
    case "unavailable":
    default:
      return "danger";
  }
}

function toneStyle(
  tone: "active" | "attention" | "danger" | "subtle",
): React.CSSProperties {
  switch (tone) {
    case "active":
      return {
        background: "var(--accent-weak)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 35%, var(--panel-border))",
        color: "var(--text-on-accent)",
      };
    case "attention":
      return {
        background: "color-mix(in oklab, var(--chip-bg) 82%, var(--accent-strong) 18%)",
        borderColor: "color-mix(in oklab, var(--accent-strong) 42%, var(--panel-border))",
        color: "var(--text)",
      };
    case "danger":
      return {
        background: "var(--danger-surface)",
        borderColor: "var(--danger-border)",
        color: "var(--danger-text)",
      };
    case "subtle":
    default:
      return {
        background: "var(--surface-soft)",
        borderColor: "var(--panel-border)",
        color: "var(--muted)",
      };
  }
}

/* ------------------------------------------------------------------ */
/*  Component                                                         */
/* ------------------------------------------------------------------ */

export interface ThreadWakePanelProps {
  baseUrl: string | null;
  /** Set to true to hide the panel when unavailable (default: show with "Unavailable" badge). */
  hideWhenUnavailable?: boolean;
  pollIntervalMs?: number;
}

export default function ThreadWakePanel({
  baseUrl,
  hideWhenUnavailable = false,
  pollIntervalMs,
}: ThreadWakePanelProps) {
  const health = useThreadWakeHealth(baseUrl, pollIntervalMs);

  if (hideWhenUnavailable && health.status === "unavailable") {
    return null;
  }

  const tone = statusTone(health.status);
  const hitRate = formatHitRate(health.totalHits, health.totalMisses);
  const memoryStr = formatBytes(health.estimatedMemoryBytes);

  return (
    <Card
      className="bezel-none border"
      role="region"
      aria-label="ThreadWake cache status"
      data-testid="threadwake-panel"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="pb-3">
        <CardTitle
          className="text-base"
          style={{ color: "var(--text)" }}
          title="ThreadWake reuses compatible computed prompt-prefix state for supported local models. It is a runtime optimization, not long-term memory."
        >
          ThreadWake Cache
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {/* Status row */}
        <div className="flex items-center justify-between">
          <span className="text-sm" style={{ color: "var(--muted)" }}>
            Status
          </span>
          <Badge
            aria-label={`ThreadWake status ${health.status}`}
            className="border text-[11px] font-medium leading-none"
            style={toneStyle(tone)}
          >
            {health.status === "unavailable" ? "Unavailable" : health.status.toUpperCase()}
          </Badge>
        </div>

        {/* Mode */}
        {health.mode && health.status !== "unavailable" && health.status !== "off" ? (
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              Mode
            </span>
            <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
              {health.mode}
            </span>
          </div>
        ) : null}

        {/* Hit rate */}
        {health.totalHits + health.totalMisses > 0 ? (
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              Cache Hit Rate
            </span>
            <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
              {hitRate}
            </span>
          </div>
        ) : null}

        {/* Ready entries */}
        {health.readyEntries > 0 ? (
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              Ready Entries
            </span>
            <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
              {health.readyEntries} / {health.maxEntries}
            </span>
          </div>
        ) : null}

        {/* Memory */}
        {health.estimatedMemoryBytes > 0 ? (
          <div className="flex items-center justify-between">
            <span className="text-sm" style={{ color: "var(--muted)" }}>
              Est. Memory
            </span>
            <span className="text-sm font-medium" style={{ color: "var(--text)" }}>
              {memoryStr}
            </span>
          </div>
        ) : null}

        {/* Error */}
        {health.fetchError ? (
          <div
            className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs"
            style={{
              background: "var(--danger-surface)",
              borderColor: "var(--danger-border)",
              color: "var(--danger-text)",
            }}
          >
            {health.fetchError}
          </div>
        ) : null}

        {/* Tooltip footer */}
        <p className="text-[11px] leading-4" style={{ color: "var(--muted)" }}>
          ThreadWake reuses compatible computed prompt-prefix state for supported local
          models. It is a runtime optimization, not long-term memory.
        </p>
      </CardContent>
    </Card>
  );
}
