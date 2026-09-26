import { act, cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/runtimeConfig", () => ({
  getRuntimeConfigSync: () => ({ backendBaseUrl: "http://backend.test" }),
  resolveBackendUrl: (path: string) => `http://backend.test${path}`,
}));

import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";

describe("useWallpaperUrl persistence", () => {
  beforeEach(() => localStorage.clear());
  afterEach(() => {
    cleanup();
    vi.restoreAllMocks();
  });

  it("updates the active wallpaper immediately and restores it after remount", () => {
    const firstMount = renderHook(() => useWallpaperUrl());

    act(() => {
      firstMount.result.current.setWallpaper("/media/images/wallpaper.png?sig=stable");
    });

    const expected = "http://backend.test/media/images/wallpaper.png?sig=stable";
    expect(firstMount.result.current.wallpaperUrl).toBe(expected);
    expect(localStorage.getItem("cfy.wallpaper")).toBe(expected);

    firstMount.unmount();
    const reloaded = renderHook(() => useWallpaperUrl());
    expect(reloaded.result.current.wallpaperUrl).toBe(expected);

    act(() => reloaded.result.current.setWallpaper(null));
    expect(reloaded.result.current.wallpaperUrl).toBeNull();
    expect(localStorage.getItem("cfy.wallpaper")).toBeNull();
  });

  it("ignores transient object URLs", () => {
    const { result } = renderHook(() => useWallpaperUrl());

    act(() => result.current.setWallpaper("blob:temporary-rendering-url"));

    expect(result.current.wallpaperUrl).toBeNull();
    expect(localStorage.getItem("cfy.wallpaper")).toBeNull();
  });
});
