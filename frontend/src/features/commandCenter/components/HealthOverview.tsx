import * as React from "react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet";

import {
  buildCommandCenterHealthViewModel,
} from "@/features/commandCenter/commandCenterObservability";
import type { CommandCenterHealthItem } from "@/features/commandCenter/types";

type HealthOverviewProps = {
  healthItems: CommandCenterHealthItem[];
  lastCheckedAt: number | null;
  loading: boolean;
  onRefresh: () => Promise<void>;
};

function formatTimestamp(value: number | null): string {
  if (!value) return "Not yet";
  return new Date(value).toLocaleString();
}

function toneStyle(tone: "active" | "attention" | "danger" | "info" | "neutral" | "subtle"): React.CSSProperties {
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
    case "info":
      return {
        background: "var(--info-surface)",
        borderColor: "var(--panel-border)",
        color: "var(--info-text)",
      };
    case "neutral":
      return {
        background: "var(--chip-bg)",
        borderColor: "var(--panel-border)",
        color: "var(--text)",
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
  statusLabel,
  tone,
}: {
  ariaLabelPrefix?: string;
  statusLabel: string;
  tone: "active" | "attention" | "danger" | "info" | "neutral" | "subtle";
}) {
  return (
    <Badge
      aria-label={ariaLabelPrefix ? `${ariaLabelPrefix} ${statusLabel}` : statusLabel}
      className="border text-[11px] font-medium leading-none"
      style={toneStyle(tone)}
    >
      {statusLabel}
    </Badge>
  );
}

function DetailBlock({
  label,
  value,
}: {
  label: string;
  value: string;
}) {
  return (
    <div className="rounded-[var(--tile-radius)] border p-3" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
      <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
        {label}
      </div>
      <div className="mt-1 text-xs leading-5" style={{ color: "var(--text)" }}>
        {value}
      </div>
    </div>
  );
}

export default function HealthOverview({
  healthItems,
  lastCheckedAt,
  loading,
  onRefresh,
}: HealthOverviewProps) {
  const [selectedKey, setSelectedKey] = React.useState<CommandCenterHealthItem["key"] | null>(
    null
  );

  const selectedItem = selectedKey
    ? healthItems.find((item) => item.key === selectedKey) ?? null
    : null;

  React.useEffect(() => {
    if (selectedKey != null && !healthItems.some((item) => item.key === selectedKey)) {
      setSelectedKey(healthItems[0]?.key ?? null);
    }
  }, [healthItems, selectedKey]);

  return (
    <Card
      className="bezel-none border"
      role="region"
      aria-label="Command Center health overview"
      data-testid="command-center-health-overview"
      style={{
        background: "color-mix(in oklab, var(--panel-bg) 96%, transparent)",
        borderColor: "var(--panel-border)",
      }}
    >
      <CardHeader className="flex flex-col gap-3 border-b border-[var(--panel-border)] pb-4 lg:flex-row lg:items-start lg:justify-between">
        <div className="space-y-1">
          <CardTitle className="text-base" style={{ color: "var(--text)" }}>
            Health overview
          </CardTitle>
          <p className="text-sm" style={{ color: "var(--muted)" }}>
            Compact service health with raw responses available in the detail drawer. Last checked:{" "}
            {formatTimestamp(lastCheckedAt)}
          </p>
        </div>
        <Button type="button" variant="ghost" size="sm" onClick={() => void onRefresh()}>
          {loading ? "Refreshing..." : "Refresh"}
        </Button>
      </CardHeader>
      <CardContent className="grid gap-3 p-[var(--card-pad)] md:grid-cols-2 xl:grid-cols-3">
        {healthItems.map((item) => {
          const vm = buildCommandCenterHealthViewModel(item);
          const detailsPreview = item.details
            ? Object.entries(item.details)
                .slice(0, 3)
                .map(([key, value]) => `${key}: ${typeof value === "string" ? value : JSON.stringify(value)}`)
                .join(" · ")
            : item.error ?? "No parsed health detail";

          return (
            <button
              key={item.key}
              type="button"
              className="text-left"
              onClick={() => setSelectedKey(item.key)}
              aria-haspopup="dialog"
            >
              <Card
                className="bezel-none h-full border transition-colors hover:border-[var(--accent)]"
                style={{
                  background:
                    "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
                  borderColor: selectedItem?.key === item.key ? "var(--accent)" : "var(--panel-border)",
                }}
              >
                <CardContent className="space-y-3 p-[var(--card-pad)]">
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0 space-y-1">
                      <div className="text-sm font-semibold leading-5" style={{ color: "var(--text)" }}>
                        {item.label}
                      </div>
                      <div className="text-xs leading-5" style={{ color: "var(--muted)" }}>
                        {item.endpoint}
                      </div>
                    </div>
                    <StatusBadge
                      ariaLabelPrefix={`${item.label} status`}
                      statusLabel={vm.statusLabel}
                      tone={vm.statusTone}
                    />
                  </div>

                  <div className="space-y-1">
                    <div className="text-xs font-medium" style={{ color: "var(--text)" }}>
                      {vm.diagnosis}
                    </div>
                    <div className="text-[11px]" style={{ color: "var(--muted)" }}>
                      Last checked {vm.lastCheckedLabel}
                    </div>
                  </div>

                  <div className="flex items-center justify-between gap-3">
                    <div className="text-xs" style={{ color: "var(--muted)" }}>
                      {vm.action}
                    </div>
                    <Badge className="border text-[11px] font-medium leading-none" style={toneStyle("subtle")}>
                      Inspect
                    </Badge>
                  </div>

                  <div className="rounded-[var(--tile-radius)] border px-3 py-2 text-xs leading-5" style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}>
                    {detailsPreview}
                  </div>
                </CardContent>
              </Card>
            </button>
          );
        })}
      </CardContent>

      <Sheet
        open={Boolean(selectedItem)}
        onOpenChange={(next) => {
          if (!next) setSelectedKey(null);
        }}
      >
        <SheetContent side="right" className="w-[min(92vw,36rem)] overflow-auto">
          {selectedItem ? (
            <>
              <SheetHeader>
                <SheetTitle>Health detail: {selectedItem.label}</SheetTitle>
              </SheetHeader>
              <div className="space-y-3 p-4">
                <DetailBlock label="Endpoint" value={selectedItem.endpoint} />
                <DetailBlock label="Last checked" value={formatTimestamp(selectedItem.checkedAt)} />
                <DetailBlock label="Status" value={buildCommandCenterHealthViewModel(selectedItem).statusLabel} />
                <DetailBlock
                  label="Suggested action"
                  value={buildCommandCenterHealthViewModel(selectedItem).action}
                />

                <div className="rounded-[var(--tile-radius)] border p-3" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                    Parsed health detail
                  </div>
                  <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words text-xs leading-5" style={{ color: "var(--text)" }}>
                    {selectedItem.details
                      ? JSON.stringify(selectedItem.details, null, 2)
                      : "No parsed health detail available."}
                  </pre>
                </div>

                <div className="rounded-[var(--tile-radius)] border p-3" style={{ background: "var(--surface-soft)", borderColor: "var(--panel-border)" }}>
                  <div className="text-[11px] font-semibold uppercase tracking-[0.16em]" style={{ color: "var(--muted)" }}>
                    Raw response
                  </div>
                  <pre className="mt-2 overflow-auto whitespace-pre-wrap break-words text-xs leading-5" style={{ color: "var(--muted)" }}>
                    {selectedItem.raw ?? "No raw payload available."}
                  </pre>
                </div>
              </div>
            </>
          ) : null}
        </SheetContent>
      </Sheet>
    </Card>
  );
}
