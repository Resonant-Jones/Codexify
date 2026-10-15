/**
 * Host actions available to sandboxed generative UI.
 *
 * Generated code must never cause silent action execution or permission
 * escalation. The single bridge action available in this slice is
 * `send_prompt`, and it deliberately does **not** send anything: it routes the
 * requested text into the existing composer prefill seam
 * (`cfy:composer:prefill`, consumed by GuardianChat), so the user reviews the
 * text and presses send themselves.
 *
 * That means a sandbox can *request* a turn but can never cause one, and the
 * request travels the same authorized composer path a human turn would.
 */
import { MAX_BRIDGE_PROMPT_CHARS } from "./SandboxFrame";

export const COMPOSER_PREFILL_EVENT = "cfy:composer:prefill";

/**
 * Hand a model-requested prompt to the composer for user review.
 *
 * Returns false when the request is unusable, so callers can treat it as
 * ignored rather than partially applied.
 */
export function requestComposerPrefill(text: string): boolean {
  const normalized = typeof text === "string" ? text.trim() : "";
  if (!normalized || normalized.length > MAX_BRIDGE_PROMPT_CHARS) return false;
  if (typeof window === "undefined") return false;
  try {
    window.dispatchEvent(
      new CustomEvent(COMPOSER_PREFILL_EVENT, { detail: { text: normalized } })
    );
    return true;
  } catch {
    return false;
  }
}