import React from "react";

import Textarea from "@/components/ui/textarea";

import { useWorkspaceScratchpadState } from "../state/useWorkspaceScratchpadState";

type WorkspaceScratchpadPanelProps = {
  threadIdentity?: string | number | null;
  onMoveToComposer?: (text: string) => void;
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
  const descriptionId = `${textareaId}-description`;
  const statusId = `${textareaId}-status`;
  const [statusMessage, setStatusMessage] = React.useState("");
  const hasContent = text.length > 0;

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
    setStatusMessage("Scratchpad cleared.");
  }, [clear]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-3">
      <div className="space-y-1">
        <label
          htmlFor={textareaId}
          className="text-sm font-semibold"
          style={{ color: "var(--text)" }}
        >
          Scratchpad
        </label>
        <p
          id={descriptionId}
          className="text-xs leading-5"
          style={{ color: "var(--muted)" }}
        >
          Plaintext staging area. Autosaves locally per thread and stays separate
          from the composer draft.
        </p>
      </div>

      <div
        className="rounded-[var(--radius-micro)] border px-3 py-2 text-xs"
        style={{
          borderColor: "var(--chip-border)",
          background: "var(--chip-bg)",
          color: "var(--text-subtle)",
        }}
      >
        Thread scope: {threadKey}
      </div>

      <Textarea
        id={textareaId}
        data-testid="workspace-scratchpad-textarea"
        aria-describedby={`${descriptionId} ${statusId}`}
        value={text}
        rows={12}
        spellCheck={false}
        placeholder="Stage plaintext notes, prompts, or fragments here."
        className="min-h-[14rem] flex-1 resize-none rounded-[var(--radius)] border px-3 py-3 leading-6"
        style={{
          borderColor: "var(--panel-border)",
          background:
            "color-mix(in oklab, var(--panel-bg) 94%, transparent)",
        }}
        onChange={(event) => {
          setText(event.target.value);
        }}
      />

      <div className="flex flex-wrap items-center gap-2">
        <button
          type="button"
          className="rounded-[var(--radius-micro)] border px-3 py-2 text-sm font-medium"
          style={{
            borderColor: "var(--chip-border)",
            background: "var(--chip-bg)",
            color: "var(--text)",
          }}
          disabled={!hasContent}
          onClick={handleMoveToComposer}
        >
          Move to composer
        </button>
        <button
          type="button"
          className="rounded-[var(--radius-micro)] border px-3 py-2 text-sm font-medium"
          style={{
            borderColor: "var(--chip-border)",
            background: "var(--chip-bg)",
            color: "var(--text)",
          }}
          disabled={!hasContent}
          onClick={() => {
            void handleCopyToClipboard();
          }}
        >
          Copy to clipboard
        </button>
        <button
          type="button"
          className="rounded-[var(--radius-micro)] border px-3 py-2 text-sm font-medium"
          style={{
            borderColor: "var(--chip-border)",
            background: "var(--chip-bg)",
            color: "var(--text)",
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
        className="text-xs"
        style={{ color: "var(--muted)" }}
      >
        {statusMessage || "Scratchpad stays local to this browser."}
      </div>
    </div>
  );
}
