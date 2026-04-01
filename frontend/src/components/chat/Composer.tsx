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
import { Send, Sparkles, ImagePlus, Paperclip, Plus, X, FileText } from "lucide-react";
import { ModelProvider } from "@/Providers/ModelProvider";
import api from "@/lib/api";

import {
  CHAT_COMPOSER_SEND_EDGE_INSET_CLASS,
  CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS,
} from "@/features/chat/chatLane";

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


function inferProjectIdFromLocation(fallback = 1): number {
  if (typeof window === "undefined") return fallback;
  const path = window.location.pathname || "";
  // Common shapes: /projects/:id, /project/:id, /p/:id
  const m = path.match(/\/(?:projects?|p)\/(\d+)/i);
  if (!m) return fallback;
  const n = Number(m[1]);
  return Number.isFinite(n) ? n : fallback;
}

function toAbsoluteMediaUrl(srcUrl: string) {
  if (!srcUrl) return srcUrl;
  if (srcUrl.startsWith("http://") || srcUrl.startsWith("https://")) return srcUrl;

  // Prefer the API base if present; otherwise fall back to same-origin.
  const base = (import.meta as any)?.env?.VITE_API_BASE_URL || "";
  if (base) return `${base}${srcUrl.startsWith("/") ? "" : "/"}${srcUrl}`;

  if (typeof window === "undefined") return srcUrl;
  const origin = window.location.origin;
  return `${origin}${srcUrl.startsWith("/") ? "" : "/"}${srcUrl}`;
}

function buildChatAttachmentMessage(args: {
  kind: "image" | "document";
  src_url: string;
  filename: string;
  id?: string;
  text?: string;
}): string {
  const { kind, src_url, filename, id, text } = args;
  const abs = toAbsoluteMediaUrl(src_url);

  // Primary marker is used by the backend worker to resolve media in the DB.
  // NOTE: this must remain `cfy-media:<kind>:<uuid>` for the worker regex.
  const media = id ? `<!-- cfy-media:${kind}:${id} -->` : "";

  // UI-only metadata: ChatBubble will read these to render a polished attachment tile.
  // These are hidden comments (never shown to users).
  const src = abs ? `<!-- cfy-media-src:${abs} -->` : "";
  const name = filename ? `<!-- cfy-media-name:${filename} -->` : "";

  const body = (text || "").trim();

  // Message content MUST be non-empty; if there is no body text, keep at least the primary marker.
  return [media || "<!-- cfy-media:missing-id -->", src, name, body].filter(Boolean).join("\n\n").trim();
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
  onSend: (t: string) => void | Promise<void>;
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

  const imageInputRef = useRef<HTMLInputElement | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const [uploading, setUploading] = useState(false);

  const [addMenuOpen, setAddMenuOpen] = useState(false);
  const addMenuRef = useRef<HTMLDivElement | null>(null);

  type DraftAttachment = {
    id: string;
    file: File;
    kind: "image" | "document";
    previewUrl?: string; // only for images
  };

  const [draftAttachments, setDraftAttachments] = useState<DraftAttachment[]>([]);

  // Revoke blob URLs on unmount
  useEffect(() => {
    return () => {
      for (const a of draftAttachments) {
        if (a.previewUrl) {
          try { URL.revokeObjectURL(a.previewUrl); } catch {}
        }
      }
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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

  useEffect(() => {
    if (!addMenuOpen) return;

    function onKeyDown(e: KeyboardEvent) {
      if (e.key === "Escape") setAddMenuOpen(false);
    }

    function onMouseDown(e: MouseEvent) {
      const el = addMenuRef.current;
      if (!el) return;
      if (e.target instanceof Node && el.contains(e.target)) return;
      setAddMenuOpen(false);
    }

    window.addEventListener("keydown", onKeyDown);
    window.addEventListener("mousedown", onMouseDown);
    return () => {
      window.removeEventListener("keydown", onKeyDown);
      window.removeEventListener("mousedown", onMouseDown);
    };
  }, [addMenuOpen]);

  function stageFiles(files: FileList | File[]) {
    const arr = Array.from(files || []);
    if (!arr.length) return;

    setDraftAttachments((prev) => {
      const next: DraftAttachment[] = [...prev];
      for (const f of arr) {
        // rudimentary client-side dedupe to reduce accidental repeats in the same draft
        const already = next.some((x) => x.file.name === f.name && x.file.size === f.size && x.file.type === f.type);
        if (already) continue;

        const isImage = f.type.startsWith("image/");
        const kind: DraftAttachment["kind"] = isImage ? "image" : "document";
        const previewUrl = isImage ? URL.createObjectURL(f) : undefined;
        next.push({
          id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
          file: f,
          kind,
          previewUrl,
        });
      }
      return next;
    });
  }

  function removeDraftAttachment(id: string) {
    setDraftAttachments((prev) => {
      const target = prev.find((p) => p.id === id);
      if (target?.previewUrl) {
        try { URL.revokeObjectURL(target.previewUrl); } catch {}
      }
      return prev.filter((p) => p.id !== id);
    });
  }

  async function uploadOneAttachment(att: DraftAttachment): Promise<{
    kind: "image" | "document";
    src_url: string;
    filename: string;
    id?: string;
  } | null> {
    const file = att.file;
    if (!file) return null;

    // Prefer explicit threadId prop when present; projectId is inferred from the URL as a best-effort fallback.
    const projectId = inferProjectIdFromLocation(1);
    const tid = typeof threadId === "number" ? threadId : undefined;

    const isImage = att.kind === "image";
    const endpoint = isImage ? "/api/media/upload/image" : "/api/media/upload/file";

    const form = new FormData();
    form.append("project_id", String(projectId));
    if (tid !== undefined) form.append("thread_id", String(tid));
    form.append("file", file);

    try {
      const res = await api.post(endpoint, form, {
        headers: { "Content-Type": "multipart/form-data" },
      });

      const data = (res as any)?.data ?? res;
      const src_url = data?.src_url;
      const filename = data?.filename ?? file.name;
      const id = data?.id;

      if (!src_url) {
        console.error("Upload succeeded but no src_url returned", data);
        return null;
      }

      return {
        kind: isImage ? "image" : "document",
        src_url: toAbsoluteMediaUrl(String(src_url)),
        filename,
        id,
      };
    } catch (err) {
      console.error("Upload failed", err);
      return null;
    }
  }

  function buildChatAttachmentBatchMessage(args: {
    attachments: { kind: "image" | "document"; src_url: string; filename: string; id?: string }[];
    text?: string;
  }): string {
    const { attachments, text } = args;
    const parts: string[] = [];

    for (const a of attachments) {
      const media = a.id ? `<!-- cfy-media:${a.kind}:${a.id} -->` : "<!-- cfy-media:missing-id -->";
      const src = a.src_url ? `<!-- cfy-media-src:${toAbsoluteMediaUrl(a.src_url)} -->` : "";
      const name = a.filename ? `<!-- cfy-media-name:${a.filename} -->` : "";
      parts.push([media, src, name].filter(Boolean).join("\n"));
    }

    const body = (text || "").trim();
    if (body) parts.push(body);

    // Ensure non-empty
    return parts.filter(Boolean).join("\n\n").trim() || "<!-- cfy-media:missing-id -->";
  }

  function onPickImageClick() {
    imageInputRef.current?.click();
  }

  function onPickFileClick() {
    fileInputRef.current?.click();
  }

  // Send handler: uploads attachments (if any) and sends message.
  async function send() {
    if (sending || uploading) return;
    if (addMenuOpen) setAddMenuOpen(false);

    const bodyText = value.trim();
    const hasAttachments = draftAttachments.length > 0;
    if (!bodyText && !hasAttachments) return;

    setSending(true);
    setUploading(hasAttachments);

    try {
      let uploaded: { kind: "image" | "document"; src_url: string; filename: string; id?: string }[] = [];

      if (hasAttachments) {
        // Upload sequentially to avoid stampeding the server and to keep ordering predictable.
        for (const att of draftAttachments) {
          const up = await uploadOneAttachment(att);
          if (up) uploaded.push(up);
        }
      }

      const msg = hasAttachments
        ? buildChatAttachmentBatchMessage({ attachments: uploaded, text: bodyText })
        : bodyText;

      await onSend(msg);

      // Clear draft text + attachments after successful send
      setValue("");
      setDraftAttachments((prev) => {
        for (const a of prev) {
          if (a.previewUrl) {
            try { URL.revokeObjectURL(a.previewUrl); } catch {}
          }
        }
        return [];
      });

      if (storageKey && typeof window !== "undefined") {
        try {
          sessionStorage.removeItem(storageKey);
        } catch {
          // ignore storage errors
        }
      }

      setTimeout(() => ref.current?.focus(), 0);
    } finally {
      setUploading(false);
      setTimeout(() => setSending(false), 200);
    }
  }

  const accentStrong = readCssVar("--accent-strong", "#2f2f2f");
  const isDark = typeof window !== "undefined" ? document.documentElement.classList.contains("dark") : false;
  // srgb mixing is more broadly supported than oklab
  const bg = isDark ? "color-mix(in srgb, var(--panel-bg) 86%, black 14%)" : "#ffffff"; // white in light mode
  const ink = isDark ? readCssVar("--text", "#ffffff") : "#000000";

  // Presentation: ModelProvider wraps the composer so model config can be per-composer
  return (
    // ModelProvider: defaultModel="**REPLACE**" sets the per-composer default model.
    // If provider expects a different prop name, update accordingly.
    <ModelProvider>
      <div
        data-composer-root
        className="w-full max-w-none mx-0 flex items-end gap-2 rounded-2xl border px-[var(--composer-pad-x,12px)] py-[var(--composer-pad-y,12px)] pr-[max(var(--composer-pad-x,12px),16px)]"
        style={{
          margin: 0,
          background: bg,
          borderColor: "var(--panel-bezel)",
          // strong floaty shadow so it "sits above" the card beneath
          boxShadow: "0 14px 34px rgba(0,0,0,0.28), 0 4px 10px rgba(0,0,0,0.22)",
          backgroundClip: "padding-box",
        }}
      >
        {/* Render draft attachments, if any */}
        {draftAttachments.length > 0 && (
          <div className="w-full flex flex-wrap gap-2 pb-2">
            {draftAttachments.map((att) => (
              <div
                key={att.id}
                className="relative overflow-hidden rounded-xl border border-black/10 dark:border-white/10 bg-black/5 dark:bg-white/5"
                style={{ width: 96, height: 72 }}
                title={att.file.name}
              >
                {att.kind === "image" ? (
                  <img
                    src={att.previewUrl}
                    alt={att.file.name}
                    className="h-full w-full object-cover"
                    loading="lazy"
                  />
                ) : (
                  <div className="h-full w-full flex items-center justify-center">
                    <FileText className="h-6 w-6 opacity-70" />
                  </div>
                )}

                <button
                  type="button"
                  aria-label="Remove attachment"
                  onClick={() => removeDraftAttachment(att.id)}
                  className="absolute right-1 top-1 grid h-6 w-6 place-items-center rounded-full bg-black/50 text-white"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            ))}
          </div>
        )}
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
            void send();
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

      <div
        data-send-wrap
        className={`shrink-0 m-0 flex gap-2 ${CHAT_COMPOSER_SEND_EDGE_INSET_CLASS} ${CHAT_COMPOSER_CONTROLS_BOTTOM_GAP_CLASS}`}
      >
        {/* Hidden file inputs (triggered by the attachment buttons) */}
        <input
          ref={imageInputRef}
          type="file"
          accept="image/*"
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            const files = e.target.files;
            e.currentTarget.value = "";
            if (files && files.length) stageFiles(files);
          }}
        />
        <input
          ref={fileInputRef}
          type="file"
          // Allow docs too; backend route is /api/media/upload/file
          accept="application/pdf,text/plain,text/markdown,.md,.txt"
          multiple
          style={{ display: "none" }}
          onChange={(e) => {
            const files = e.target.files;
            e.currentTarget.value = "";
            if (files && files.length) stageFiles(files);
          }}
        />

        {/* Add menu (attachments + creation) */}
        <div className="relative" ref={addMenuRef}>
          <Button
            type="button"
            size="icon"
            aria-label="Add"
            title="Add"
            onClick={() => setAddMenuOpen((v) => !v)}
            disabled={sending || uploading}
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
            <Plus className="h-5 w-5" />
          </Button>

          {addMenuOpen && (
            <div
              role="menu"
              aria-label="Add menu"
              className="absolute bottom-14 left-0 z-50 min-w-[220px] overflow-hidden rounded-xl border border-black/10 dark:border-white/10 bg-white/95 dark:bg-black/80 shadow-2xl"
              style={{ backdropFilter: "blur(10px)" }}
            >
              <div className="px-3 py-2 text-[11px] uppercase tracking-wide opacity-70">Attach</div>

              <button
                type="button"
                role="menuitem"
                className="w-full px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10 flex items-center gap-2"
                onClick={() => {
                  setAddMenuOpen(false);
                  onPickImageClick();
                }}
              >
                <ImagePlus className="h-4 w-4" />
                <span>Attach image</span>
              </button>

              <button
                type="button"
                role="menuitem"
                className="w-full px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10 flex items-center gap-2"
                onClick={() => {
                  setAddMenuOpen(false);
                  onPickFileClick();
                }}
              >
                <Paperclip className="h-4 w-4" />
                <span>Attach file</span>
              </button>

              <div className="my-1 h-px bg-black/10 dark:bg-white/10" />
              <div className="px-3 py-2 text-[11px] uppercase tracking-wide opacity-70">Create</div>

              <button
                type="button"
                role="menuitem"
                className="w-full px-3 py-2 text-left text-sm hover:bg-black/5 dark:hover:bg-white/10 flex items-center gap-2"
                onClick={() => {
                  setAddMenuOpen(false);
                  // If an ImageGen surface exists elsewhere, it should listen for this event.
                  window.dispatchEvent(
                    new CustomEvent("cfy:imagegen:open", { detail: { source: "composer" } })
                  );
                }}
              >
                <Sparkles className="h-4 w-4" />
                <span>Generate image</span>
              </button>
            </div>
          )}
        </div>

      {/* Open Prompt Library Button: visually prominent, similar styling to Send button */}
        <Button
          type="button"
          size="icon"
          aria-label="Open Prompt Library"
          title="Prompt Library"
          onClick={() => window.dispatchEvent(new CustomEvent("cfy:workspace:togglePromptLibrary", { detail: { source: "composer" } }))}
          disabled={sending || uploading}
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
          onClick={() => void send()}
          disabled={sending || uploading || (!value.trim() && draftAttachments.length === 0)}
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
