import { Loader2 } from "lucide-react";

import type { InferenceRequestState } from "@/types/inference";

type InferenceStatusBannerProps = {
  state: InferenceRequestState;
  onCancel?: () => void;
  onSwitchToFast?: () => void;
};

function isVisiblePhase(phase: InferenceRequestState["phase"]): boolean {
  return phase !== "idle";
}

export function InferenceStatusBanner({
  state,
  onCancel,
  onSwitchToFast,
}: InferenceStatusBannerProps) {
  if (!isVisiblePhase(state.phase)) {
    return null;
  }

  const isActive =
    state.phase === "sending" ||
    state.phase === "thinking" ||
    state.phase === "streaming";

  const tone =
    state.phase === "failed"
      ? "rgba(248, 113, 113, 0.22)"
      : state.phase === "cancelled"
        ? "rgba(148, 163, 184, 0.18)"
        : "rgba(245, 158, 11, 0.22)";

  return (
    <div
      className="relative overflow-hidden rounded-xl border px-3 py-2"
      style={{
        borderColor: "color-mix(in oklab, var(--panel-border) 80%, transparent)",
        background:
          "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 90%, transparent)",
        color: "var(--text)",
      }}
      aria-live="polite"
    >
      <div
        className={`absolute inset-x-0 top-0 h-px ${isActive ? "animate-pulse" : ""}`}
        style={{
          background: `linear-gradient(90deg, transparent, ${tone}, transparent)`,
        }}
      />
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <div className="flex items-center gap-2 text-[12px] font-medium">
            {isActive ? (
              <Loader2 className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <span
                className="inline-block h-2 w-2 rounded-full"
                style={{
                  background:
                    state.phase === "failed"
                      ? "rgb(248 113 113)"
                      : state.phase === "cancelled"
                        ? "rgb(148 163 184)"
                        : "rgb(16 185 129)",
                }}
              />
            )}
            <span>{state.statusText ?? "Working…"}</span>
          </div>
          {state.detailText ? (
            <div className="mt-1 text-[11px]" style={{ color: "var(--muted)" }}>
              {state.detailText}
            </div>
          ) : null}
          {state.errorText ? (
            <div className="mt-1 text-[11px]" style={{ color: "rgb(248 113 113)" }}>
              {state.errorText}
            </div>
          ) : null}
        </div>
        {(state.canCancel || state.canSwitchToFast) && (
          <div className="flex shrink-0 items-center gap-2">
            {state.canCancel && onCancel ? (
              <button
                type="button"
                onClick={onCancel}
                disabled={state.isPendingCancel}
                className="rounded-md border px-2 py-1 text-[11px] transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-45"
                style={{
                  borderColor: "var(--panel-border)",
                  color: "var(--text)",
                }}
              >
                {state.isPendingCancel ? "Stopping…" : "Stop"}
              </button>
            ) : null}
            {state.canSwitchToFast && onSwitchToFast ? (
              <button
                type="button"
                onClick={onSwitchToFast}
                disabled={state.isPendingCancel}
                className="rounded-md border px-2 py-1 text-[11px] transition-opacity hover:opacity-95 disabled:cursor-not-allowed disabled:opacity-45"
                style={{
                  borderColor: "var(--panel-border)",
                  color: "var(--text)",
                }}
              >
                Switch to Fast
              </button>
            ) : null}
          </div>
        )}
      </div>
    </div>
  );
}

export default InferenceStatusBanner;
