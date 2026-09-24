import React from "react";
import { createPortal } from "react-dom";

import {
  NOTE_FORMATS,
  readLastNoteFormat,
  resolveNoteTitle,
  suggestNoteTitle,
  type NoteFormat,
} from "../noteSave";

type Props = {
  content: string;
  onClose: () => void;
  onSave: (title: string, format: NoteFormat) => Promise<void>;
};

export default function WorkspaceNoteSaveModal({ content, onClose, onSave }: Props) {
  const [title, setTitle] = React.useState(() => suggestNoteTitle(content));
  const [format, setFormat] = React.useState<NoteFormat>(readLastNoteFormat);
  const [saving, setSaving] = React.useState(false);
  const [error, setError] = React.useState("");
  const dialogRef = React.useRef<HTMLDivElement>(null);
  const titleRef = React.useRef<HTMLInputElement>(null);
  const resolved = resolveNoteTitle(title, format);

  React.useEffect(() => {
    titleRef.current?.focus();
  }, []);

  const handleKeyDown = (event: React.KeyboardEvent<HTMLDivElement>) => {
    if (event.key === "Escape" && !saving) {
      event.preventDefault();
      onClose();
    }
    if (event.key !== "Tab") return;
    const focusable = Array.from(dialogRef.current?.querySelectorAll<HTMLElement>(
      'input:not(:disabled), select:not(:disabled), button:not(:disabled)'
    ) ?? []);
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const handleSubmit = async (event: React.FormEvent) => {
    event.preventDefault();
    if (resolved.error || saving) return;
    setSaving(true);
    setError("");
    try {
      await onSave(resolved.title, resolved.format);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save note.");
    } finally {
      setSaving(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4">
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label="Save Note"
        onKeyDown={handleKeyDown}
        className="w-full max-w-sm rounded-[var(--radius)] border p-4 shadow-xl"
        style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)", color: "var(--text)" }}
      >
        <form onSubmit={(event) => { void handleSubmit(event); }} className="flex flex-col gap-3">
          <h2 className="text-base font-semibold">Save Note</h2>
          <label className="flex flex-col gap-1 text-sm">
            Title
            <input
              ref={titleRef}
              value={title}
              onChange={(event) => {
                const next = event.target.value;
                setTitle(next);
                const suffix = next.match(/\.([^.\s]+)$/)?.[1]?.toLowerCase();
                if (suffix === "md" || suffix === "txt") setFormat(suffix);
              }}
              className="rounded border p-2 text-sm text-[var(--text)]"
              style={{ background: "var(--surface)", borderColor: "var(--panel-border)" }}
            />
          </label>
          <label className="flex flex-col gap-1 text-sm">
            File type
            <select
              value={format}
              onChange={(event) => {
                const next = event.target.value as NoteFormat;
                setFormat(next);
                setTitle((current) => current.replace(/\.(md|txt)$/i, ""));
              }}
              className="rounded border p-2 text-sm text-[var(--text)]"
              style={{ background: "var(--surface)", borderColor: "var(--panel-border)" }}
            >
              {NOTE_FORMATS.map((entry) => <option key={entry.value} value={entry.value}>{entry.label}</option>)}
            </select>
          </label>
          {(resolved.error || error) && <p role="alert" className="text-sm">{resolved.error || error}</p>}
          <div className="flex justify-end gap-2">
            <button type="button" disabled={saving} onClick={onClose} className="rounded px-3 py-2 text-sm">Cancel</button>
            <button type="submit" disabled={Boolean(resolved.error) || saving} className="rounded px-3 py-2 text-sm font-semibold" style={{ background: "var(--accent)", color: "var(--text-on-accent)" }}>Save</button>
          </div>
        </form>
      </div>
    </div>,
    document.body
  );
}
