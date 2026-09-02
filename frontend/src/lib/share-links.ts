/**
 * Typed runtime bindings for the tokenized share-link contract.
 *
 * `POST /api/share` remains the sole authority for creating a secure
 * read-only share URL.  Nothing here changes link access semantics:
 * a link is token-authorized for anyone who holds it — it is NOT
 * recipient-bound.  This module only wraps the existing contract plus
 * the existing clipboard fallback chain.
 */
import api from "@/lib/api";

export type ShareTargetType = "thread" | "document";

export type CreateShareResult = {
  ok: boolean;
  token: string;
  url: string;
  expires_at: string | null;
};

export type CopyMethod = "clipboard" | "execCommand" | "prompt" | "none";

export class ShareLinkApiError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ShareLinkApiError";
    this.status = status;
  }
}

/**
 * Create exactly one secure tokenized share link for a Thread or Document.
 * One call = one SharedLink row.  Callers must preserve the returned URL
 * across retry states instead of calling this again.
 */
export async function createShareLink(
  targetType: ShareTargetType,
  targetId: number,
  expiresInDays?: number | null
): Promise<CreateShareResult> {
  try {
    const response = await api.post<CreateShareResult>("/api/share", {
      target_type: targetType,
      target_id: targetId,
      ...(expiresInDays != null && expiresInDays > 0
        ? { expires_in_days: expiresInDays }
        : {}),
    });
    return response.data;
  } catch (error) {
    const status =
      typeof (error as { response?: { status?: unknown } } | null)?.response
        ?.status === "number"
        ? ((error as { response: { status: number } }).response.status)
        : 0;
    throw new ShareLinkApiError(
      status,
      error instanceof Error
        ? error.message
        : "Failed to create share link"
    );
  }
}

/**
 * Copy text using the established clipboard chain: async clipboard, then
 * execCommand, then a visible prompt.  Returns the method that succeeded.
 */
export async function copyTextWithFallback(text: string): Promise<CopyMethod> {
  if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return "clipboard";
    } catch {
      // Continue to fallback copy methods below.
    }
  }

  if (
    typeof document !== "undefined" &&
    typeof document.execCommand === "function"
  ) {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.setAttribute("readonly", "");
    textarea.style.position = "fixed";
    textarea.style.left = "-9999px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    try {
      if (document.execCommand("copy")) return "execCommand";
    } catch {
      // Continue to fallback prompt below.
    } finally {
      document.body.removeChild(textarea);
    }
  }

  if (typeof window !== "undefined" && typeof window.prompt === "function") {
    try {
      window.prompt("Copy link:", text);
      return "prompt";
    } catch {
      // No-op. We'll return "none" below.
    }
  }

  return "none";
}
