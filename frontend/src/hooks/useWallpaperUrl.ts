import { useEffect, useState } from "react";

export function useWallpaperUrl() {
  const [wallpaperUrl, setWallpaperUrl] = useState<string | null>(() => {
    if (typeof window === "undefined") return null;
    try {
      return localStorage.getItem("cfy.wallpaper");
    } catch {
      return null;
    }
  });

  useEffect(() => {
    if (typeof window === "undefined") return;
    const onStorage = (e: StorageEvent) => {
      if (e.key === "cfy.wallpaper") setWallpaperUrl(e.newValue);
    };
    window.addEventListener("storage", onStorage);
    return () => window.removeEventListener("storage", onStorage);
  }, []);

  return { wallpaperUrl } as const;
}

export default useWallpaperUrl;
