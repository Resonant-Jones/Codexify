import { BookOpen, FileText, Sparkles, X } from "lucide-react";
import React from "react";

import type { CodexSuggestion } from "@/api/codex";

export type CodexSuggestionCardProps = {
  suggestion: CodexSuggestion;
  onDraft: (suggestion: CodexSuggestion) => void | Promise<void>;
  onDismiss: (suggestion: CodexSuggestion) => void;
};

function formatReason(reason: string | null): string | null {
  if (!reason) return null;
  return reason
    .split(/[_-]+/g)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function CodexSuggestionCard({
  suggestion,
  onDraft,
  onDismiss,
}: CodexSuggestionCardProps) {
  const reason = formatReason(suggestion.reason);

  return (
    <div
      data-testid="codex-suggestion-card"
      className="w-full flex justify-start min-w-0"
    >
      <div
        className="max-w-[min(36rem,calc(100%-1rem))] min-w-0 rounded-[22px] border shadow-sm overflow-hidden"
        style={{
          background:
            "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 82%, transparent)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        <div className="flex items-center gap-2 px-4 pt-3 pb-2">
          <Sparkles
            className="h-4 w-4 shrink-0"
            style={{ color: "var(--accent, rgb(99 102 241))" }}
            aria-hidden="true"
          />
          <span className="text-sm font-semibold tracking-tight">
            {suggestion.label || "Codex Entry"}
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background:
                "color-mix(in oklab, var(--accent, rgb(99 102 241)) 18%, transparent)",
              color: "var(--accent, rgb(99 102 241))",
            }}
          >
            Suggested
          </span>
        </div>

        <div className="px-4 pb-2">
          <div className="flex items-center gap-1.5">
            <FileText
              className="h-3 w-3 shrink-0"
              style={{ color: "var(--muted)" }}
              aria-hidden="true"
            />
            <span className="text-xs" style={{ color: "var(--muted)" }}>
              {suggestion.sourceSummary}
            </span>
          </div>
          {reason ? (
            <div
              data-testid="codex-suggestion-reason"
              className="mt-1 text-xs"
              style={{ color: "var(--muted)" }}
            >
              {reason}
            </div>
          ) : null}
        </div>

        <div
          className="flex items-center gap-1 px-3 py-2 border-t"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <button
            type="button"
            data-testid="codex-suggestion-draft"
            onClick={() => {
              void onDraft(suggestion);
            }}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background:
                "color-mix(in oklab, var(--accent, rgb(99 102 241)) 16%, transparent)",
              color: "var(--accent, rgb(99 102 241))",
            }}
          >
            <BookOpen className="h-3.5 w-3.5" aria-hidden="true" />
            Draft Codex Entry
          </button>

          <button
            type="button"
            data-testid="codex-suggestion-dismiss"
            onClick={() => onDismiss(suggestion)}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors ml-auto"
            style={{
              background:
                "color-mix(in oklab, var(--panel-bg) 60%, transparent)",
              color: "var(--muted)",
            }}
          >
            <X className="h-3.5 w-3.5" aria-hidden="true" />
            Dismiss
          </button>
        </div>
      </div>
    </div>
  );
}

export default CodexSuggestionCard;
