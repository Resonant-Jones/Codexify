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
  if (!intervention) {
    return null;
  }

  const railClassName = [
    "rounded-[var(--card-radius)] border p-[var(--card-pad)]",
    className ?? "",
  ]
    .filter(Boolean)
    .join(" ");
  const decisionBusy = submittingAction != null;
  const hasContext = intervention.details.length > 0;
  const contextId = `guardian-intervention-context-${intervention.id.replace(
    /[^a-zA-Z0-9_-]/g,
    "-"
  )}`;

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
        background:
          "color-mix(in oklab, var(--panel-bg) 90%, var(--accent-weak) 10%)",
        borderColor:
          "color-mix(in oklab, var(--panel-border) 66%, var(--accent) 34%)",
        marginBottom: "var(--card-pad)",
      }}
      aria-busy={decisionBusy}
      aria-labelledby={`${contextId}-title`}
      data-testid="guardian-thread-approval-rail"
    >
      <div className="min-w-0">
        <div
          className="text-[11px] font-semibold uppercase tracking-[0.08em]"
          style={{ color: "var(--accent)" }}
        >
          {intervention.statusLabel}
        </div>
        <h3
          id={`${contextId}-title`}
          className="text-sm font-semibold"
          style={{ color: "var(--text)", marginTop: "calc(var(--card-pad) / 3)" }}
        >
          {intervention.title}
        </h3>
        <p
          className="text-xs leading-5"
          style={{ color: "var(--muted)", marginTop: "calc(var(--card-pad) / 3)" }}
        >
          {intervention.summary}
        </p>
      </div>

      <div
        className="flex flex-wrap"
        style={{ gap: "calc(var(--card-pad) / 2)", marginTop: "var(--card-pad)" }}
      >
        {canSubmitDecision ? (
          <>
            <Button
              type="button"
              size="sm"
              onClick={() => void approve()}
              disabled={decisionBusy}
              aria-label="Approve Guardian request"
            >
              {submittingAction === "approve" ? "Approving…" : "Approve"}
            </Button>
            <Button
              type="button"
              size="sm"
              variant="destructive"
              onClick={() => void deny()}
              disabled={decisionBusy}
              aria-label="Deny Guardian request"
            >
              {submittingAction === "deny" ? "Denying…" : "Deny"}
            </Button>
          </>
        ) : null}
        {hasContext ? (
          <Button
            type="button"
            size="sm"
            variant="ghost"
            className="border border-[var(--panel-border)]"
            onClick={() => setShowContext((current) => !current)}
            aria-controls={contextId}
            aria-expanded={showContext}
          >
            {showContext ? "Hide context" : "Inspect context"}
          </Button>
        ) : null}
        {intervention.canRedirect ? (
          <Button
            type="button"
            size="sm"
            variant={canSubmitDecision ? "ghost" : "default"}
            className="border border-[var(--panel-border)]"
            onClick={handleTellGuardian}
          >
            Tell Guardian what to do instead
          </Button>
        ) : null}
      </div>

      {showContext && hasContext ? (
        <ul
          id={contextId}
          className="grid rounded-[var(--radius-micro)] border p-[var(--card-pad)] text-xs"
          style={{
            borderColor: "var(--panel-border)",
            color: "var(--muted)",
            gap: "calc(var(--card-pad) / 3)",
            marginTop: "calc(var(--card-pad) / 2)",
          }}
        >
          {intervention.details.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      ) : null}

      {notice ? (
        <div
          className="rounded-[var(--radius-micro)] border text-xs"
          style={{
            borderColor:
              "color-mix(in oklab, var(--accent) 34%, var(--panel-border))",
            background:
              "color-mix(in oklab, var(--accent-weak) 18%, var(--panel-bg))",
            color: "var(--text)",
            marginTop: "calc(var(--card-pad) / 2)",
            padding: "calc(var(--card-pad) / 2)",
          }}
          role="status"
        >
          {notice}
        </div>
      ) : null}

      {error ? (
        <div
          className="rounded-[var(--radius-micro)] border text-xs"
          style={{
            borderColor: "var(--danger-border)",
            background: "var(--danger-surface)",
            color: "var(--danger-text)",
            marginTop: "calc(var(--card-pad) / 2)",
            padding: "calc(var(--card-pad) / 2)",
          }}
          role="alert"
        >
          {error}
        </div>
      ) : null}
    </section>
  );
}
