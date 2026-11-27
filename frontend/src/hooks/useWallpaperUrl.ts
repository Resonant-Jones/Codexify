import { useCallback } from "react";
import { useAccountPresentation } from "@/features/settings/accountPresentation";
import { setWallpaperPreference } from "@/lib/wallpaperPreference";

export function useWallpaperUrl() {
  const { wallpaperSrc, epoch } = useAccountPresentation();

  const setWallpaper = useCallback((src: string | null) => setWallpaperPreference(src, epoch), [epoch]);

  return {
    wallpaperUrl: wallpaperSrc,
    renderableWallpaperUrl: wallpaperSrc,
    setWallpaper,
  } as const;
}

export default useWallpaperUrl;
