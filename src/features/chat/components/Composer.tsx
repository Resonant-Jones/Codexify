import { useEffect, useRef, useState } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";

export function Composer({ onSend, prefill, onPrefillConsumed }: { onSend: (t: string) => void; prefill?: string; onPrefillConsumed?: () => void }) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);
  useEffect(() => {
    if (prefill && prefill !== value) {
      setValue(prefill);
      setTimeout(() => ref.current?.focus(), 0);
      onPrefillConsumed && onPrefillConsumed();
    }
  }, [prefill]);
  function send() {
    const v = value.trim();
    if (!v) return;
    setSending(true);
    onSend(v);
    setValue("");
    setTimeout(() => setSending(false), 200);
  }
  return (
    <div className="flex items-center gap-2 rounded-2xl border p-2 shadow-sm" style={{ background: "var(--panel-bg)", borderColor: "var(--panel-border)" }}>
      <Textarea
        ref={ref}
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Write a message…"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
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
        disabled={sending || !value.trim()}
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

