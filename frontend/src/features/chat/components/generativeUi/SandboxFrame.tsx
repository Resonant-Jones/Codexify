/**
 * Sandboxed generative UI frame.
 *
 * Renders model-authored HTML/CSS/JS inside an isolated iframe. The frame is
 * the containment boundary: `sandbox="allow-scripts"` with no
 * `allow-same-origin`, so it runs in an opaque origin with no access to host
 * `storage`, cookies, `document`, or any host API.
 *
 * Note `src-tauri/tauri.conf.json` declares `"csp": null`, so this iframe
 * sandbox attribute is the load-bearing boundary and must not be weakened.
 *
 * The host bridge accepts exactly two validated actions and grants no other
 * capability. See docs/architecture/generative-ui-contract.md
 */
import React from "react";
import type { SandboxUiArtifact } from "./artifactCodec";

export const BRIDGE_CHANNEL = "cfy-ui";
export const BRIDGE_ACTIONS = ["resize", "send_prompt"] as const;

/** Frame height bounds. Generated code cannot grow the bubble without limit. */
export const MIN_FRAME_HEIGHT = 80;
export const MAX_FRAME_HEIGHT = 640;
export const DEFAULT_FRAME_HEIGHT = 200;

/** Generated code cannot flood the thread through the bridge. */
export const MAX_BRIDGE_PROMPT_CHARS = 2000;

const SESSION_TOKEN = "__CFY_UI_SESSION__";

/**
 * Codexify builds this CSP and injects it before any generated content.
 *
 * `default-src 'none'` plus an explicit allowlist denies all network egress:
 * generated UI cannot fetch remote modules, fonts, tiles, or APIs. This is a
 * deliberate tightening of upstream, which permits four public CDNs. Codexify
 * therefore ships no CDN importmap.
 */
const FRAME_CSP = [
  "default-src 'none'",
  "script-src 'unsafe-inline'",
  "style-src 'unsafe-inline'",
  "img-src data: blob:",
  "connect-src 'none'",
  "form-action 'none'",
  "base-uri 'none'",
  "frame-src 'none'",
].join("; ");

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Prevent a generated payload from closing its own script/style element. */
function escapeRawElementText(value: string): string {
  return value.replace(/<\/(script|style)/gi, "<\\/$1");
}

function clampHeight(value: unknown): number {
  const parsed = typeof value === "number" ? value : Number(value);
  if (!Number.isFinite(parsed)) return DEFAULT_FRAME_HEIGHT;
  return Math.min(Math.max(Math.round(parsed), MIN_FRAME_HEIGHT), MAX_FRAME_HEIGHT);
}

/**
 * The in-frame bridge. This is the only path from generated code to the host.
 *
 * It posts to `"*"` because an opaque-origin frame cannot discover the host's
 * origin. That is safe only because every message is validated host-side by
 * source, origin, session, and schema before it can cause any effect, and
 * because no credential ever travels through this channel.
 */
function bridgeScript(session: string): string {
  return `(function(){
  var SESSION = ${JSON.stringify(session)};
  function post(action, payload) {
    try {
      parent.postMessage({ channel: "cfy-ui", session: SESSION, action: action, payload: payload || {} }, "*");
    } catch (err) {}
  }
  function clamp(height) {
    var n = Number(height);
    if (!isFinite(n)) return;
    post("resize", { height: Math.min(Math.max(Math.round(n), 80), 640) });
  }
  window.addEventListener("message", function (ev) {
    if (ev.source !== parent) return;
    var d = ev.data;
    if (!d || d.channel !== "cfy-ui" || d.session !== SESSION) return;
    if (d.action === "set_height") clamp(d.payload && d.payload.height);
  });
  Object.defineProperty(window, "cfyUI", {
    value: Object.freeze({
      sendPrompt: function (text) {
        if (typeof text !== "string") return;
        post("send_prompt", { text: text.slice(0, ${MAX_BRIDGE_PROMPT_CHARS}) });
      },
      resize: clamp,
      resizeTo: function (el) {
        if (!el) return;
        var h = el.scrollHeight || (el.getBoundingClientRect ? el.getBoundingClientRect().height : 0);
        clamp(h);
      }
    }),
    writable: false,
    configurable: false
  });
})();`;
}

/**
 * Build the complete frame document.
 *
 * Exported as a pure function so containment can be asserted in unit tests
 * without a live iframe.
 */
export function buildSandboxDocument(artifact: SandboxUiArtifact, session: string): string {
  const title = artifact.title ? escapeHtml(artifact.title) : "Generated interface";
  const style = artifact.css?.trim() ? `<style>\n${escapeRawElementText(artifact.css)}\n</style>` : "";
  const script = artifact.js?.trim()
    ? `<script>\ntry {\n${escapeRawElementText(artifact.js)}\n} catch (err) {\n  console.error("[cfy-ui] generated script failed", err);\n}\n</script>`
    : "";

  return `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="${FRAME_CSP}">
<title>${title}</title>
<style>
  :root { color-scheme: light dark; }
  html, body {
    margin: 0;
    padding: 0.75rem;
    background: transparent;
    color: CanvasText;
    font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
    font-size: 14px;
    line-height: 1.45;
    overflow-wrap: anywhere;
  }
  button, input, select, textarea { font: inherit; }
  * { box-sizing: border-box; }
</style>
${style}
</head>
<body>
${artifact.html}
<script>\n${bridgeScript(session)}\n</script>
${script}
</body>
</html>`;
}

export type SandboxBridgeHandler = {
  /** Called only for a fully validated `send_prompt`. */
  onSendPrompt?: (text: string) => void;
};

export type SandboxFrameProps = {
  artifact: SandboxUiArtifact;
  onSendPrompt?: (text: string) => void;
  onHeightChange?: (height: number) => void;
};

/**
 * A single isolated generative UI frame.
 *
 * Falls back to an inline notice if the frame cannot be constructed, so a
 * broken artifact never blocks the surrounding message.
 */
const SandboxFrame: React.FC<SandboxFrameProps> = ({ artifact, onSendPrompt, onHeightChange }) => {
  const frameRef = React.useRef<HTMLIFrameElement | null>(null);
  const [session] = React.useState(
    () => `ui-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 12)}`
  );
  const [height, setHeight] = React.useState(() =>
    clampHeight(artifact.initialHeight ?? DEFAULT_FRAME_HEIGHT)
  );

  const sessionRef = React.useRef(session);
  sessionRef.current = session;
  const promptHandlerRef = React.useRef<SandboxBridgeHandler["onSendPrompt"]>(undefined);
  promptHandlerRef.current = onSendPrompt;
  const heightHandlerRef = React.useRef<SandboxBridgeHandler["onSendPrompt"]>(undefined);
  heightHandlerRef.current = onHeightChange;

  const doc = React.useMemo(() => buildSandboxDocument(artifact, session), [artifact, session]);

  React.useEffect(() => {
    function handleMessage(event: MessageEvent) {
      // Source binding: only this frame's own window may talk to us.
      if (event.source !== frameRef.current?.contentWindow) return;
      // Opaque origin of a sandboxed frame serializes to "null".
      if (event.origin !== "null") return;

      const data = event.data;
      if (!data || typeof data !== "object") return;
      if (data.channel !== BRIDGE_CHANNEL) return;
      // Session binding: reject frames or stale messages from another mount.
      if (data.session !== sessionRef.current) return;

      const payload = (data.payload && typeof data.payload === "object" ? data.payload : {}) as Record<string, unknown>;

      if (data.action === "resize") {
        const next = clampHeight(payload.height);
        setHeight(next);
        heightHandlerRef.current?.(next);
        return;
      }

      if (data.action === "send_prompt") {
        const text = typeof payload.text === "string" ? payload.text.trim() : "";
        if (!text || text.length > MAX_BRIDGE_PROMPT_CHARS) return;
        promptHandlerRef.current?.(text);
        return;
      }

      // Unknown actions are ignored, never partially applied.
    }

    window.addEventListener("message", handleMessage);
    return () => window.removeEventListener("message", handleMessage);
  }, []);

  const label = artifact.title || "Generated interface";

  return (
    <div
      className="max-w-[min(34rem,100%)] overflow-hidden rounded-xl border"
      style={{ borderColor: "color-mix(in srgb, var(--panel-border) 80%, transparent)" }}
    >
      <iframe
        ref={frameRef}
        title={label}
        data-testid="generative-ui-sandbox-frame"
        // Containment boundary. Do not add allow-same-origin, forms, popups,
        // top-navigation, modals, or downloads.
        sandbox="allow-scripts"
        srcDoc={doc}
        style={{ width: "100%", height, border: 0, display: "block", background: "transparent" }}
      />
    </div>
  );
};

export default SandboxFrame;