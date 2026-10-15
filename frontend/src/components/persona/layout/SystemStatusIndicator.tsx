import { AlertTriangle, CheckCircle2, CircleAlert } from "lucide-react";
import React, { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";

export type SystemStatusTone =
  | "healthy"
  | "attention"
  | "critical"
  | "checking";

export type SystemStatusRow = {
  label: string;
  status: string;
  tone: SystemStatusTone;
};

export type SystemStatusIssue = {
  title: string;
  detail: string;
  guidance?: string;
  badge?: string;
};

type SystemStatusIndicatorProps = {
  level: SystemStatusTone;
  issue: SystemStatusIssue | null;
  rows: SystemStatusRow[];
  diagnostics?: string[];
  isPhoneShell?: boolean;
};

type OverlayPosition = {
  top: number;
  right: number;
  maxHeight: number;
  themeVars: React.CSSProperties;
};

const OVERLAY_GAP_PX = 9;
const OVERLAY_VIEWPORT_MARGIN_PX = 16;
const OVERLAY_MAX_HEIGHT_PX = 576;

function readOverlayThemeVars(anchor: HTMLElement): React.CSSProperties {
  if (typeof window === "undefined") return {};
  const computed = window.getComputedStyle(anchor);
  return {
    "--panel-border": computed.getPropertyValue("--panel-border").trim(),
    "--panel-bg": computed.getPropertyValue("--panel-bg").trim(),
    "--text": computed.getPropertyValue("--text").trim(),
    "--muted": computed.getPropertyValue("--muted").trim(),
    "--shell-overlay-z": computed.getPropertyValue("--shell-overlay-z").trim(),
    fontFamily: computed.fontFamily,
    colorScheme: computed.colorScheme,
  } as React.CSSProperties;
}

function measureOverlayPosition(anchor: HTMLElement, isPhoneShell: boolean): OverlayPosition {
  const rect = anchor.getBoundingClientRect();
  const rootFontSize = parseFloat(window.getComputedStyle(document.documentElement).fontSize) || 16;
  const panelWidth = Math.min(
    (isPhoneShell ? 23 : 24) * rootFontSize,
    window.innerWidth - 2 * OVERLAY_VIEWPORT_MARGIN_PX
  );
  const top = Math.min(
    rect.bottom + OVERLAY_GAP_PX,
    window.innerHeight - OVERLAY_VIEWPORT_MARGIN_PX
  );
  return {
    top,
    right: Math.max(
      OVERLAY_VIEWPORT_MARGIN_PX,
      Math.min(
        window.innerWidth - rect.right,
        window.innerWidth - panelWidth - OVERLAY_VIEWPORT_MARGIN_PX
      )
    ),
    maxHeight: Math.max(
      0,
      Math.min(
        OVERLAY_MAX_HEIGHT_PX,
        window.innerHeight - top - OVERLAY_VIEWPORT_MARGIN_PX
      )
    ),
    themeVars: readOverlayThemeVars(anchor),
  };
}

const STATUS_COLOR: Record<SystemStatusTone, string> = {
  healthy: "#4ade80",
  attention: "#f59e0b",
  critical: "#fb7185",
  checking: "#94a3b8",
};

const STATUS_LABEL: Record<SystemStatusTone, string> = {
  healthy: "Healthy",
  attention: "Needs attention",
  critical: "Action required",
  checking: "Checking",
};

function StatusGlyph({ tone }: { tone: SystemStatusTone }) {
  if (tone === "critical") {
    return <CircleAlert className="h-4 w-4" aria-hidden="true" />;
  }
  if (tone === "attention") {
    return <AlertTriangle className="h-4 w-4" aria-hidden="true" />;
  }
  return <CheckCircle2 className="h-4 w-4" aria-hidden="true" />;
}

export default function SystemStatusIndicator({
  level,
  issue,
  rows,
  diagnostics = [],
  isPhoneShell = false,
}: SystemStatusIndicatorProps) {
  const [open, setOpen] = useState(false);
  const [overlayPosition, setOverlayPosition] = useState<OverlayPosition | null>(null);
  const rootRef = useRef<HTMLDivElement | null>(null);
  const panelRef = useRef<HTMLElement | null>(null);
  const statusColor = STATUS_COLOR[level];

  useEffect(() => {
    if (!open) return undefined;

    const updateOverlayPosition = () => {
      const anchor = rootRef.current;
      if (!anchor || typeof window === "undefined") return;
      setOverlayPosition(measureOverlayPosition(anchor, isPhoneShell));
    };

    const handlePointerDown = (event: PointerEvent) => {
      const target = event.target;
      if (!(target instanceof Node)) return;
      if (
        !rootRef.current?.contains(target) &&
        !panelRef.current?.contains(target)
      ) {
        setOpen(false);
      }
    };
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setOpen(false);
      }
    };

    document.addEventListener("pointerdown", handlePointerDown);
    document.addEventListener("keydown", handleKeyDown);
    window.addEventListener("resize", updateOverlayPosition);
    window.addEventListener("scroll", updateOverlayPosition, true);
    const resizeObserver =
      typeof ResizeObserver === "undefined" || !rootRef.current
        ? null
        : new ResizeObserver(updateOverlayPosition);
    resizeObserver?.observe(rootRef.current);
    return () => {
      document.removeEventListener("pointerdown", handlePointerDown);
      document.removeEventListener("keydown", handleKeyDown);
      window.removeEventListener("resize", updateOverlayPosition);
      window.removeEventListener("scroll", updateOverlayPosition, true);
      resizeObserver?.disconnect();
    };
  }, [open, isPhoneShell]);

  const healthySummary =
    level === "checking"
      ? {
          title: "Checking system health",
          detail: "Codexify is still collecting the current runtime state.",
        }
      : {
          title: "Everything is working normally",
          detail: "Guardian, provider health, and live updates are operating normally.",
        };
  const summary = issue ?? healthySummary;

  const statusPanel =
    open && typeof document !== "undefined"
      ? createPortal(
          <section
            ref={panelRef}
            id="codexify-system-status-panel"
            data-testid="system-status-panel"
            aria-label="System status"
            className="overflow-auto rounded-[20px] border p-3 text-left shadow-2xl"
            style={{
              ...overlayPosition?.themeVars,
              position: "fixed",
              top: overlayPosition?.top ?? 0,
              right: overlayPosition?.right ?? OVERLAY_VIEWPORT_MARGIN_PX,
              zIndex: "var(--shell-overlay-z, 2000)",
              visibility: overlayPosition ? "visible" : "hidden",
              width: isPhoneShell
                ? "min(23rem, calc(100vw - 2rem))"
                : "min(24rem, calc(100vw - 2rem))",
              maxHeight: overlayPosition?.maxHeight ?? OVERLAY_MAX_HEIGHT_PX,
              borderColor: "color-mix(in oklab, var(--panel-border) 88%, white 12%)",
              background:
                "color-mix(in oklab, var(--panel-bg) 94%, rgba(4,8,14,0.94) 6%)",
              color: "var(--text)",
              backdropFilter: "blur(24px) saturate(135%)",
              WebkitBackdropFilter: "blur(24px) saturate(135%)",
              boxShadow:
                "0 22px 60px rgba(0,0,0,0.42), inset 0 1px 0 rgba(255,255,255,0.08)",
            }}
          >
            <div className="flex items-center justify-between gap-3 px-1 pb-3">
              <h2 className="text-sm font-semibold tracking-wide">System status</h2>
              <span
                className="inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.08em]"
                style={{
                  borderColor: `color-mix(in oklab, ${statusColor} 38%, transparent)`,
                  background: `color-mix(in oklab, ${statusColor} 12%, transparent)`,
                  color: statusColor,
                }}
              >
                <StatusGlyph tone={level} />
                {STATUS_LABEL[level]}
              </span>
            </div>

            <div
              className="rounded-[16px] border px-4 py-3"
              style={{
                borderColor:
                  level === "healthy" || level === "checking"
                    ? "var(--panel-border)"
                    : `color-mix(in oklab, ${statusColor} 58%, var(--panel-border))`,
                background:
                  level === "healthy" || level === "checking"
                    ? "rgba(255,255,255,0.035)"
                    : `color-mix(in oklab, ${statusColor} 8%, rgba(255,255,255,0.025))`,
              }}
            >
              <div className="flex items-start gap-3">
                <span
                  className="mt-0.5 inline-flex h-8 w-8 shrink-0 items-center justify-center rounded-[10px]"
                  style={{
                    background: `color-mix(in oklab, ${statusColor} 14%, transparent)`,
                    color: statusColor,
                  }}
                >
                  <StatusGlyph tone={level} />
                </span>
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="text-sm font-semibold">{summary.title}</p>
                    {issue?.badge ? (
                      <span
                        className="rounded-full border px-2 py-0.5 text-[9px] font-semibold uppercase tracking-[0.08em]"
                        style={{
                          borderColor: "var(--panel-border)",
                          color: "var(--muted)",
                          background: "rgba(255,255,255,0.035)",
                        }}
                      >
                        {issue.badge}
                      </span>
                    ) : null}
                  </div>
                  <p
                    className="mt-1 text-[12px] leading-5"
                    style={{ color: "var(--muted)" }}
                  >
                    {summary.detail}
                  </p>
                  {issue?.guidance ? (
                    <p className="mt-2 text-[12px] leading-5 opacity-90">
                      {issue.guidance}
                    </p>
                  ) : null}
                </div>
              </div>
            </div>

            <div className="mt-3 divide-y divide-white/5">
              {rows.map((row) => (
                <div
                  key={row.label}
                  className="flex items-center justify-between gap-4 px-1 py-2.5 text-[12px]"
                >
                  <span className="font-medium">{row.label}</span>
                  <span
                    className="inline-flex items-center gap-2"
                    style={{ color: "var(--muted)" }}
                  >
                    <span
                      aria-hidden="true"
                      className="h-2 w-2 rounded-full"
                      style={{ background: STATUS_COLOR[row.tone] }}
                    />
                    {row.status}
                  </span>
                </div>
              ))}
            </div>

            {diagnostics.length > 0 ? (
              <details
                className="mt-2 border-t pt-2"
                style={{ borderColor: "var(--panel-border)" }}
              >
                <summary className="cursor-pointer select-none px-1 py-2 text-[12px] font-medium">
                  Technical details
                </summary>
                <div
                  className="mt-1 max-h-48 overflow-auto rounded-[12px] border px-3 py-2 font-mono text-[10px] leading-5"
                  style={{
                    borderColor: "var(--panel-border)",
                    background: "rgba(0,0,0,0.18)",
                    color: "var(--muted)",
                  }}
                >
                  {diagnostics.map((line) => (
                    <div key={line}>{line}</div>
                  ))}
                </div>
              </details>
            ) : null}
          </section>,
          document.body
        )
      : null;

  return (
    <div ref={rootRef} className="relative shrink-0" data-testid="system-status-control">
      <button
        type="button"
        data-testid="system-status-toggle"
        aria-label={`System status: ${STATUS_LABEL[level]}`}
        aria-expanded={open}
        aria-controls="codexify-system-status-panel"
        title={`System status: ${STATUS_LABEL[level]}`}
        onClick={() => {
          if (open) {
            setOpen(false);
            return;
          }
          if (rootRef.current && typeof window !== "undefined") {
            setOverlayPosition(measureOverlayPosition(rootRef.current, isPhoneShell));
          }
          setOpen(true);
        }}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-full border border-transparent transition-[background,border-color,transform] hover:border-[color:var(--chip-border)] hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/30"
      >
        <span
          aria-hidden="true"
          className="block h-2.5 w-2.5 rounded-full"
          style={{
            background: statusColor,
            boxShadow:
              level === "healthy"
                ? "0 0 0 1px rgba(74,222,128,0.18)"
                : `0 0 0 1px color-mix(in oklab, ${statusColor} 40%, transparent), 0 0 12px color-mix(in oklab, ${statusColor} 45%, transparent)`,
          }}
        />
      </button>
      {statusPanel}
    </div>
  );
}
