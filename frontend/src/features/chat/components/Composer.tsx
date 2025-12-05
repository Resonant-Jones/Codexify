import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Paperclip, ImagePlus } from "lucide-react";
import useUploader from "@/hooks/useUploader";

import { ImageGenModal } from "@/components/modals/ImageGenModal";

export function Composer({
  onSend,
  prefill,
  onPrefillConsumed,
  threadId,
  isSending,
}: {
  onSend: (t: string) => Promise<void> | void;
  prefill?: string;
  onPrefillConsumed?: () => void;
  threadId?: number;
  isSending?: boolean;
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
  const effectiveSending = isSending ?? internalSending;

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

  const uploader = useUploader({
    tag: "chat",
    onImages: (items) => {
      try { window.dispatchEvent(new CustomEvent("cfy:gallery:add", { detail: { items } })); } catch {}
      try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Added ${items.length} image${items.length===1?"":"s"} to Gallery` } })); } catch {}
    },
    onDocuments: (items) => {
      try { window.dispatchEvent(new CustomEvent("cfy:documents:add", { detail: { items } })); } catch {}
      try { window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message: `Added ${items.length} document${items.length===1?"":"s"}` } })); } catch {}
    },
    onAnyUpload: () => { try { localStorage.setItem("cfy.hasUserUpload", "true"); } catch {} },
  });

  function onPaste(e: React.ClipboardEvent<HTMLTextAreaElement>) {
    const files = e.clipboardData?.files;
    if (files && files.length > 0) {
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
    } finally {
      setInternalSending(false);
    }
  }
  return (
    <>
      <div className="flex flex-col flex-1 w-full p-[4px]">
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
                if (e.key === "Enter" && !e.shiftKey && !effectiveSending) {
                  e.preventDefault();
                  send();
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
                onClick={uploader.pick}
                className="inline-flex items-center justify-center h-9 w-9 opacity-70 hover:opacity-100 transition-opacity"
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
                onClick={() => setShowImgGen(true)}
                className="inline-flex items-center justify-center h-9 w-9 opacity-70 hover:opacity-100 transition-opacity"
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
              disabled={effectiveSending || !value.trim()}
              size="sm"
              className="h-9 px-5 mr-[8px] rounded-full disabled:opacity-50 font-medium text-sm transition-opacity"
              style={{
                background: "var(--accent-strong)",
                color: "#fff",
                boxShadow: "none",
              }}
            >
              Send
            </Button>
          </div>
        </div>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
    </>
  );
}

export default Composer;
