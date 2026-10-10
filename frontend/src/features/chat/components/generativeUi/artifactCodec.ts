/**
 * Generative UI artifact codec.
 *
 * A generative UI artifact rides inside canonical assistant message content as
 * an HTML comment marker, mirroring the `cfy-doc-tile` convention already
 * proven end to end by `lib/documentContext.ts`. Because the payload is base64url
 * (alphabet `A-Za-z0-9_-`), it cannot contain `>` and therefore cannot escape
 * an HTML-comment-delimited regex.
 *
 * Contract: docs/architecture/generative-ui-contract.md
 *
 * Artifacts are model-authored and therefore untrusted. Nothing in this module
 * grants a capability; it only decides whether an artifact is structurally
 * valid enough to hand to the renderer. An artifact that fails any check is
 * dropped, and the surrounding message renders as ordinary text.
 */

const MARKER_RE = /<!--\s*cfy-ui:([^>]*?)\s*-->/gi;
/**
 * A marker still streaming in has no closing `-->`, so MARKER_RE cannot match
 * it and the raw payload would be shown as text until the reply completes.
 *
 * `[^>]*$` is deliberate: neither wire encoding can contain `>`, so this only
 * matches a genuinely unterminated trailing marker and leaves prose that merely
 * mentions the prefix intact.
 */
const UNTERMINATED_MARKER_RE = /<!--\s*cfy-ui:[^>]*$/i;
const EXCESSIVE_BLANK_LINES_RE = /\n{3,}/g;

export const UI_ARTIFACT_MARKER_PREFIX = "cfy-ui";

/** Bounds chosen to reject absurd payloads before they reach the renderer. */
export const MAX_SANDBOX_HTML_CHARS = 120_000;
export const MAX_SANDBOX_STYLE_CHARS = 60_000;
export const MAX_SANDBOX_SCRIPT_CHARS = 80_000;
export const MAX_SANDBOX_TOTAL_CHARS = 260_000;
export const MAX_NATIVE_PROPS_CHARS = 20_000;
export const MAX_TITLE_CHARS = 200;

export type NativeUiArtifact = {
  version: 1;
  kind: "native";
  component: string;
  props: Record<string, unknown>;
};

export type SandboxUiArtifact = {
  version: 1;
  kind: "sandbox";
  title?: string;
  html: string;
  css?: string;
  js?: string;
  initialHeight?: number;
};

export type GenerativeUiArtifact = NativeUiArtifact | SandboxUiArtifact;

function normalizeString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function toBase64Url(input: string): string {
  const bytes = new TextEncoder().encode(input);
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/g, "");
}

function fromBase64Url(input: string): string | null {
  const normalized = normalizeString(input);
  if (!normalized) return null;
  try {
    const padded = normalized.replace(/-/g, "+").replace(/_/g, "/");
    const withPadding = `${padded}${"=".repeat((4 - (padded.length % 4)) % 4)}`;
    const binary = atob(withPadding);
    const bytes = new Uint8Array(binary.length);
    for (let index = 0; index < binary.length; index += 1) {
      bytes[index] = binary.charCodeAt(index);
    }
    return new TextDecoder().decode(bytes);
  } catch {
    return null;
  }
}

function encodePayload(payload: unknown): string {
  return toBase64Url(JSON.stringify(payload));
}

/**
 * Percent-encode a JSON payload.
 *
 * This is the model-facing wire format. Base64url is compact but models emit it
 * unreliably by hand, whereas percent-encoding JSON is a mechanical transform a
 * model gets right far more often. The alphabet excludes `>`, so it stays safe
 * inside an HTML comment, and it is trivially reversible.
 */
export function encodeUiArtifactPayload(payload: unknown): string {
  return encodeURIComponent(JSON.stringify(payload));
}

function decodeJsonText(text: string): unknown {
  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

/**
 * Decode a marker payload in either supported encoding.
 *
 * The two alphabets are disjoint: base64url uses only `A-Za-z0-9_-`, so a
 * payload containing `%` cannot be base64url. That makes the check
 * deterministic rather than order-dependent.
 */
function decodePayload(payload: string): unknown {
  const normalized = normalizeString(payload);
  if (!normalized) return null;

  if (normalized.includes("%")) {
    try {
      return decodeJsonText(decodeURIComponent(normalized));
    } catch {
      return null;
    }
  }

  const decoded = fromBase64Url(normalized);
  return decoded ? decodeJsonText(decoded) : null;
}

/**
 * Structural validation. Returns null for anything unrecognized.
 *
 * `version` is checked explicitly so a future envelope revision fails closed
 * instead of being partially interpreted by this renderer.
 */
export function validateUiArtifact(candidate: unknown): GenerativeUiArtifact | null {
  if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) return null;
  const raw = candidate as Record<string, unknown>;
  if (raw.version !== 1) return null;

  if (raw.kind === "native") {
    const component = normalizeString(raw.component);
    if (!component || component.length > MAX_TITLE_CHARS) return null;
    const props = raw.props;
    if (props !== undefined && (typeof props !== "object" || props === null || Array.isArray(props))) {
      return null;
    }
    let serialized = "";
    try {
      serialized = JSON.stringify(props ?? {});
    } catch {
      return null;
    }
    if (serialized.length > MAX_NATIVE_PROPS_CHARS) return null;
    return { version: 1, kind: "native", component, props: (props ?? {}) as Record<string, unknown> };
  }

  if (raw.kind === "sandbox") {
    const html = typeof raw.html === "string" ? raw.html : "";
    if (!html.trim() || html.length > MAX_SANDBOX_HTML_CHARS) return null;
    const css = typeof raw.css === "string" ? raw.css : "";
    const js = typeof raw.js === "string" ? raw.js : "";
    if (css.length > MAX_SANDBOX_STYLE_CHARS) return null;
    if (js.length > MAX_SANDBOX_SCRIPT_CHARS) return null;
    if (html.length + css.length + js.length > MAX_SANDBOX_TOTAL_CHARS) return null;

    const title = normalizeString(raw.title);
    if (title.length > MAX_TITLE_CHARS) return null;

    let initialHeight: number | undefined;
    if (raw.initialHeight !== undefined && raw.initialHeight !== null) {
      const candidateHeight = typeof raw.initialHeight === "number" ? raw.initialHeight : Number(raw.initialHeight);
      if (!Number.isFinite(candidateHeight)) return null;
      initialHeight = Math.round(candidateHeight);
    }

    return {
      version: 1,
      kind: "sandbox",
      ...(title ? { title } : {}),
      html,
      ...(css.trim() ? { css } : {}),
      ...(js.trim() ? { js } : {}),
      ...(initialHeight !== undefined ? { initialHeight } : {}),
    };
  }

  return null;
}

/**
 * Extract every valid artifact from message content and return the remaining
 * prose. Invalid markers are stripped from display exactly like valid ones, so
 * an unusable artifact degrades to text instead of leaking marker syntax into
 * the transcript.
 */
export function parseUiArtifacts(content: string): {
  artifacts: GenerativeUiArtifact[];
  text: string;
} {
  const artifacts: GenerativeUiArtifact[] = [];
  let stripped = content || "";

  stripped = stripped.replace(MARKER_RE, (_match, rawPayload: string) => {
    const artifact = validateUiArtifact(decodePayload(String(rawPayload || "")));
    if (!artifact) return "";
    artifacts.push(artifact);
    return "";
  });

  stripped = stripped.replace(UNTERMINATED_MARKER_RE, "");
  stripped = stripped.replace(EXCESSIVE_BLANK_LINES_RE, "\n\n").trim();
  return { artifacts, text: stripped };
}

/** Build the canonical marker for an artifact. Used by authoring and tests. */
export function serializeUiArtifact(artifact: GenerativeUiArtifact): string {
  return `<!-- ${UI_ARTIFACT_MARKER_PREFIX}:${encodePayload(artifact)} -->`;
}

/** Build the marker using the model-facing percent-encoded encoding. */
export function serializeUiArtifactForModel(artifact: GenerativeUiArtifact): string {
  return `<!-- ${UI_ARTIFACT_MARKER_PREFIX}:${encodeUiArtifactPayload(artifact)} -->`;
}

/** Stable key for React reconciliation and duplicate suppression. */
export function uiArtifactKey(artifact: GenerativeUiArtifact, index: number): string {
  if (artifact.kind === "native") return `native:${artifact.component}:${index}`;
  return `sandbox:${index}:${artifact.html.length}:${artifact.js?.length ?? 0}`;
}