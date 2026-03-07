import { resolveBackendUrl } from "@/lib/runtimeConfig";

const MEDIA_SOURCE_FIELDS = [
  "src_url",
  "srcUrl",
  "image_url",
  "imageUrl",
  "url",
  "src",
  "path",
] as const;

function asNonEmptyString(value: unknown): string {
  return typeof value === "string" ? value.trim() : "";
}

function isDirectlyRenderableUrl(value: string): boolean {
  return /^(?:https?:|data:|blob:)/i.test(value) || value.startsWith("//");
}

export function normalizeMediaUrl(srcUrl: string | null | undefined): string {
  const trimmed = asNonEmptyString(srcUrl);
  if (!trimmed) return "";
  if (isDirectlyRenderableUrl(trimmed)) return trimmed;
  return resolveBackendUrl(trimmed);
}

export function resolveMediaAssetSrc(
  media: Record<string, unknown> | null | undefined
): string {
  if (!media || typeof media !== "object") return "";

  // Backend image payloads use `src_url` as the canonical asset field.
  for (const field of MEDIA_SOURCE_FIELDS) {
    const candidate = asNonEmptyString(media[field]);
    if (candidate) return normalizeMediaUrl(candidate);
  }

  return "";
}
