import { normalizeMediaUrl } from "@/lib/mediaUrl";

export const WALLPAPER_CHANGE_EVENT = "cfy:wallpaper-change";
export const WALLPAPER_STORAGE_KEY = "cfy.wallpaper";

/**
 * Normalize an image asset for durable wallpaper use. Object URLs are only
 * valid for the current document lifetime, so never persist them.
 */
export function normalizeWallpaperAssetUrl(src: string | null | undefined): string | null {
  if (typeof src !== "string" || !src.trim()) return null;
  const normalized = normalizeMediaUrl(src);
  if (!normalized || /^blob:/i.test(normalized)) return null;
  return normalized;
}

/** Persist a wallpaper and notify same-window observers immediately. */
export function setWallpaperPreference(src: string | null): boolean {
  if (typeof window === "undefined") return false;

  const normalized = src === null ? null : normalizeWallpaperAssetUrl(src);
  if (src !== null && !normalized) return false;

  let persisted = true;
  try {
    if (normalized) window.localStorage.setItem(WALLPAPER_STORAGE_KEY, normalized);
    else window.localStorage.removeItem(WALLPAPER_STORAGE_KEY);
  } catch {
    persisted = false;
  }

  try {
    window.dispatchEvent(
      new CustomEvent(WALLPAPER_CHANGE_EVENT, { detail: { url: normalized } })
    );
  } catch {
    // Keep persistence usable even if event delivery is unavailable.
  }
  return persisted;
}
