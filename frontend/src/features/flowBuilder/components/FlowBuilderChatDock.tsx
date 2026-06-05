import { MessageSquareMore, X } from "lucide-react";

import type { FlowDraftSupportContextSummary, FlowDraftValidationSummary } from "../model/flowDraft";

type FlowBuilderChatDockProps = {
  onToggleOpen: () => void;
  open: boolean;
  supportChatContext: FlowDraftSupportContextSummary;
  validationSummary: FlowDraftValidationSummary;
};

const ASSISTANT_NOTES = [
  "Use this dock to review an automation specification draft from a known process or rough intent.",
  "Mark missing steps, assumptions, constraints, and validation gates before runnable claims.",
  "Sidecar notes only: no backend chat integration, persistence, thread binding, or automation execution is wired here.",
];

function getVisibleDraftModeLabel(modeLabel: string): string {
  return modeLabel.toLowerCase() === "expertise" ? "Assistant-guided" : "manual process";
}

export default function FlowBuilderChatDock({
  onToggleOpen,
  open,
  supportChatContext,
  validationSummary,
}: FlowBuilderChatDockProps) {
  const visibleDraftModeLabel = getVisibleDraftModeLabel(supportChatContext.modeLabel);

  if (!open) {
    return (
      <aside
        data-testid="flow-builder-chat-dock"
        className="flex min-h-[220px] flex-col justify-between overflow-hidden rounded-[var(--tile-radius,19px)] border"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 92%, transparent), color-mix(in oklab, var(--panel-bg) 84%, transparent))",
        }}
      >
        <button
          type="button"
          data-testid="flow-builder-assistant-toggle"
          onClick={onToggleOpen}
          className="flex w-full items-center justify-between gap-3 border-b border-[var(--panel-border)] px-4 py-4 text-left"
        >
          <span>
            <span className="block text-[11px] uppercase tracking-[0.24em]" style={{ color: "var(--muted)" }}>
              Assistant dock hidden
            </span>
            <span className="mt-1 block text-sm font-medium">
              Reopen to inspect Assistant-guided sidecar notes.
            </span>
          </span>
          <span
            className="rounded-full border px-2.5 py-1 text-[11px] uppercase tracking-[0.2em]"
            style={{
              borderColor: "var(--chip-border)",
              background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
              color: "var(--muted)",
            }}
          >
            Open
          </span>
        </button>
        <div className="space-y-2 px-4 py-4 text-sm leading-6" style={{ color: "var(--muted)" }}>
          <div>{supportChatContext.dockStateLabel} support lane.</div>
          <div>{validationSummary.label}</div>
        </div>
      </aside>
    );
  }

  return (
    <aside
      data-testid="flow-builder-chat-dock"
      className="flex min-h-[560px] flex-col overflow-hidden rounded-[var(--tile-radius,19px)] border"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "linear-gradient(180deg, color-mix(in oklab, var(--panel-bg) 94%, transparent), color-mix(in oklab, var(--panel-bg) 88%, transparent))",
        boxShadow: "inset 0 1px 0 color-mix(in oklab, white 6%, transparent)",
      }}
    >
      <div className="flex items-start justify-between gap-3 border-b border-[var(--panel-border)] p-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            <MessageSquareMore className="h-4 w-4" style={{ color: "var(--accent-weak)" }} />
            <div className="text-[11px] uppercase tracking-[0.24em]" style={{ color: "var(--muted)" }}>
              Assistant-guided draft support
            </div>
          </div>
          <p className="mt-2 text-sm leading-6" style={{ color: "var(--muted)" }}>
            Local review support for {visibleDraftModeLabel} automation-spec drafting. It can help
            frame questions and notes, but it is not a live chat transport.
          </p>
        </div>
        <button
          type="button"
          data-testid="flow-builder-assistant-toggle"
          onClick={onToggleOpen}
          className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border transition hover:-translate-y-[1px]"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in oklab, var(--chip-bg) 88%, transparent)",
            color: "var(--text)",
          }}
          aria-label="Hide assistant dock"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="flex-1 space-y-3 p-4">
        {ASSISTANT_NOTES.map((note) => (
          <div
            key={note}
            className="rounded-[var(--tile-radius,19px)] border px-4 py-3 text-sm leading-6"
            style={{
              borderColor: "var(--panel-border)",
              background: "color-mix(in oklab, var(--chip-bg) 92%, transparent)",
            }}
          >
            {note}
          </div>
        ))}

        <div
          data-testid="flow-builder-support-context"
          className="rounded-[var(--tile-radius,19px)] border px-4 py-3"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in oklab, var(--accent) 10%, var(--panel-bg))",
          }}
        >
          <div className="text-[11px] uppercase tracking-[0.22em]" style={{ color: "var(--muted)" }}>
            Shared draft context
          </div>
          <div className="mt-2 text-sm font-medium">{supportChatContext.draftTitle}</div>
          <div className="mt-2 space-y-1 text-sm leading-6" style={{ color: "var(--muted)" }}>
            <div>Stage: {supportChatContext.selectedStageLabel}</div>
            <div>Node: {supportChatContext.selectedNodeLabel}</div>
            <div>Validation: {validationSummary.label}</div>
          </div>
        </div>
      </div>

      <div className="border-t border-[var(--panel-border)] p-4">
        <div
          className="rounded-[var(--tile-radius,19px)] border px-3 py-2 text-sm leading-6"
          style={{
            borderColor: "var(--panel-border)",
            background: "color-mix(in oklab, var(--chip-bg) 90%, transparent)",
            color: "var(--muted)",
          }}
        >
          {supportChatContext.provenanceLabel}. Validation {validationSummary.label}. Sidecar
          notes only. No backend chat integration is wired here. No automation execution is
          triggered here.
        </div>
      </div>
    </aside>
  );
}
