import { Loader2 } from "lucide-react";

import type { InferenceRequestState } from "@/types/inference";

type InferenceStatusBannerProps = {
  state: InferenceRequestState;
  onCancel?: () => void;
  onSwitchToFast?: () => void;
  isPhoneShell?: boolean;
};

function isVisibleState(state: InferenceRequestState): boolean {
  return (
    state.phase === "sending" ||
    state.phase === "thinking" ||
    state.phase === "streaming" ||
    state.phase === "failed" ||
    state.phase === "cancelled" ||
    (state.phase === "completed" && (state.latencyMetrics?.length ?? 0) > 0)
  );
}

export function InferenceStatusBanner({
  state,
  onCancel,
  onSwitchToFast,
  isPhoneShell = false,
}: InferenceStatusBannerProps) {
  if (!isVisibleState(state)) {
    return null;
  }

  const isActive =
    state.phase === "sending" ||
    state.phase === "thinking" ||
    state.phase === "streaming";

  const isPendingStop = state.isPendingCancel;
  // The canonical lifecycle stage ("Queued…", "Warming model…",
  // "Waiting for first token…", "Provider degraded…") is already computed by
  // the request state machine. On a phone the banner is the request-state
  // surface, so it names that stage instead of collapsing queue, model
  // warmup, and first-token wait into a single "Working…".
  const canonicalStageLabel = state.statusText?.trim() ?? "";
  const label = (() => {
    if (isPendingStop) return "Stopping…";
    if (state.phase === "failed") return "Reply failed";
    if (state.phase === "cancelled") return "Reply stopped";
    if (state.phase === "completed") return "Completed";
    if (isPhoneShell && canonicalStageLabel) return canonicalStageLabel;
    if (state.phase === "sending") return "Working…";
    if (state.phase === "thinking") return "Thinking…";
    if (state.phase === "streaming") return "Replying…";
    if (state.statusText) return state.statusText;
    return state.statusText ?? "Working…";
  })();

  const isActiveLifecycleDiagnostic =
    typeof state.detailText === "string" &&
    (/still (waiting|warming up|streaming)/i.test(state.detailText) ||
      /stop request could not be confirmed/i.test(state.detailText));
  const detail =
    !isActive || isActiveLifecycleDiagnostic
      ? state.detailText ?? (state.phase === "failed" ? state.errorText : null)
      : null;

  const tone =
    state.phase === "failed"
      ? "rgb(248 113 113)"
      : state.phase === "cancelled"
        ? "rgb(148 163 184)"
        : "var(--muted)";

  return (
    <div className="flex items-start justify-between gap-3" aria-live="polite">
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2 text-[11px]">
          {isActive ? (
            <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin" style={{ color: tone }} />
          ) : (
            <span
              className="inline-block h-1.5 w-1.5 shrink-0 rounded-full"
              style={{ background: tone }}
            />
          )}
          <span className="truncate font-medium" style={{ color: "var(--text)" }}>
            {label}
          </span>
          {!isPhoneShell && detail ? (
            <span className="hidden truncate sm:inline" style={{ color: "var(--muted)" }}>
              {detail}
            </span>
          ) : null}
        </div>
        {isPhoneShell && detail ? (
          <div className="mt-0.5 text-[11px]" style={{ color: "var(--muted)" }}>
            {detail}
          </div>
        ) : null}
      </div>
      <div className="flex shrink-0 items-center gap-3 text-[11px]">
        {state.canCancel && onCancel ? (
          <button
            type="button"
            onClick={onCancel}
            disabled={state.isPendingCancel}
            className="transition-opacity hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-45"
            style={{ color: "var(--muted)" }}
          >
            Stop
          </button>
        ) : null}
        {state.canSwitchToFast && onSwitchToFast ? (
          <button
            type="button"
            onClick={onSwitchToFast}
            disabled={state.isPendingCancel}
            className="transition-opacity hover:opacity-100 disabled:cursor-not-allowed disabled:opacity-45"
            style={{ color: "var(--muted)" }}
          >
            No Think
          </button>
        ) : null}
      </div>
    </div>
  );
}

export default InferenceStatusBanner;
