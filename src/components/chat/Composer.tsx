import { useEffect, useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send } from "lucide-react";

function readCssVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

export function Composer({
  onSend,
  prefill,
  onPrefillConsumed,
}: {
  onSend: (t: string) => void;
  prefill?: string;
  onPrefillConsumed?: () => void;
}) {
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const [value, setValue] = useState("");
  const [sending, setSending] = useState(false);

  const autoResize = useCallback(() => {
    const ta = ref.current;
    if (!ta) return;
    // collapse then grow to fit, capped at ~40vh to avoid taking over the screen
    ta.style.height = "0px";
    const cap = typeof window !== "undefined" ? Math.round(window.innerHeight * 0.4) : 300;
    ta.style.height = Math.min(ta.scrollHeight, cap) + "px";
  }, []);

  useEffect(() => {
    if (prefill && prefill !== value) {
      setValue(prefill);
      setTimeout(() => {
        ref.current?.focus();
        autoResize();
      }, 0);
      onPrefillConsumed && onPrefillConsumed();
    }
  }, [prefill]);

  useEffect(() => {
    autoResize();
  }, [value, autoResize]);

  function send() {
    const v = value.trim();
    if (!v) return;
    setSending(true);
    onSend(v);
    setValue("");
    setTimeout(() => setSending(false), 200);
  }

  const accentStrong = readCssVar("--accent-strong", "#2f2f2f");
  const isDark = typeof window !== "undefined" ? document.documentElement.classList.contains("dark") : false;
  // srgb mixing is more broadly supported than oklab
  const bg = isDark ? "color-mix(in srgb, var(--panel-bg) 86%, black 14%)" : "#ffffff"; // white in light mode
  const ink = isDark ? readCssVar("--text", "#ffffff") : "#000000";

  return (
    <div
      data-composer-root
      className="w-full max-w-none mx-0 flex items-end gap-2 rounded-2xl border px-[var(--composer-pad-x,12px)] py-[var(--composer-pad-y,12px)]"
      style={{
        margin: 0,
        background: bg,
        borderColor: "var(--panel-bezel)",
        // strong floaty shadow so it "sits above" the card beneath
        boxShadow: "0 14px 34px rgba(0,0,0,0.28), 0 4px 10px rgba(0,0,0,0.22)",
        backgroundClip: "padding-box",
      }}
    >
      <Textarea
        ref={ref}
        value={value}
        rows={1}
        onInput={autoResize}
        onChange={(e) => setValue(e.target.value)}
        placeholder="Write a message…"
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
        className="block w-full resize-none overflow-hidden rounded-xl border-0 bg-transparent focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2"
        style={{
          color: ink,
          outlineColor: "var(--accent-weak)",
          maxHeight: "40vh",
          padding: "var(--composer-pad-y, 12px) var(--composer-pad-x, 16px)",
        }}
      />

      <div data-send-wrap className="shrink-0 m-0">
        <Button
          type="button"
          onClick={send}
          disabled={sending || !value.trim()}
          size="icon"
          className="relative grid h-11 w-11 place-items-center rounded-2xl border focus:outline-none m-0"
          style={{
            // glossy cap + jewel body tied to accent
            background:
              "radial-gradient(120% 120% at 30% 12%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.38) 10%, rgba(255,255,255,0.0) 36%), " +
              `linear-gradient(180deg, ${accentStrong} 0%, color-mix(in srgb, ${accentStrong} 85%, black 15%) 100%)`,
            color: "#fff",
            borderColor: "color-mix(in srgb, var(--accent-strong) 70%, white 30%)",
            boxShadow:
              "inset 0 1px rgba(255,255,255,0.35), inset 0 -8px 12px rgba(0,0,0,0.28), 0 8px 18px color-mix(in srgb, var(--accent-strong) 55%, black 45%)",
            outlineColor: "var(--accent-weak)",
          }}
          aria-label="Send"
        >
          <Send className="h-5 w-5" />
          {/* tiny sparkle */}
          <span
            aria-hidden
            className="pointer-events-none absolute -top-0.5 left-1 block h-2 w-2 rounded-full"
            style={{
              background:
                "radial-gradient(100% 100% at 50% 50%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.0) 70%)",
              filter: "blur(0.2px)",
            }}
          />
        </Button>
      </div>
    </div>
  );
}

export default Composer;
