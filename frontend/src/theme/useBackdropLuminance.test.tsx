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
const UNDERLAY: Rgb = { r: 128, g: 128, b: 128 };

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
    // With a mid-grey underlay the measured backdrop is mid-grey, which
    // resolves to the dark foreground. Treating it as opaque black would
    // have produced the light foreground instead.
    expect(result.current.foreground).toEqual(FOREGROUND_CANDIDATES.dark);
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
});