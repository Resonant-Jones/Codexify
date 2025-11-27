/**
 * Composer.tsx
 *
 * Purpose:
 * Renders the message composer (text entry box + send button) used in the chat UI.
 * This component is the primary surface for user input in conversational flows and
 * encapsulates autosizing behavior, keyboard shortcuts, optimistic send behavior,
 * theming, and an optional ModelProvider wrapper to scope model configuration.
 *
 * Responsibilities:
 *  - Provide an accessible, resizable textarea that honors Enter-to-send and
 *    Shift+Enter for newline.
 *  - Expose a simple `onSend` callback and support a `prefill` prop for guided
 *    prompts or completions.
 *  - Render a prominent send button that conveys affordance and state (sending).
 *  - Be theme-aware (reads CSS variables) and keep presentation concerns local.
 *
 * Integration notes:
 *  - The Composer currently wraps itself with `ModelProvider` so model config can
 *    be set per-composer (useful for per-chat model overrides). If multiple
 *    composers should share a provider, move the provider higher in the tree.
 *  - `onSend` is called synchronously; consider returning/awaiting a Promise from
 *    `onSend` if you want to reflect server-acknowledged sends instead of optimistic.
 */

import { useEffect, useRef, useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Send, Sparkles } from "lucide-react";
import { ModelProvider } from "@/Providers/ModelProvider";
import api from "@/lib/api";

/**
 * Read a CSS variable from the document root with a fallback.
 * This utility is server-safe (returns fallback if `window` is undefined).
 *
 * @param {string} name - CSS variable name (eg. '--accent-strong')
 * @param {string} fallback - fallback value used if CSS var is not available
 * @returns {string}
 */

function readCssVar(name: string, fallback: string) {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}


/**
 * Composer component
 *
 * Props:
 * @param {{
 *   onSend: (text: string) => void;
 *   prefill?: string;
 *   onPrefillConsumed?: () => void;
 *   threadId?: number;
 * }} props
 *
 * Notes:
 * - `onSend` is invoked with the trimmed message text. The current implementation
 *   calls `onSend` synchronously; if you switch to an async send pipeline, consider
 *   returning a Promise from `onSend` and awaiting it in `send()` so the UI can reflect
 *   server acknowledgement (success/failure).
 * - `prefill` is consumed once and triggers focus + auto-resize.
 */


export function Composer({
  onSend,
  prefill,
  onPrefillConsumed,
  threadId,
}: {
  onSend: (t: string) => void;
  prefill?: string;
  onPrefillConsumed?: () => void;
  threadId?: number;
})
// Refs & local state: textarea ref, value and sending flag
{
  const ref = useRef<HTMLTextAreaElement | null>(null);
  const storageKey = typeof threadId === "number" ? `cfy.composer.${threadId}` : null;
  const [value, setValue] = useState(() => {
    if (typeof window === "undefined" || !storageKey) return "";
    try {
      return sessionStorage.getItem(storageKey) ?? "";
    } catch {
      return "";
    }
  });
  const [sending, setSending] = useState(false);
  const prevKeyRef = useRef<string | null>(storageKey);

  // Auto-resize helper: expand textarea to fit content but cap at ~40vh
  const autoResize = useCallback(() => {
    const ta = ref.current;
    if (!ta) return;
    // collapse then grow to fit, capped at ~40vh to avoid taking over the screen
    ta.style.height = "0px";
    const cap = typeof window !== "undefined" ? Math.round(window.innerHeight * 0.4) : 300;
    ta.style.height = Math.min(ta.scrollHeight, cap) + "px";
  }, []);

// Handle `prefill` prop: set value, focus textarea and call onPrefillConsumed
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

  // When the active thread changes, hydrate from sessionStorage
  useEffect(() => {
    if (storageKey === prevKeyRef.current) return;
    prevKeyRef.current = storageKey;
    if (typeof window === "undefined") {
      if (!storageKey) setValue("");
      return;
    }
    if (!storageKey) {
      setValue("");
      return;
    }
    try {
      const cached = sessionStorage.getItem(storageKey) ?? "";
      setValue(cached);
    } catch {
      setValue("");
    }
  }, [storageKey]);

  // Persist drafts per-thread in sessionStorage
  useEffect(() => {
    if (!storageKey || typeof window === "undefined") return;
    try {
      if (value && value.trim()) {
        sessionStorage.setItem(storageKey, value);
      } else {
        sessionStorage.removeItem(storageKey);
      }
    } catch {
      // ignore storage errors
    }
  }, [storageKey, value]);

// Recompute textarea size when the value changes
  useEffect(() => {
    autoResize();
  }, [value, autoResize]);

  // Send handler: optimistic send (sets sending=true), clears input.
  // Consider awaiting a promise from onSend if you want server-confirmed sends.
  function send() {
    const v = value.trim();
    if (!v) return;
    setSending(true);
    onSend(v);
    setValue("");
    if (storageKey && typeof window !== "undefined") {
      try {
        sessionStorage.removeItem(storageKey);
      } catch {
        // ignore storage errors
      }
    }
    setTimeout(() => setSending(false), 200);
  }

  const accentStrong = readCssVar("--accent-strong", "#2f2f2f");
  const isDark = typeof window !== "undefined" ? document.documentElement.classList.contains("dark") : false;
  // srgb mixing is more broadly supported than oklab
  const bg = isDark ? "color-mix(in srgb, var(--panel-bg) 86%, black 14%)" : "#ffffff"; // white in light mode
  const ink = isDark ? readCssVar("--text", "#ffffff") : "#000000";

  // Presentation: ModelProvider wraps the composer so model config can be per-composer
  return (
    // ModelProvider: defaultModel="gpt-120b-oss" sets the per-composer default model.
    // If provider expects a different prop name, update accordingly.
    <ModelProvider>
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
        {/* Textarea: auto-resizes on input; Enter sends (unless Shift is held) */}
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

      <div data-send-wrap className="shrink-0 m-0 flex gap-2">
      {/* Open Prompt Library Button: visually prominent, similar styling to Send button */}
        <Button
          type="button"
          size="icon"
          aria-label="Open Prompt Library"
          title="Prompt Library"
          onClick={() => window.dispatchEvent(new CustomEvent("cfy:workspace:togglePromptLibrary", { detail: { source: "composer" } }))}
          className="relative grid h-11 w-11 place-items-center rounded-2xl border focus:outline-none m-0"
          style={{
            background:
              "radial-gradient(120% 120% at 30% 12%, rgba(255,255,255,0.95) 0%, rgba(255,255,255,0.38) 10%, rgba(255,255,255,0.0) 36%), " +
              `linear-gradient(180deg, ${accentStrong} 0%, color-mix(in srgb, ${accentStrong} 85%, black 15%) 100%)`,
            color: "#fff",
            borderColor: "color-mix(in srgb, var(--accent-strong) 70%, white 30%)",
            boxShadow:
              "inset 0 1px rgba(255,255,255,0.35), inset 0 -8px 12px rgba(0,0,0,0.28), 0 8px 18px color-mix(in srgb, var(--accent-strong) 55%, black 45%)",
            outlineColor: "var(--accent-weak)",
          }}
        >
          <Sparkles className="h-5 w-5" />
        </Button>

      {/* Send Button: visually prominent, shows disabled state while sending */}
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
    </ModelProvider>
  );
}

export default Composer;
