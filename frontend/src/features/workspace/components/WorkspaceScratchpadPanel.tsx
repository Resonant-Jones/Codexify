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
  const statusId = `${textareaId}-status`;
  const [statusMessage, setStatusMessage] = React.useState("");
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
    setStatusMessage("Scratchpad cleared.");
  }, [clear]);

  return (
    <div className="flex h-full min-h-0 flex-col gap-4">
      <div className="flex items-center justify-between gap-3">
        <label
          htmlFor={textareaId}
          className="text-sm font-semibold"
          style={{ color: "var(--text)" }}
        >
          Scratchpad
        </label>
        <div
          data-testid="workspace-scratchpad-thread-scope"
          className="text-[11px]"
          style={{ color: "var(--text-subtle)" }}
        >
          Thread: {threadKey}
        </div>
      </div>

      <Textarea
        id={textareaId}
        data-testid="workspace-scratchpad-textarea"
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
        {statusMessage || "Scratchpad stays local to this browser."}
      </div>
    </div>
  );
}
