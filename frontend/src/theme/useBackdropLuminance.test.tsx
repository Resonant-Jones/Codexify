import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  FOREGROUND_CANDIDATES,
  useBackdropLuminance,
  type Rgb,
} from "./backdropLuminance";

/**
 * jsdom cannot decode images or allocate a 2D canvas, so the hook's success
 * path is unreachable without stubbing both. These fakes let each request be
 * resolved independently and in any order, which is exactly what the
 * race-safety contract needs to be observable.
 */

type FakeImage = {
  crossOrigin: string | null;
  decoding: string;
  src: string;
  width: number;
  height: number;
  onload: (() => void) | null;
  onerror: (() => void) | null;
};

const pending: FakeImage[] = [];
let pixel: Rgb = { r: 0, g: 0, b: 0 };

function installStubs() {
  class FakeImageCtor {
    crossOrigin: string | null = null;
    decoding = "auto";
    width = 400;
    height = 400;
    onload: (() => void) | null = null;
    onerror: (() => void) | null = null;
    #src = "";

    get src() {
      return this.#src;
    }

    set src(value: string) {
      this.#src = value;
      pending.push(this as unknown as FakeImage);
    }
  }

  vi.stubGlobal("Image", FakeImageCtor);

  const realCreate = document.createElement.bind(document);
  const createSpy = vi.spyOn(document, "createElement");
  createSpy.mockImplementation(((tag: string) => {
    if (tag === "canvas") {
      return {
        width: 0,
        height: 0,
        getContext: () => ({
          drawImage: () => {},
          getImageData: (_x: number, _y: number, w: number, h: number) => {
            const data = new Uint8ClampedArray(w * h * 4);
            for (let i = 0; i < data.length; i += 4) {
              data[i] = pixel.r;
              data[i + 1] = pixel.g;
              data[i + 2] = pixel.b;
              data[i + 3] = 255;
            }
            return { data };
          },
        }),
      } as unknown as HTMLElement;
    }
    return realCreate(tag);
  }) as unknown as typeof document.createElement);
}

/** Resolve every image whose src matches, after marking them loaded. */
function resolveMatching(match: string) {
  for (const image of pending.splice(0)) {
    if (image.src !== match) {
      // Put non-matching ones back so they can resolve later.
      pending.push(image);
      continue;
    }
    image.onload?.();
  }
}

function elementRef(width: number, height: number, left = 0, top = 0) {
  return {
    current: {
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        width,
        height,
        right: width,
        bottom: height,
      }),
    } as unknown as React.RefObject<HTMLElement>,
  };
}

function regionRef(left: number, top: number, width: number, height: number) {
  return {
    current: {
      getBoundingClientRect: () => ({
        left,
        top,
        width,
        height,
        right: left + width,
        bottom: top + height,
      }),
    } as unknown as React.RefObject<HTMLElement>,
  };
}

const WASH = { color: { r: 0, g: 0, b: 0 }, startAlpha: 0, endAlpha: 0 };

describe("useBackdropLuminance race safety", () => {
  beforeEach(() => {
    pending.length = 0;
    pixel = { r: 0, g: 0, b: 0 };
    installStubs();
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    vi.restoreAllMocks();
  });

  it("commits a dark wallpaper as a light foreground", async () => {
    pixel = { r: 20, g: 22, b: 18 };
    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall-dark.png",
        elementRef: elementRef(1000, 600),
        regionRef: regionRef(700, 20, 280, 40),
        wash: WASH,
        mode: "dark",
      })
    );

    await act(async () => {
      resolveMatching("wall-dark.png");
    });

    await waitFor(() => expect(result.current.state).toBe("measured"));
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light);
    expect(result.current.needsBacking).toBe(false);
  });

  it("commits a bright wallpaper as a dark foreground", async () => {
    pixel = { r: 245, g: 243, b: 220 };
    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall-bright.png",
        elementRef: elementRef(1000, 600),
        regionRef: regionRef(700, 20, 280, 40),
        wash: WASH,
        mode: "dark",
      })
    );

    await act(async () => {
      resolveMatching("wall-bright.png");
    });

    await waitFor(() => expect(result.current.state).toBe("measured"));
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.dark);
  });

  it("discards a stale earlier decode that resolves after a newer wallpaper", async () => {
    const { result, rerender } = renderHook(
      ({ src }: { src: string }) =>
        useBackdropLuminance({
          src,
          elementRef: elementRef(1000, 600),
          regionRef: regionRef(700, 20, 280, 40),
          wash: WASH,
          mode: "dark",
        }),
      { initialProps: { src: "wall-first.png" } }
    );

    // The first wallpaper is bright -> dark foreground.
    pixel = { r: 245, g: 243, b: 220 };
    await act(async () => {
      resolveMatching("wall-first.png");
    });
    await waitFor(() => expect(result.current.state).toBe("measured"));
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.dark);

    // Swap to a dark wallpaper before the first is committed again.
    pixel = { r: 20, g: 22, b: 18 };
    rerender({ src: "wall-second.png" });

    // Resolve the NEW wallpaper first (correct ordering).
    await act(async () => {
      resolveMatching("wall-second.png");
    });
    await waitFor(() =>
      expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light)
    );

    // Now let any straggler for the OLD wallpaper resolve. It must not be
    // able to overwrite the newer commitment.
    await act(async () => {
      for (const image of pending.splice(0)) {
        image.onload?.();
      }
    });

    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light);
  });

  it("never leaves an unguarded foreground when the image fails to load", async () => {
    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall-broken.png",
        elementRef: elementRef(1000, 600),
        regionRef: regionRef(700, 20, 280, 40),
        wash: WASH,
        mode: "dark",
      })
    );

    await act(async () => {
      for (const image of pending.splice(0)) image.onerror?.();
    });

    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    // Mode fallback, but always backed.
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light);
    expect(result.current.needsBacking).toBe(true);
    expect(result.current.backingAlpha).toBe(1);
  });

  it("keeps backing active while a wallpaper is still loading", () => {
    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall-slow.png",
        elementRef: elementRef(1000, 600),
        regionRef: regionRef(700, 20, 280, 40),
        wash: WASH,
        mode: "dark",
      })
    );

    // Before any resolution the result must already be guarded.
    expect(result.current.needsBacking).toBe(true);
    expect(result.current.backingAlpha).toBe(1);
  });

  it("falls back safely when the wallpaper is cleared", async () => {
    const { result, rerender } = renderHook(
      ({ src }: { src: string | null }) =>
        useBackdropLuminance({
          src,
          elementRef: elementRef(1000, 600),
          regionRef: regionRef(700, 20, 280, 40),
          wash: WASH,
          mode: "dark",
        }),
      { initialProps: { src: "wall.png" as string | null } }
    );

    rerender({ src: null });

    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(result.current.needsBacking).toBe(true);
  });
});