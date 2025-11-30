import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Paperclip, ImagePlus } from "lucide-react";
import useUploader from "@/hooks/useUploader";
import { ProviderSelect } from "@/components/ProviderSelect";
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
      <div className="mb-2 flex items-center justify-between gap-2">
        <ProviderSelect />
        {/* Reserved space for future controls (e.g., depth selector / RAG controls) */}
        <div className="flex items-center gap-1" />
      </div>

      <div
        className="flex items-end gap-2 rounded-2xl border p-2 shadow-sm"
        style={{
          background: "var(--panel-bg)",
          borderColor: "var(--panel-border)"
        }}
        onDrop={uploader.onDrop}
        onDragOver={uploader.onDragOver}
      >
        <div className="flex items-center gap-1">
          <button
            type="button"
            aria-label="Attach files"
            title="Attach files"
            onClick={uploader.pick}
            className="icon-inline h-10 w-10"
            style={{ borderRadius: "var(--radius-micro)" }}
          >
            <Paperclip className="h-4 w-4" />
          </button>
          <button
            type="button"
            aria-label="Generate image"
            title="Generate image"
            onClick={() => setShowImgGen(true)}
            className="icon-inline h-10 w-10"
            style={{ borderRadius: "var(--radius-micro)" }}
          >
            <ImagePlus className="h-4 w-4" />
          </button>
        </div>

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
          className="min-h-[44px] max-h-44 flex-1 resize-none border-0 bg-transparent px-2 py-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ color: "var(--text)", outlineColor: "var(--accent-weak)" }}
        />
        <Button
          type="button"
          onClick={send}
          disabled={effectiveSending || !value.trim()}
          size="icon"
          className="h-11 w-11 grid place-items-center rounded-full shadow-sm disabled:opacity-60"
          style={{
            background: "var(--accent-strong)",
            color: "var(--pill-active-text, #fff)",
            outlineColor: "var(--accent-weak)",
          }}
        >
          <Send className="h-4 w-4" />
        </Button>
        </div>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
    </>
  );
}

export default Composer;
