import { useEffect, useState } from "react";

import { Button } from "@/components/ui/button";
import useGuardianThreadApprovalRail from "@/features/chat/hooks/useGuardianThreadApprovalRail";

type GuardianThreadApprovalRailProps = {
  className?: string;
  onTellGuardianWhatToDoInstead?: (payload: {
    runId: string | null;
    suggestedPrompt: string;
    threadId: number;
  }) => void;
  reloadSignal?: number;
  threadId?: number;
};

export default function GuardianThreadApprovalRail({
  className,
  onTellGuardianWhatToDoInstead,
  reloadSignal,
  threadId,
}: GuardianThreadApprovalRailProps) {
  const {
    approve,
    canSubmitDecision,
    deny,
    error,
    hasLoaded,
    intervention,
    loading,
    notice,
    reload,
    submittingAction,
    visible,
  } = useGuardianThreadApprovalRail({ threadId, reloadSignal });
  const [showContext, setShowContext] = useState(false);

  useEffect(() => {
    setShowContext(false);
  }, [intervention?.id]);

  if (!visible) {
    if (!hasLoaded || loading) return null;
    return null;
  }

  const railClassName = [
    "rounded-xl border px-3 py-3",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  const decisionBusy = submittingAction != null;
  const decisionDisabled = decisionBusy || !canSubmitDecision;
  const hasContext = intervention.details.length > 0;

  const handleTellGuardian = () => {
    if (onTellGuardianWhatToDoInstead) {
      onTellGuardianWhatToDoInstead({
        runId: intervention.runId,
        suggestedPrompt: intervention.redirectPrompt,
        threadId: intervention.threadId,
      });
      return;
    }

    if (typeof document === "undefined") return;
    const composer = document.querySelector<HTMLTextAreaElement>(
      '[data-testid="composer-textarea"]'
    );
    composer?.focus();
  };

  return (
    <section
      className={railClassName}
      style={{
        background: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
        borderColor: "var(--panel-border)",
      }}
      data-testid="guardian-thread-approval-rail"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div
            className="text-[11px] font-semibold uppercase tracking-[0.08em]"
            style={{ color: "var(--muted)" }}
          >
            {intervention.statusLabel}
          </div>
          <h3 className="mt-1 text-sm font-semibold" style={{ color: "var(--text)" }}>
            {intervention.title}
          </h3>
          <p className="mt-1 text-xs leading-5" style={{ color: "var(--muted)" }}>
            {intervention.summary}
          </p>
        </div>
        <Button
          type="button"
          size="sm"
          variant="ghost"
          className="border border-[var(--panel-border)]"
          onClick={() => void reload()}
          disabled={loading || decisionBusy}
        >
          {loading ? "Checking…" : "Reload"}
        </Button>
      </div>

      <div className="mt-3 flex flex-wrap gap-2">
        <Button
          type="button"
          size="sm"
          onClick={() => void approve()}
          disabled={decisionDisabled}
        >
          {submittingAction === "approve" ? "Approving…" : "Approve"}
        </Button>
        <Button
          type="button"
          size="sm"
          variant="destructive"
          onClick={() => void deny()}
          disabled={decisionDisabled}
        >
          {submittingAction === "deny" ? "Denying…" : "Deny"}
        </Button>
        {hasContext ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-[var(--panel-border)]"
            onClick={() => setShowContext((current) => !current)}
          >
            {showContext ? "Hide context" : "Inspect context"}
          </Button>
        ) : null}
        {intervention.canRedirect ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-[var(--panel-border)]"
            onClick={handleTellGuardian}
          >
            Tell Guardian what to do instead
          </Button>
        ) : null}
      </div>

      {!canSubmitDecision ? (
        <p className="mt-2 text-xs" style={{ color: "var(--muted)" }}>
          Direct approve/deny is unavailable for this thread intervention.
        </p>
      ) : null}

      {showContext && hasContext ? (
        <ul
          className="mt-2 space-y-1 rounded-lg border px-2 py-2 text-xs"
          style={{ borderColor: "var(--panel-border)", color: "var(--muted)" }}
        >
          {intervention.details.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}

      {notice ? (
        <div
          className="mt-2 rounded-lg border px-2 py-1 text-xs"
          style={{
            borderColor: "rgba(34, 197, 94, 0.35)",
            background: "rgba(34, 197, 94, 0.12)",
            color: "var(--text)",
          }}
          role="status"
        >
          {notice}
        </div>
      ) : null}

      {error ? (
        <div
          className="mt-2 rounded-lg border px-2 py-1 text-xs"
          style={{
            borderColor: "rgba(239, 68, 68, 0.35)",
            background: "rgba(239, 68, 68, 0.12)",
            color: "var(--text)",
          }}
          role="alert"
        >
          {error}
        </div>
      ) : null}
    </section>
  );
}
