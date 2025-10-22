import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";

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
  const effectiveSending = isSending ?? internalSending;
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
    <div className="flex items-center gap-2 rounded-2xl border p-2 shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Write a message…"
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
  );
}

export default Composer;
