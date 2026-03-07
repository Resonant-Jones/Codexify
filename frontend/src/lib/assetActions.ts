import api, { buildAuthenticatedFetchInit } from "@/lib/api";
import { normalizeMediaUrl } from "@/lib/mediaUrl";
import { resolveApiUrl } from "@/lib/runtimeConfig";

export type AssetActionKind = "document" | "image";

function emitToast(message: string): void {
  if (typeof window === "undefined") return;
  try {
    window.dispatchEvent(new CustomEvent("cfy:toast", { detail: { message } }));
  } catch {
    // Ignore toast transport failures.
  }
}

function buildDeletePath(kind: AssetActionKind, id: string): string {
  const normalizedId = encodeURIComponent(id.trim());
  return kind === "document"
    ? `/media/documents/${normalizedId}`
    : `/media/images/${normalizedId}`;
}

export function resolveAssetDownloadUrl(
  srcUrl: string | null | undefined,
  fallbackApiPath?: string
): string {
  const normalized = normalizeMediaUrl(srcUrl);
  if (normalized) return normalized;
  if (!fallbackApiPath) return "";
  return resolveApiUrl(fallbackApiPath);
}

export async function downloadAsset(options: {
  url: string;
  filename?: string;
}): Promise<void> {
  const url = options.url.trim();
  if (!url) throw new Error("Missing asset download URL");

  const response = await fetch(
    url,
    buildAuthenticatedFetchInit({ method: "GET" }, { forceApiKey: true })
  );
  if (!response.ok) {
    throw new Error(`Download failed with status ${response.status}`);
  }

  const blob = await response.blob();
  const objectUrl = window.URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = objectUrl;
  if (options.filename?.trim()) anchor.download = options.filename.trim();
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  window.setTimeout(() => window.URL.revokeObjectURL(objectUrl), 0);
}

export async function deleteAsset(options: {
  kind: AssetActionKind;
  id: string;
}): Promise<void> {
  const normalizedId = options.id.trim();
  if (!normalizedId) throw new Error("Missing asset identifier");
  await api.delete(buildDeletePath(options.kind, normalizedId));
}

export function notifyAssetActionError(action: "download" | "delete", label: string): void {
  emitToast(`Unable to ${action} ${label}`);
}
