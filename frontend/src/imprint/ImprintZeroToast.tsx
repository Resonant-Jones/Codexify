import React from "react";
import clsx from "clsx";
import { X, Check, Edit, AlertTriangle } from "lucide-react";
import { ImprintProposal } from "./api";

type Props = {
  proposal: ImprintProposal;
  onAccept: (override?: string) => void;
  onReject: () => void;
  onEditAccept: (text: string) => void;
};

export function ImprintZeroToast({ proposal, onAccept, onReject, onEditAccept }: Props) {
  const [openEditor, setOpenEditor] = React.useState(false);
  const [draftText, setDraftText] = React.useState(proposal.persona_draft || "");

  return (
    <>
      <div
        className={clsx(
          "fixed right-4 top-4 z-[200] w-[min(360px,90vw)] rounded-xl border shadow-lg backdrop-blur",
          "bg-[var(--panel-bg,#111827)] border-[var(--panel-border,rgba(255,255,255,0.1))]"
        )}
      >
        <div className="flex items-start gap-3 p-3">
          <div className="mt-0.5 rounded-full bg-[var(--accent-weak,#334155)]/40 p-1.5 text-[var(--text,#f8fafc)]">
            <AlertTriangle className="h-4 w-4" />
          </div>
          <div className="flex-1">
            <div className="text-sm font-semibold" style={{ color: "var(--text,#f8fafc)" }}>
              Imprint Zero proposal
            </div>
            <div className="text-xs opacity-80" style={{ color: "var(--muted,#cbd5e1)" }}>
              Proposed Guardian name: <strong>{proposal.name}</strong>
            </div>
            <div className="mt-2 rounded-lg bg-white/5 p-2 text-xs" style={{ color: "var(--text,#f8fafc)" }}>
              {proposal.persona_draft}
            </div>
            <div className="mt-2 flex gap-2">
              <button className="embedded-btn inline-flex items-center gap-1" onClick={() => onAccept()}>
                <Check className="h-4 w-4" /> Accept
              </button>
              <button className="embedded-btn inline-flex items-center gap-1" onClick={() => setOpenEditor(true)}>
                <Edit className="h-4 w-4" /> Edit & Accept
              </button>
              <button className="embedded-btn inline-flex items-center gap-1" onClick={onReject}>
                <X className="h-4 w-4" /> Reject
              </button>
            </div>
          </div>
          <button className="icon-inline" aria-label="Close" onClick={onReject}>
            <X className="h-4 w-4" />
          </button>
        </div>
      </div>

      {openEditor && (
        <div className="fixed inset-0 z-[210] flex items-center justify-center">
          <div className="absolute inset-0 bg-black/50" onClick={() => setOpenEditor(false)} />
          <div
            className="relative z-[211] w-[min(520px,90vw)] rounded-2xl border p-4 shadow-xl"
            style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
          >
            <div className="flex items-center justify-between mb-2">
              <div className="text-sm font-semibold">Edit persona</div>
              <button className="icon-inline" onClick={() => setOpenEditor(false)}>
                <X className="h-4 w-4" />
              </button>
            </div>
            <textarea
              value={draftText}
              onChange={(e) => setDraftText(e.target.value)}
              className="w-full rounded-lg border bg-transparent p-2 text-sm"
              rows={6}
              style={{ borderColor: "var(--panel-border)", color: "var(--text)" }}
            />
            <div className="mt-3 flex justify-end gap-2">
              <button className="embedded-btn" onClick={() => setOpenEditor(false)}>
                Cancel
              </button>
              <button
                className="embedded-btn"
                onClick={() => {
                  onEditAccept(draftText);
                  setOpenEditor(false);
                }}
                disabled={!draftText.trim()}
              >
                Save & Accept
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}

export default ImprintZeroToast;
