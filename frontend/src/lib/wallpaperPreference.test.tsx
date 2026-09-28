import { act, cleanup, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

const runtimeState = vi.hoisted(() => ({
  tauri: false,
  invokeTauriCommand: vi.fn(),
}));

vi.mock("@/lib/runtimeConfig", () => ({
  getRuntimeConfigSync: () => ({ backendBaseUrl: "http://backend.test" }),
  resolveBackendUrl: (path: string) => `http://backend.test${path}`,
  isTauriRuntime: () => runtimeState.tauri,
  invokeTauriCommand: runtimeState.invokeTauriCommand,
}));

import { useWallpaperUrl } from "@/hooks/useWallpaperUrl";

describe("useWallpaperUrl persistence", () => {
  beforeEach(() => {
    localStorage.clear();
    runtimeState.tauri = false;
    runtimeState.invokeTauriCommand.mockReset();
  });
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

  it("renders a persisted desktop asset through a temporary URL without storing that URL", async () => {
    runtimeState.tauri = true;
    runtimeState.invokeTauriCommand.mockResolvedValue({
      contentType: "image/png",
      bytesBase64: "aGVsbG8=",
      sizeBytes: 5,
    });
    Object.defineProperty(window.URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:desktop-wallpaper"),
    });

    const { result } = renderHook(() => useWallpaperUrl());
    act(() => result.current.setWallpaper("/media/images/desktop-wallpaper.png?sig=stable"));

    await waitFor(() => {
      expect(result.current.renderableWallpaperUrl).toBe("blob:desktop-wallpaper");
    });
    expect(runtimeState.invokeTauriCommand).toHaveBeenCalledWith("desktop_fetch_media", {
      path: "/media/images/desktop-wallpaper.png",
    });
    expect(localStorage.getItem("cfy.wallpaper")).toBe(
      "http://backend.test/media/images/desktop-wallpaper.png?sig=stable"
    );
  });
});
