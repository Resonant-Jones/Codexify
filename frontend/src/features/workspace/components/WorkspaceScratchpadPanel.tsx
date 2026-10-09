import React from "react";

import Textarea from "@/components/ui/textarea";
import api from "@/lib/api";

import WorkspaceNoteSaveModal from "./WorkspaceNoteSaveModal";
import { rememberNoteFormat, type NoteFormat } from "../noteSave";

import { useWorkspaceScratchpadState } from "../state/useWorkspaceScratchpadState";

type WorkspaceScratchpadPanelProps = {
  threadIdentity?: string | number | null;
  onMoveToComposer?: (text: string) => void;
};

type SaveSnapshot = {
  content: string;
  threadIdentity?: string | number | null;
};

async function copyTextToClipboard(text: string): Promise<boolean> {
  if (!text) return false;

  try {
    if (
      typeof navigator !== "undefined" &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function"
    ) {
      await navigator.clipboard.writeText(text);
      return true;
    }
  } catch {
    // Fall through to the DOM fallback.
  }

  if (typeof document === "undefined") return false;

  try {
    const ghost = document.createElement("textarea");
    ghost.value = text;
    ghost.setAttribute("readonly", "");
    ghost.style.position = "fixed";
    ghost.style.opacity = "0";
    ghost.style.pointerEvents = "none";
    document.body.appendChild(ghost);
    ghost.focus();
    ghost.select();
    const copied =
      typeof document.execCommand === "function"
        ? document.execCommand("copy")
        : false;
    document.body.removeChild(ghost);
    return copied;
  } catch {
    return false;
  }
}

export default function WorkspaceScratchpadPanel({
  threadIdentity,
  onMoveToComposer,
}: WorkspaceScratchpadPanelProps) {
  const { text, setText, clear, threadKey } = useWorkspaceScratchpadState({
    threadIdentity,
  });
  const textareaId = React.useId();
  const statusId = `${textareaId}-status`;
  const [statusMessage, setStatusMessage] = React.useState("");
  const [saveSnapshot, setSaveSnapshot] = React.useState<SaveSnapshot | null>(
    null
  );
  const saveTriggerRef = React.useRef<HTMLButtonElement>(null);
  const hasContent = text.length > 0;
  const scratchpadPlaceholder =
    "Stage plaintext notes, prompts, or fragments before moving them into the composer.";

  const handleMoveToComposer = React.useCallback(() => {
    if (!hasContent) return;
    onMoveToComposer?.(text);
    setStatusMessage("Moved to composer.");
  }, [hasContent, onMoveToComposer, text]);

  const handleCopyToClipboard = React.useCallback(async () => {
    const didCopy = await copyTextToClipboard(text);
    setStatusMessage(didCopy ? "Copied to clipboard." : "Clipboard unavailable.");
  }, [text]);

  const handleClear = React.useCallback(() => {
    clear();
    setStatusMessage("Notes draft cleared.");
  }, [clear]);

  const closeSaveModal = React.useCallback(() => {
    setSaveSnapshot(null);
    saveTriggerRef.current?.focus();
  }, []);

  const handleSave = React.useCallback(async (title: string, format: NoteFormat) => {
    if (!saveSnapshot) {
      throw new Error("Open the Save dialog before saving this Note.");
    }
    const threadId = Number(saveSnapshot.threadIdentity);
    if (!Number.isSafeInteger(threadId) || threadId <= 0) {
      throw new Error("Select a saved thread before saving this Note.");
    }
    const response = await api.post<{ filename: string }>("/documents/notes", {
      thread_id: threadId,
      title,
      content: saveSnapshot.content,
      format,
    });
    rememberNoteFormat(format);
    setStatusMessage(`Saved ${response.data.filename} to this thread and project.`);
    closeSaveModal();
  }, [closeSaveModal, saveSnapshot]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div
        data-testid="workspace-scratchpad-thread-scope"
        className="text-center text-[11px]"
        style={{ color: "var(--text-subtle)" }}
      >
        Thread: {threadKey}
      </div>

      <Textarea
        id={textareaId}
        data-testid="workspace-scratchpad-textarea"
        aria-label="Notes"
        aria-describedby={statusId}
        value={text}
        rows={12}
        spellCheck={false}
        placeholder={scratchpadPlaceholder}
        className="min-h-[14rem] flex-1 resize-none rounded-[var(--radius)] border px-3 py-3 text-sm leading-6"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        }}
        onChange={(event) => {
          setText(event.target.value);
        }}
      />

      <div
        data-testid="workspace-scratchpad-actions"
        className="flex flex-wrap items-center justify-center gap-1.5"
      >
        <button
          ref={saveTriggerRef}
          type="button"
          className="rounded-[var(--radius-micro)] px-2.5 py-1 text-sm font-semibold disabled:opacity-35"
          style={{ color: "var(--text-on-accent)", background: "var(--accent)" }}
          disabled={!text.trim()}
          onClick={() => setSaveSnapshot({ content: text, threadIdentity })}
        >
          Save
        </button>
        <button
          type="button"
          className="rounded-[var(--radius-micro)] px-2.5 py-1 text-sm font-medium opacity-80 transition-opacity hover:opacity-100 active:opacity-70 disabled:opacity-35"
          style={{
            color: "var(--text)",
            background: "transparent",
          }}
          disabled={!hasContent}
          onClick={handleMoveToComposer}
        >
          Move to composer
        </button>
        <button
          type="button"
          className="rounded-[var(--radius-micro)] px-2.5 py-1 text-sm font-medium opacity-80 transition-opacity hover:opacity-100 active:opacity-70 disabled:opacity-35"
          style={{
            color: "var(--text)",
            background: "transparent",
          }}
          disabled={!hasContent}
          onClick={() => {
            void handleCopyToClipboard();
          }}
        >
          Copy to Clipboard
        </button>
        <button
          type="button"
          className="rounded-[var(--radius-micro)] px-2.5 py-1 text-sm font-medium opacity-80 transition-opacity hover:opacity-100 active:opacity-70 disabled:opacity-35"
          style={{
            color: "var(--text)",
            background: "transparent",
          }}
          disabled={!hasContent}
          onClick={handleClear}
        >
          Clear
        </button>
      </div>

      <div
        id={statusId}
        aria-live="polite"
        data-testid="workspace-scratchpad-status"
        className="text-center text-[11px]"
        style={{ color: "var(--text-subtle)" }}
      >
        {statusMessage || "Notes draft stays local to this browser until Save."}
      </div>
      {saveSnapshot !== null && (
        <WorkspaceNoteSaveModal
          content={saveSnapshot.content}
          onClose={closeSaveModal}
          onSave={handleSave}
        />
      )}
    </div>
  );
}
