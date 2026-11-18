import { cleanup, renderHook } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
const state = vi.hoisted(() => ({ wallpaperSrc: null as string | null }));
vi.mock("@/features/settings/accountPresentation", () => ({ useAccountPresentation: () => state }));
vi.mock("@/lib/runtimeConfig", () => ({
  getRuntimeConfigSync: () => ({ backendBaseUrl: "http://backend.test" }),
  resolveBackendUrl: (path: string) => `http://backend.test${path}`,
}));
import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";
import { registerWallpaperWriter } from "./wallpaperPreference";
describe("account wallpaper authority", () => {
  const write = vi.fn();
  beforeEach(() => { localStorage.clear(); write.mockReset(); registerWallpaperWriter(write); state.wallpaperSrc = null; });
  afterEach(cleanup);
  it("delegates actions and preserves recoverable legacy browser values", () => {
    localStorage.setItem("cfy.wallpaper", "data:legacy-value");
    const { result } = renderHook(() => useWallpaperUrl());
    expect(result.current.wallpaperUrl).toBeNull();
    expect(result.current.setWallpaper("/media/images/example.png")).toBe(true);
    expect(write).toHaveBeenCalledWith("http://backend.test/media/images/example.png", undefined);
    result.current.setWallpaper(null);
    expect(write).toHaveBeenLastCalledWith(null, undefined);
    expect(localStorage.getItem("cfy.wallpaper")).toBe("data:legacy-value");
  });
  it("renders only authenticated account wallpaper and clears on account reset", () => {
    state.wallpaperSrc = "blob:owner-a";
    const { result, rerender } = renderHook(() => useWallpaperUrl());
    expect(result.current.renderableWallpaperUrl).toBe("blob:owner-a");
    state.wallpaperSrc = null; rerender();
    expect(result.current.renderableWallpaperUrl).toBeNull();
  });
  it("rejects transient object URLs as source actions", () => {
    const { result } = renderHook(() => useWallpaperUrl());
    expect(result.current.setWallpaper("blob:transient")).toBe(false);
    expect(write).not.toHaveBeenCalled();
  });
});
