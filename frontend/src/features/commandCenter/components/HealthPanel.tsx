import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

import type { CommandCenterHealthItem } from "@/features/commandCenter/types";
import { describeCommandCenterHealthStatePresentation } from "@/features/commandCenter/types";

type HealthPanelProps = {
  healthItems: CommandCenterHealthItem[];
  lastCheckedAt: number | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
};

type BadgeTone = "active" | "attention" | "danger" | "subtle";

const sectionSurfaceStyle: React.CSSProperties = {
  background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

const tileSurfaceStyle: React.CSSProperties = {
  background: "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

const rawSurfaceStyle: React.CSSProperties = {
  background: "var(--surface-soft)",
  borderColor: "var(--panel-border)",
  borderRadius: "var(--tile-radius)",
};

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function badgeToneStyle(tone: BadgeTone): React.CSSProperties {
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

function StatusBadge({
  ariaLabelPrefix,
  status,
}: {
  ariaLabelPrefix?: string;
  status: CommandCenterHealthItem["status"];
}) {
  const presentation = describeCommandCenterHealthStatePresentation(status);
  return (
    <Badge
      aria-label={
        ariaLabelPrefix ? `${ariaLabelPrefix} ${presentation.label}` : presentation.label
      }
      className="border text-[11px] font-medium leading-none"
      style={badgeToneStyle(presentation.tone as BadgeTone)}
    >
      {presentation.label}
    </Badge>
  );
}

function HealthRawDetails({ item }: { item: CommandCenterHealthItem }) {
  const detailText = item.details
    ? JSON.stringify(item.details, null, 2)
    : item.raw ?? "No raw payload available.";

  return (
    <div className="mt-3 space-y-2">
      <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
        <div
          className="text-[11px] font-semibold uppercase tracking-[0.16em]"
          style={{ color: "var(--muted)" }}
        >
          Checked
        </div>
        <div className="text-xs leading-5" style={{ color: "var(--text)" }}>
          {formatTimestamp(item.checkedAt)}
        </div>
      </div>
      {item.httpStatus != null ? (
        <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: "var(--muted)" }}
          >
            HTTP status
          </div>
          <div className="text-xs leading-5" style={{ color: "var(--text)" }}>
            {item.httpStatus}
          </div>
        </div>
      ) : null}
      {item.error ? (
        <div className="rounded-[var(--tile-radius)] border p-3" style={rawSurfaceStyle}>
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.16em]"
            style={{ color: "var(--muted)" }}
          >
            Error
          </div>
          <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
            {item.error}
          </div>
        </div>
      ) : null}
      <pre
        className="overflow-x-auto rounded-[var(--tile-radius)] border p-3 text-[11px] leading-5"
        style={{
          ...rawSurfaceStyle,
          color: "var(--muted)",
        }}
      >
        {detailText}
      </pre>
    </div>
  );
}

export default function HealthPanel({
  healthItems,
  lastCheckedAt,
  loading,
  onRefresh,
}: HealthPanelProps) {
  return (
    <Card
      className="bezel-none border"
      role="region"
      aria-label="Command Center health strip"
      data-testid="command-center-health-strip"
      style={sectionSurfaceStyle}
    >
      <CardHeader className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base" style={{ color: "var(--text)" }}>
            Health
          </CardTitle>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Per-endpoint snapshots from the current health checks. Last checked:{" "}
            {formatTimestamp(lastCheckedAt)}
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => void onRefresh()}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {healthItems.map((item) => (
          <Card
            key={item.key}
            className="bezel-none border"
            data-testid={`command-center-health-${item.key}`}
            style={tileSurfaceStyle}
          >
            <CardContent className="space-y-3 p-[var(--card-pad)]">
              <div className="flex flex-col gap-2 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
                    {item.label}
                  </div>
                  <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                    {item.endpoint}
                  </div>
                </div>
                <StatusBadge ariaLabelPrefix={`${item.label} status`} status={item.status} />
              </div>

              <details className="text-xs" style={{ color: "var(--muted)" }}>
                <summary className="cursor-pointer text-[11px] font-semibold uppercase tracking-[0.16em]">
                  Inspect raw details
                </summary>
                <HealthRawDetails item={item} />
              </details>
            </CardContent>
          </Card>
        ))}
      </CardContent>
    </Card>
  );
}
