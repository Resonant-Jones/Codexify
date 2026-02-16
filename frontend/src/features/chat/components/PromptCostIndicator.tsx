import { useState } from "react";
import clsx from "clsx";

import type { PromptCostStatus, SystemPromptSummary } from "@/imprint/api";

type PromptCostIndicatorProps = {
  summary?: SystemPromptSummary | null;
};

const STATUS_LABEL: Record<PromptCostStatus, string> = {
  ok: "Prompt Cost: OK",
  warn: "Prompt Cost: WARN",
  hard: "Prompt Cost: HARD",
  unknown: "Prompt Cost: UNKNOWN",
};

const STATUS_CLASS: Record<PromptCostStatus, string> = {
  ok: "border-emerald-500/35 bg-emerald-500/10 text-emerald-200",
  warn: "border-amber-500/45 bg-amber-500/10 text-amber-200",
  hard: "border-rose-500/55 bg-rose-500/12 text-rose-200",
  unknown: "border-[var(--panel-border)] bg-transparent text-[var(--text)]",
};

const STATUS_HELPER: Record<PromptCostStatus, string> = {
  ok: "Within prompt budget.",
  warn: "Approaching token budget.",
  hard: "High prompt cost. Consider trimming persona/docs context.",
  unknown: "Prompt estimate unavailable.",
};

export default function PromptCostIndicator({
  summary,
}: PromptCostIndicatorProps) {
  const status: PromptCostStatus = summary?.threshold?.status ?? "unknown";
  const estimatedTotal =
    summary?.estimated_tokens_total ?? summary?.estimated_tokens ?? null;
  const warnings = summary?.warnings || [];
  const [showTokens, setShowTokens] = useState(false);
  const hasEstimatedTotal = typeof estimatedTotal === "number";

  return (
    <div
      className={clsx(
        "mx-4 mt-3 rounded-lg border px-3 py-2 text-xs",
        STATUS_CLASS[status]
      )}
      role="status"
      aria-live="polite"
      data-testid="prompt-cost-indicator"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-semibold tracking-wide">
          {STATUS_LABEL[status]}
        </span>
        <span className="flex items-center gap-1">
          <button
            type="button"
            className={clsx(
              "rounded px-1 py-0.5 text-[10px] leading-none opacity-70 transition hover:opacity-100",
              "border border-current/20"
            )}
            aria-label={showTokens ? "Hide token count" : "Show token count"}
            onClick={() => setShowTokens((prev) => !prev)}
            disabled={!hasEstimatedTotal}
            data-testid="prompt-cost-toggle-tokens"
            title={hasEstimatedTotal ? "Toggle token count" : "Token estimate unavailable"}
          >
            #
          </button>
          {showTokens && hasEstimatedTotal ? (
            <span className="tabular-nums text-[11px] opacity-80">
              {estimatedTotal} tokens
            </span>
          ) : null}
        </span>
      </div>
      <div className="mt-1 opacity-85">
        {warnings.length > 0 ? warnings.join(" ") : STATUS_HELPER[status]}
      </div>
    </div>
  );
}
