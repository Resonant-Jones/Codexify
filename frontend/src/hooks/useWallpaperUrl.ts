import { useCallback, useEffect, useState } from "react";
import {
  setWallpaperPreference,
  WALLPAPER_CHANGE_EVENT,
  WALLPAPER_STORAGE_KEY,
} from "@/lib/wallpaperPreference";

export function useWallpaperUrl() {
  const [wallpaperUrl, setWallpaperUrl] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem(WALLPAPER_STORAGE_KEY);
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === WALLPAPER_STORAGE_KEY) setWallpaperUrl(e.newValue);
    };
    const onWallpaperChange = (event: Event) => {
      const detail = (event as CustomEvent<{ url: string | null }>).detail;
      setWallpaperUrl(detail?.url ?? null);
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener(WALLPAPER_CHANGE_EVENT, onWallpaperChange);
    return () => {
      window.removeEventListener("storage", onStorage);
      window.removeEventListener(WALLPAPER_CHANGE_EVENT, onWallpaperChange);
    };
  }, []);

  const setWallpaper = useCallback((src: string | null) => {
    setWallpaperPreference(src);
  }, []);

  return { wallpaperUrl, setWallpaper } as const;
}

export default useWallpaperUrl;
