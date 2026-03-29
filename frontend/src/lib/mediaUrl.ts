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

function splitPathAndSuffix(value: string): { path: string; suffix: string } {
  const queryIndex = value.indexOf("?");
  const hashIndex = value.indexOf("#");
  const cutIndex =
    queryIndex === -1 ? hashIndex :
      hashIndex === -1 ? queryIndex :
        Math.min(queryIndex, hashIndex);

  if (cutIndex === -1) {
    return { path: value, suffix: "" };
  }

  return {
    path: value.slice(0, cutIndex),
    suffix: value.slice(cutIndex),
  };
}

function normalizeRelativeMediaPath(path: string): string | null {
  if (!path) return null;
  if (path === "/media" || path.startsWith("/media/")) return path;
  if (path === "media" || path.startsWith("media/")) return `/${path}`;
  return null;
}

function classifyPathname(value: string): string {
  const trimmed = asNonEmptyString(value);
  if (!trimmed) return "";
  if (/^data:/i.test(trimmed)) return "";

  if (/^(?:https?:)?\/\//i.test(trimmed)) {
    try {
      return new URL(trimmed, "http://placeholder").pathname || "";
    } catch {
      return splitPathAndSuffix(trimmed).path;
    }
  }

  return splitPathAndSuffix(trimmed).path;
}

export function resolveMediaSrc(src: string): string {
  const trimmed = asNonEmptyString(src);
  if (!trimmed) return "";
  if (isDirectlyRenderableUrl(trimmed)) return trimmed;

  const { path, suffix } = splitPathAndSuffix(trimmed);
  const normalizedMediaPath = normalizeRelativeMediaPath(path);
  if (!normalizedMediaPath) return trimmed;

  return `${resolveBackendUrl(normalizedMediaPath)}${suffix}`;
}

export function normalizeMediaUrl(srcUrl: string | null | undefined): string {
  const trimmed = asNonEmptyString(srcUrl);
  if (!trimmed) return "";
  return resolveMediaSrc(trimmed);
}

export function isImageMediaUrl(src: string): boolean {
  const trimmed = asNonEmptyString(src);
  if (!trimmed) return false;
  if (/^data:image\//i.test(trimmed)) return true;

  const pathname = classifyPathname(trimmed).toLowerCase();
  return (
    pathname.endsWith(".png") ||
    pathname.endsWith(".jpg") ||
    pathname.endsWith(".jpeg") ||
    pathname.endsWith(".webp")
  );
}

export function isPdfMediaUrl(src: string): boolean {
  const trimmed = asNonEmptyString(src);
  if (!trimmed) return false;
  if (/^data:application\/pdf(?:[;,]|$)/i.test(trimmed)) return true;

  return classifyPathname(trimmed).toLowerCase().endsWith(".pdf");
}

export function resolveMediaAssetSrc(
  media: Record<string, unknown> | null | undefined
): string {
  if (!media || typeof media !== "object") return "";

  // Backend image payloads use `src_url` as the canonical asset field.
  for (const field of MEDIA_SOURCE_FIELDS) {
    const candidate = asNonEmptyString(media[field]);
    if (candidate) return resolveMediaSrc(candidate);
  }

  return "";
}
