/**
 * Composer.tsx
 *
 * Renders the chat composer input and controls, including turn-based gating
 * to prevent overlapping user sends while an assistant reply is in flight.
 */
import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Paperclip, ImagePlus } from "lucide-react";
import useUploader, { UploadedAttachment, toAbsoluteMediaUrl } from "@/hooks/useUploader";

import { ImageGenModal } from "@/components/modals/ImageGenModal";
import { cn } from "@/lib/utils";

export function Composer({
  onSend,
  prefill,
  onPrefillConsumed,
  threadId,
  isSending,
  isTurnInFlight,
}: {
  onSend: (t: string) => Promise<void> | void;
  prefill?: string;
  onPrefillConsumed?: () => void;
  threadId?: number;
  isSending?: boolean;
  isTurnInFlight?: boolean;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);

  // Initialize with saved draft if available
  const [value, setValue] = useState(() => {
    if (threadId && typeof window !== "undefined") {
      try {
        const saved = sessionStorage.getItem(`composer-draft-${threadId}`);
        if (saved) return saved;
      } catch {}
    }
    return "";
  });

  const [internalSending, setInternalSending] = useState(false);
  const [showImgGen, setShowImgGen] = useState(false);
  const effectiveSending = Boolean(isSending) || internalSending;
  const turnLocked = Boolean(isTurnInFlight);
  const actionsDisabled = turnLocked || effectiveSending;
  const showToast = (message: string) => {
    try {
      window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message, kind: "error" } }));
    } catch {}
  };
  const notifyTurnLocked = () => {
    showToast("One moment—finish the current reply first.");
  };

  // Auto-save draft to sessionStorage
  useEffect(() => {
    if (threadId && typeof window !== "undefined") {
      try {
        if (value.trim()) {
          sessionStorage.setItem(`composer-draft-${threadId}`, value);
        } else {
          sessionStorage.removeItem(`composer-draft-${threadId}`);
        }
      } catch {}
    }
  }, [value, threadId]);

  const buildChatAttachmentMessage = (items: UploadedAttachment[], bodyText: string) => {
    const lines: string[] = [];

    for (const item of items) {
      const kind = item.kind;
      const id = (item.id ?? "").toString().trim();
      const src = toAbsoluteMediaUrl(item.src_url);
      const name = (item.filename ?? "").toString().trim();

      // Primary marker for backend worker; keep format stable.
      lines.push(`<!-- cfy-media:${kind}:${id || "missing-id"} -->`);
      if (src) lines.push(`<!-- cfy-media-src:${src} -->`);
      if (name) lines.push(`<!-- cfy-media-name:${name} -->`);
    }

    const body = bodyText.trim();
    if (body) lines.push(body);

    return lines.join("\n\n").trim();
  };

  const uploader = useUploader({
    tag: "chat",
    onImages: (items) => {
      try { window.dispatchEvent(new CustomEvent("cfy:gallery:add", { detail: { items } })); } catch {}
      try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Added ${items.length} image${items.length===1?"":"s"}` } })); } catch {}
    },
    onDocuments: (items) => {
      try { window.dispatchEvent(new CustomEvent("cfy:documents:add", { detail: { items } })); } catch {}
      try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Added ${items.length} document${items.length===1?"":"s"}` } })); } catch {}
    },
    onUploaded: async (items) => {
      if (!items.length) return;
      if (actionsDisabled) {
        notifyTurnLocked();
        return;
      }
      const message = buildChatAttachmentMessage(items, value);
      if (!message) return;
      setInternalSending(true);
      try {
        await onSend(message);
        setValue("");
        if (threadId && typeof window !== "undefined") {
          try {
            sessionStorage.removeItem(`composer-draft-${threadId}`);
          } catch {}
        }
      } catch (err: any) {
        const message = err?.message || "Failed to send message.";
        showToast(message);
      } finally {
        setInternalSending(false);
      }
    },
    onAnyUpload: () => { try { localStorage.setItem("cfy.hasUserUpload", "true"); } catch {} },
    disabled: turnLocked || effectiveSending,
  });

  function onPaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
      if (actionsDisabled) {
        notifyTurnLocked();
        return;
      }
      uploader.handleFiles(files);
    }
  }
  useEffect(() => {
    if (prefill && prefill !== value) {
      setValue(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
  }, [prefill]);
  async function send() {
    const v = value.trim();
    if (!v || effectiveSending) return;
    if (turnLocked) {
      notifyTurnLocked();
      return;
    }
    setInternalSending(true);
    try {
      await onSend(v);
      setValue("");
      // Clear the draft from storage after successful send
      if (threadId && typeof window !== "undefined") {
        try {
          sessionStorage.removeItem(`composer-draft-${threadId}`);
        } catch {}
      }
    } catch (err: any) {
      const message = err?.message || "Failed to send message.";
      showToast(message);
    } finally {
      setInternalSending(false);
    }
  }
  const handleDrop = (e: React.DragEvent) => {
    if (actionsDisabled) {
      e.preventDefault();
      notifyTurnLocked();
      return;
    }
    uploader.onDrop(e);
  };
  const handleDragOver = (e: React.DragEvent) => {
    if (actionsDisabled) {
      e.preventDefault();
      return;
    }
    uploader.onDragOver(e);
  };
  return (
    <>
      <div className="flex flex-col flex-1 w-full p-[4px]" onDrop={handleDrop} onDragOver={handleDragOver}>
        <div className="flex flex-col flex-1 w-full rounded-[var(--tile-radius)] p-[4px]">
          {/* Content Rectangle - Textarea area */}
          <div className="flex-1 flex flex-col px-[12px] pt-[8px] pb-[6px]">
            <Textarea
              ref={ref}
              value={value}
              onChange={(e) => setValue(e.target.value)}
              placeholder="Write a message…"
              onPaste={onPaste}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  if (turnLocked) {
                    notifyTurnLocked();
                    return;
                  }
                  if (!effectiveSending) {
                    send();
                  }
                }
              }}
              className="w-full min-h-[96px] resize-none border-0 bg-transparent text-base leading-relaxed focus-visible:ring-0 focus-visible:outline-none shadow-none placeholder:text-white/20"
              style={{ color: "var(--text)" }}
            />
          </div>

          {/* Toolbar Row - Bottom controls */}
          <div className="flex items-center justify-between px-[8px] pb-[6px]">
            <div className="flex items-center gap-2">
              <button
                type="button"
                aria-label="Attach files"
                title="Attach files"
                aria-disabled={actionsDisabled}
                onClick={() => {
                  if (actionsDisabled) {
                    notifyTurnLocked();
                    return;
                  }
                  uploader.pick();
                }}
                tabIndex={actionsDisabled ? -1 : 0}
                className={cn(
                  "inline-flex items-center justify-center h-9 w-9 transition-opacity",
                  actionsDisabled ? "opacity-40 cursor-not-allowed" : "opacity-70 hover:opacity-100"
                )}
                style={{
                  background: "none",
                  border: "none",
                  boxShadow: "none",
                  outline: "none",
                }}
              >
                <Paperclip className="h-5 w-5" />
              </button>
              <button
                type="button"
                aria-label="Generate image"
                title="Generate image"
                aria-disabled={actionsDisabled}
                onClick={() => {
                  if (actionsDisabled) {
                    notifyTurnLocked();
                    return;
                  }
                  setShowImgGen(true);
                }}
                tabIndex={actionsDisabled ? -1 : 0}
                className={cn(
                  "inline-flex items-center justify-center h-9 w-9 transition-opacity",
                  actionsDisabled ? "opacity-40 cursor-not-allowed" : "opacity-70 hover:opacity-100"
                )}
                style={{
                  background: "none",
                  border: "none",
                  boxShadow: "none",
                  outline: "none",
                }}
              >
                <ImagePlus className="h-5 w-5" />
              </button>
            </div>

              <Button
                type="button"
                onClick={send}
                aria-disabled={actionsDisabled || !value.trim()}
                tabIndex={actionsDisabled || !value.trim() ? -1 : 0}
                size="sm"
                className={cn(
                  "h-9 px-5 mr-[8px] rounded-full font-medium text-sm transition-opacity",
                  (actionsDisabled || !value.trim()) ? "opacity-50 cursor-not-allowed" : ""
                )}
              style={{
                background: "var(--accent-strong)",
                color: "#fff",
                boxShadow: "none",
              }}
            >
              Send
            </Button>
          </div>
          {turnLocked && (
            <div className="flex items-center gap-2 px-[8px] pb-[6px]" aria-live="polite">
              <span className="h-2 w-2 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-xs opacity-70" style={{ color: "var(--muted)" }}>
                Assistant is responding…
              </span>
            </div>
          )}
        </div>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
    </>
  );
}

export default Composer;
