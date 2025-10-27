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
  const [value, setValue] = useState("");
  const [internalSending, setInternalSending] = useState(false);
  const [showImgGen, setShowImgGen] = useState(false);
  const effectiveSending = isSending ?? internalSending;

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
    } finally {
      setInternalSending(false);
    }
  }
  return (
    <>
      <div className="flex items-center gap-2 mb-2">
        <ProviderSelect />
      </div>
      <div
        className="flex items-center gap-2 rounded-2xl border p-2 shadow-sm"
        style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}
        onDrop={uploader.onDrop}
        onDragOver={uploader.onDragOver}
      >
        <button
          type="button"
          aria-label="Attach files"
          title="Attach files"
          onClick={uploader.pick}
          className="grid place-items-center h-10 w-10 rounded-xl border"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <Paperclip className="h-4 w-4" />
        </button>
        <button
          type="button"
          aria-label="Generate image"
          title="Generate image"
          onClick={() => setShowImgGen(true)}
          className="grid place-items-center h-10 w-10 rounded-xl border"
          style={{ borderColor: "var(--panel-border)" }}
        >
          <ImagePlus className="h-4 w-4" />
        </button>
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
          className="min-h-[44px] max-h-44 resize-none border-0 bg-transparent px-1 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
          style={{ color: "var(--text)", outlineColor: "var(--accent-weak)" }}
        />
        <Button
          type="button"
          onClick={send}
          disabled={effectiveSending || !value.trim()}
          size="icon"
          className="h-11 w-11 grid place-items-center"
          style={{ background: "#2f2f2f", color: "#fff", borderRadius: "22px", outlineColor: "var(--accent-weak)" }}
        >
          <Send className="h-4 w-4" />
        </Button>
      </div>
      <ImageGenModal open={showImgGen} onOpenChange={setShowImgGen} />
    </>
  );
}

export default Composer;
