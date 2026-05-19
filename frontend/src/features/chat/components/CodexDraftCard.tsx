/**
 * CodexDraftCard
 *
 * Transient card rendered inline in the chat conversation lane when a
 * /codex_entry command produces a draft.  The card shows a label,
 * preview, source summary, and three actions:
 *
 *  - Save to Codex  → persists through POST /api/codex/entries
 *  - Download       → client-side Markdown export (no save)
 *  - Dismiss        → clears the draft locally (no save)
 */
import {
  BookOpen,
  Download,
  FileText,
  Save,
  X,
} from "lucide-react";
import React, { useCallback, useState } from "react";

import type { CodexDraft } from "@/api/codex";

export type CodexDraftCardAction = "save" | "download" | "dismiss";

export type CodexDraftCardProps = {
  draft: CodexDraft;
  onSave: (draft: CodexDraft) => void | Promise<void>;
  onDownload: (draft: CodexDraft) => void;
  onDismiss: () => void;
};

const PREVIEW_MAX_CHARS = 280;

function truncatePreview(body: string, maxChars: number): string {
  const cleaned = body.replace(/^#+\s+/gm, "").trim();
  if (cleaned.length <= maxChars) return cleaned;
  return cleaned.slice(0, maxChars).replace(/\s+\S*$/, "") + "…";
}

export function CodexDraftCard({
  draft,
  onSave,
  onDownload,
  onDismiss,
}: CodexDraftCardProps) {
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const handleSave = useCallback(async () => {
    if (saving || saved) return;
    setSaving(true);
    try {
      await onSave(draft);
      setSaved(true);
    } finally {
      setSaving(false);
    }
  }, [draft, onSave, saved, saving]);

  const handleDownload = useCallback(() => {
    onDownload(draft);
  }, [draft, onDownload]);

  return (
    <div
      data-testid="codex-draft-card"
      className="w-full flex justify-start min-w-0"
    >
      <div
        className="max-w-[min(38rem,calc(100%-1rem))] min-w-0 rounded-[22px] border shadow-sm overflow-hidden"
        style={{
          background:
            "color-mix(in oklab, var(--panel-sheet, var(--panel-bg)) 82%, transparent)",
          borderColor: "var(--panel-border)",
          color: "var(--text)",
        }}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 pt-3 pb-2">
          <BookOpen
            className="h-4 w-4 shrink-0"
            style={{ color: "var(--accent, rgb(99 102 241))" }}
            aria-hidden="true"
          />
          <span className="text-sm font-semibold tracking-tight">
            Codex Entry
          </span>
          <span
            className="text-xs px-2 py-0.5 rounded-full"
            style={{
              background:
                "color-mix(in oklab, var(--accent, rgb(99 102 241)) 20%, transparent)",
              color: "var(--accent, rgb(99 102 241))",
            }}
          >
            Draft
          </span>
          {saved ? (
            <span
              className="text-xs px-2 py-0.5 rounded-full ml-auto"
              style={{
                background:
                  "color-mix(in oklab, rgb(34 197 94) 18%, transparent)",
                color: "rgb(34 197 94)",
              }}
            >
              Saved
            </span>
          ) : null}
        </div>

        {/* Title */}
        <div className="px-4 pb-1">
          <h3 className="text-base font-medium leading-snug truncate">
            {draft.title || "Codex Entry"}
          </h3>
        </div>

        {/* Preview */}
        <div className="px-4 pb-1">
          <p
            className="text-sm leading-relaxed line-clamp-3"
            style={{ color: "var(--muted)" }}
          >
            {truncatePreview(draft.body, PREVIEW_MAX_CHARS)}
          </p>
        </div>

        {/* Source summary */}
        <div className="px-4 pb-2">
          <div className="flex items-center gap-1.5">
            <FileText
              className="h-3 w-3 shrink-0"
              style={{ color: "var(--muted)" }}
              aria-hidden="true"
            />
            <span
              className="text-xs"
              style={{ color: "var(--muted)" }}
            >
              {draft.source_summary}
            </span>
          </div>
        </div>

        {/* Actions */}
        <div
          className="flex items-center gap-1 px-3 py-2 border-t"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <button
            type="button"
            data-testid="codex-draft-save"
            disabled={saving || saved}
            onClick={handleSave}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors disabled:opacity-50"
            style={{
              background:
                "color-mix(in oklab, var(--accent, rgb(99 102 241)) 16%, transparent)",
              color: "var(--accent, rgb(99 102 241))",
            }}
          >
            {saving ? (
              <>
                <span
                  className="h-3 w-3 animate-spin rounded-full border-2 border-current border-t-transparent"
                  aria-hidden="true"
                />
                Saving…
              </>
            ) : saved ? (
              <>
                <Save className="h-3.5 w-3.5" aria-hidden="true" />
                Saved
              </>
            ) : (
              <>
                <Save className="h-3.5 w-3.5" aria-hidden="true" />
                Save to Codex
              </>
            )}
          </button>

          <button
            type="button"
            data-testid="codex-draft-download"
            onClick={handleDownload}
            className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors"
            style={{
              background:
                "color-mix(in oklab, var(--panel-bg) 60%, transparent)",
              color: "var(--text)",
            }}
          >
            <Download className="h-3.5 w-3.5" aria-hidden="true" />
            Download
          </button>

          <button
            type="button"
            data-testid="codex-draft-dismiss"
            onClick={onDismiss}
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

export default CodexDraftCard;
