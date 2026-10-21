import { act, renderHook, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
  contrastRatio,
  FOREGROUND_CANDIDATES,
  relativeLuminanceOf,
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
let pixelAlpha = 255;

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
              data[i + 3] = pixelAlpha;
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
const UNDERLAY = { top: { r: 40, g: 40, b: 40 }, bottom: { r: 200, g: 200, b: 200 } };

describe("useBackdropLuminance race safety", () => {
  beforeEach(() => {
    pending.length = 0;
    pixel = { r: 0, g: 0, b: 0 };
    pixelAlpha = 255;
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
        underlay: UNDERLAY,
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
        underlay: UNDERLAY,
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
          underlay: UNDERLAY,
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
        underlay: UNDERLAY,
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
        underlay: UNDERLAY,
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
          underlay: UNDERLAY,
          mode: "dark",
        }),
      { initialProps: { src: "wall.png" as string | null } }
    );

    rerender({ src: null });

    await waitFor(() => expect(result.current.state).toBe("unavailable"));
    expect(result.current.needsBacking).toBe(true);
  });

  it("re-engages backing while RESAMPLING after a successful measurement", async () => {
    // Regression for review finding P1. Previously the loading state carried
    // the previous palette forward verbatim. After a clean sample that has
    // backingAlpha 0, swapping wallpapers briefly painted the new backdrop
    // with the old foreground and no scrim — reproducing the exact
    // illegibility this module exists to prevent.
    const { result, rerender } = renderHook(
      ({ src }: { src: string }) =>
        useBackdropLuminance({
          src,
          elementRef: elementRef(1000, 600),
          regionRef: regionRef(700, 20, 280, 40),
          wash: WASH,
          underlay: UNDERLAY,
          mode: "dark",
        }),
      { initialProps: { src: "wall-a.png" } }
    );

    pixel = { r: 20, g: 22, b: 18 };
    await act(async () => {
      resolveMatching("wall-a.png");
    });
    await waitFor(() => expect(result.current.state).toBe("measured"));
    expect(result.current.backingAlpha).toBe(0);
    expect(result.current.needsBacking).toBe(false);

    // Swap wallpapers and inspect the state BEFORE the new decode resolves.
    rerender({ src: "wall-b.png" });

    expect(result.current.state).toBe("loading");
    expect(
      result.current.needsBacking,
      "resampling must never expose an unguarded foreground"
    ).toBe(true);
    expect(result.current.backingAlpha).toBeGreaterThan(0);
  });

  it("composites transparent wallpaper pixels over the underlay", async () => {
    // Regression for review finding P2. The sampler ignored the alpha
    // channel, so a fully transparent PNG pixel was read as opaque black
    // instead of revealing the surface beneath.
    pixel = { r: 0, g: 0, b: 0 };
    pixelAlpha = 0; // fully transparent: black RGB, zero alpha

    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall-transparent.png",
        elementRef: elementRef(1000, 600),
        regionRef: regionRef(700, 20, 280, 40),
        wash: WASH,
        underlay: UNDERLAY, // mid grey — what actually shows through
        mode: "dark",
      })
    );

    await act(async () => {
      resolveMatching("wall-transparent.png");
    });

    await waitFor(() => expect(result.current.state).toBe("measured"));
    // A transparent pixel reveals the underlay gradient, evaluated at the
    // sample's vertical position. The utility cluster sits near the top of the
    // shell, so it reads close to UNDERLAY.top (dark) rather than opaque
    // black. Treating the pixel as opaque black would have produced the light
    // foreground instead.
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light);
  });

  it("picks a loading backing that opposes the RETAINED foreground", () => {
    // Regression for review finding P1 on #876. The previous implementation
    // chose the loading backing from the current mode while keeping the
    // previously measured foreground. On a dark->light theme change that pairs
    // a white foreground with a white backing: near-zero contrast until the
    // resample lands.
    const { result, rerender } = renderHook(
      ({ mode }: { mode: "light" | "dark" }) =>
        useBackdropLuminance({
          src: "wall.png",
          elementRef: elementRef(1000, 600),
          regionRef: regionRef(700, 20, 280, 40),
          wash: WASH,
          underlay: UNDERLAY,
          mode,
        }),
      { initialProps: { mode: "dark" as "light" | "dark" } }
    );

    // Measure a dark wallpaper in dark mode -> light (white) foreground.
    pixel = { r: 20, g: 22, b: 18 };
    act(() => {
      resolveMatching("wall.png");
    });
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.light);

    // Flip the theme. Mode says "light" (white backing), but the retained
    // foreground is still white, so the backing must be black.
    rerender({ mode: "light" });
    expect(result.current.needsBacking).toBe(true);

    // The retained foreground and the loading backing must be opposites.
    const fgLum = relativeLuminanceOf(result.current.foreground);
    const backLum = relativeLuminanceOf(result.current.backing);
    expect(fgLum > 0.5 ? backLum < 0.5 : backLum > 0.5).toBe(true);
    expect(
      contrastRatio(result.current.foreground, result.current.backing)
    ).toBeGreaterThanOrEqual(4.5);
  });

  it("resamples when the sampled region geometry changes", async () => {
    // Regression for review finding P1: without an observer, resizing across
    // the 850px container query or toggling utility controls left the old
    // palette over wallpaper pixels it was never measured against.
    const element = {
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        width: 1000,
        height: 600,
        right: 1000,
        bottom: 600,
      }),
    } as unknown as HTMLElement;

    let regionWidth = 280;
    const region = {
      getBoundingClientRect: () => ({
        left: 1000 - regionWidth - 20,
        top: 20,
        width: regionWidth,
        height: 40,
        right: 1000 - 20,
        bottom: 60,
      }),
    } as unknown as HTMLElement;

    const elementRef = { current: element };
    const regionRef = { current: region };

    const observers: Array<{
      callback: () => void;
      targets: Element[];
    }> = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: () => void) {
          observers.push({ callback, targets: [] });
        }
        observe(target: Element) {
          observers.at(-1)!.targets.push(target);
        }
        disconnect() {}
      }
    );

    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall.png",
        elementRef: elementRef as never,
        regionRef: regionRef as never,
        wash: WASH,
        underlay: UNDERLAY,
        mode: "dark",
      })
    );

    pixel = { r: 20, g: 22, b: 18 };
    await act(async () => {
      resolveMatching("wall.png");
    });
    await waitFor(() => expect(result.current.state).toBe("measured"));

    const requestsBefore = pending.length;
    expect(observers.length).toBeGreaterThan(0);

    // Simulate the cluster narrowing (e.g. the workspace glyph swap or a
    // control disappearing on navigation).
    regionWidth = 120;
    await act(async () => {
      observers.at(-1)!.callback();
    });

    await waitFor(() => expect(pending.length).toBeGreaterThan(requestsBefore));
    // The resample must run through the guarded loading state.
    expect(result.current.needsBacking).toBe(true);
  });

  it("resamples when the SHELL height changes but the cluster does not move", async () => {
    // Regression for review finding P1: the geometry key originally tracked
    // only the cluster's rectangle relative to the shell. A vertical resize
    // can leave that rectangle identical while changing both the cover scale
    // and the 135deg wash denominator, so no resample was scheduled and a
    // previously backing-free palette stayed live.
    let shellHeight = 600;
    const element = {
      getBoundingClientRect: () => ({
        left: 0,
        top: 0,
        width: 1000,
        height: shellHeight,
        right: 1000,
        bottom: shellHeight,
      }),
    } as unknown as HTMLElement;

    const region = {
      getBoundingClientRect: () => ({
        left: 700,
        top: 20,
        width: 280,
        height: 40,
        right: 980,
        bottom: 60,
      }),
    } as unknown as HTMLElement;

    const observers: Array<() => void> = [];
    vi.stubGlobal(
      "ResizeObserver",
      class {
        constructor(callback: () => void) {
          observers.push(callback);
        }
        observe() {}
        disconnect() {}
      }
    );

    const { result } = renderHook(() =>
      useBackdropLuminance({
        src: "wall.png",
        elementRef: { current: element } as never,
        regionRef: { current: region } as never,
        wash: WASH,
        underlay: UNDERLAY,
        mode: "dark",
      })
    );

    pixel = { r: 20, g: 22, b: 18 };
    act(() => {
      resolveMatching("wall.png");
    });
    await waitFor(() => expect(result.current.state).toBe("measured"));

    const before = pending.length;

    // Only the SHELL height changes; the cluster's relative rect is identical.
    shellHeight = 900;
    act(() => {
      observers.at(-1)!();
    });

    await waitFor(() => expect(pending.length).toBeGreaterThan(before));
    expect(result.current.needsBacking).toBe(true);
  });
});