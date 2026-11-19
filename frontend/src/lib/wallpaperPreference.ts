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

let wallpaperWriter: ((src: string | null, epoch?: number) => void) | null = null;

export function registerWallpaperWriter(writer: (src: string | null, epoch?: number) => void) {
  wallpaperWriter = writer;
}

/** Explicit wallpaper actions use the active account, never browser authority. */
export function setWallpaperPreference(src: string | null, epoch?: number): boolean {
  const normalized = src === null ? null : normalizeWallpaperAssetUrl(src);
  if ((src !== null && !normalized) || !wallpaperWriter) return false;
  wallpaperWriter(normalized, epoch);
  return true;
}
