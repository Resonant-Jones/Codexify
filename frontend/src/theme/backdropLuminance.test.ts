import { describe, expect, it } from "vitest";

import {
  AA_CONTRAST_TARGET,
  chooseBackdropForeground,
  compositeOver,
  contrastRatio,
  coverSourceRect,
  FOREGROUND_CANDIDATES,
  luminanceProfile,
  needsBacking,
  relativeLuminanceOf,
  resolveBackdropPalette,
  solveBacking,
  solveBackingAlpha,
  washAlphaAt,
  type Rgb,
} from "./backdropLuminance";
import { relativeLuminance as themeUtilsRelativeLuminance } from "@/utils/themeUtils";

const WHITE: Rgb = { r: 255, g: 255, b: 255 };
const BLACK: Rgb = { r: 0, g: 0, b: 0 };

function uniform(color: Rgb, count = 64): Rgb[] {
  return Array.from({ length: count }, () => color);
}

/**
 * The reported screenshot: dark foliage with blown-out bokeh discs.
 * 60% near-black, 40% near-white — a whole-image mean lands mid-grey and
 * neither polarity clears AA anywhere.
 */
function mixedBokeh(): Rgb[] {
  const out: Rgb[] = [];
  for (let i = 0; i < 60; i += 1) out.push({ r: 12, g: 14, b: 10 });
  for (let i = 0; i < 40; i += 1) out.push({ r: 246, g: 244, b: 214 });
  return out;
}

describe("relativeLuminanceOf", () => {
  it("matches the existing themeUtils implementation", () => {
    for (const color of [BLACK, WHITE, { r: 128, g: 128, b: 128 }, { r: 37, g: 190, b: 90 }]) {
      expect(relativeLuminanceOf(color)).toBeCloseTo(
        themeUtilsRelativeLuminance(
          `#${[color.r, color.g, color.b]
            .map((n) => n.toString(16).padStart(2, "0"))
            .join("")}`
        ),
        10
      );
    }
  });

  it("orders black below white", () => {
    expect(relativeLuminanceOf(BLACK)).toBeCloseTo(0, 6);
    expect(relativeLuminanceOf(WHITE)).toBeCloseTo(1, 6);
  });
});

describe("coverSourceRect", () => {
  it("maps a full-bleed element to the whole image", () => {
    const rect = coverSourceRect(
      { width: 1000, height: 500 },
      { width: 2000, height: 1000 },
      { left: 0, top: 0, width: 1000, height: 500 }
    );
    expect(rect).toEqual({ sx: 0, sy: 0, sw: 2000, sh: 1000 });
  });

  it("crops a portrait image into a landscape element without upscaling", () => {
    // Element 1000x500, image 1000x2000 -> cover scale 1.0, image drawn
    // 1000x2000, vertically centered => 750px of vertical overflow.
    const rect = coverSourceRect(
      { width: 1000, height: 500 },
      { width: 1000, height: 2000 },
      { left: 0, top: 0, width: 1000, height: 500 }
    );
    expect(rect.sx).toBe(0);
    expect(rect.sw).toBe(1000);
    expect(rect.sy).toBeCloseTo(750, 6);
    expect(rect.sh).toBeCloseTo(500, 6);
  });

  it("maps a landscape image into a portrait element", () => {
    const rect = coverSourceRect(
      { width: 500, height: 1000 },
      { width: 2000, height: 1000 },
      { left: 0, top: 0, width: 500, height: 1000 }
    );
    expect(rect.sy).toBe(0);
    expect(rect.sh).toBe(1000);
    expect(rect.sx).toBeCloseTo(750, 6);
    expect(rect.sw).toBeCloseTo(500, 6);
  });

  it("clamps a region that extends past the element", () => {
    const rect = coverSourceRect(
      { width: 800, height: 600 },
      { width: 800, height: 600 },
      { left: -200, top: -200, width: 2000, height: 2000 }
    );
    expect(rect.sx).toBe(0);
    expect(rect.sy).toBe(0);
    expect(rect.sw).toBe(800);
    expect(rect.sh).toBe(600);
  });

  it("never produces negative extents for a degenerate region", () => {
    const rect = coverSourceRect(
      { width: 800, height: 600 },
      { width: 800, height: 600 },
      { left: 700, top: 500, width: 500, height: 500 }
    );
    expect(rect.sw).toBeGreaterThanOrEqual(0);
    expect(rect.sh).toBeGreaterThanOrEqual(0);
    expect(rect.sx + rect.sw).toBeLessThanOrEqual(800);
    expect(rect.sy + rect.sh).toBeLessThanOrEqual(600);
  });
});

describe("washAlphaAt", () => {
  it("starts at startAlpha and ends at endAlpha", () => {
    // (0,0) -> progress 0, (W,H) -> progress 1, in element pixel space.
    expect(washAlphaAt(0, 0, 1000, 600, 0.4, 0.1)).toBeCloseTo(0.4, 6);
    expect(washAlphaAt(1000, 600, 1000, 600, 0.4, 0.1)).toBeCloseTo(0.1, 6);
  });

  it("matches the CSS 135deg projection (x + y) / (W + H)", () => {
    // 135deg direction is (sin135, -cos135) = (0.707, 0.707) and the
    // gradient line is 0.707 * (W + H), which reduces to (x + y) / (W + H).
    const w = 1600;
    const h = 600;
    // Off-centre point: at the exact midpoint both formulas agree by
    // symmetry, so the divergence would be invisible there.
    const x = 1400;
    const y = 100;
    const expected = (x + y) / (w + h);
    const value = washAlphaAt(x, y, w, h, 0, 1);
    expect(value).toBeCloseTo(expected, 6);

    // The old normalized-average formula disagrees here.
    const naive = (x / w + y / h) / 2;
    expect(naive).not.toBeCloseTo(expected, 3);
  });

  it("differs from a normalized average on a wide element", () => {
    const w = 1600;
    const h = 400;
    const pointX = 1200;
    const pointY = 100;
    const correct = washAlphaAt(pointX, pointY, w, h, 0, 1);
    const naive = (pointX / w + pointY / h) / 2;
    expect(correct).not.toBeCloseTo(naive, 3);
  });

  it("interpolates monotonically", () => {
    let previous = washAlphaAt(0, 0, 1000, 600, 0.4, 0.1);
    for (let i = 1; i <= 10; i += 1) {
      const value = washAlphaAt(
        (i / 10) * 1000,
        (i / 10) * 600,
        1000,
        600,
        0.4,
        0.1
      );
      expect(value).toBeLessThanOrEqual(previous + 1e-9);
      previous = value;
    }
  });

  it("clamps out-of-range positions", () => {
    expect(washAlphaAt(-100, -100, 1000, 600, 0.4, 0.1)).toBeCloseTo(0.4, 6);
    expect(washAlphaAt(5000, 5000, 1000, 600, 0.4, 0.1)).toBeCloseTo(0.1, 6);
  });
});

describe("compositeOver", () => {
  it("returns base unchanged at alpha 0", () => {
    expect(compositeOver(BLACK, 0, { r: 10, g: 20, b: 30 })).toEqual({
      r: 10,
      g: 20,
      b: 30,
    });
  });

  it("returns overlay at alpha 1", () => {
    expect(compositeOver(WHITE, 1, { r: 10, g: 20, b: 30 })).toEqual(WHITE);
  });

  it("blends at intermediate alpha", () => {
    const result = compositeOver(BLACK, 0.5, { r: 200, g: 200, b: 200 });
    expect(result.r).toBeCloseTo(100, 6);
  });
});

describe("luminanceProfile and chooseBackdropForeground", () => {
  it("chooses a dark foreground over a uniformly bright region", () => {
    const profile = luminanceProfile(uniform({ r: 245, g: 245, b: 235 }));
    const choice = chooseBackdropForeground(profile);
    expect(choice.polarity).toBe("dark");
    expect(choice.contrast).toBeGreaterThanOrEqual(AA_CONTRAST_TARGET);
    expect(choice.aaSatisfied).toBe(true);
    expect(needsBacking(profile)).toBe(false);
  });

  it("uses a dark candidate deep enough to clear AA on mid-grey", () => {
    // #111827 would reach only ~4.49:1 here and fail AA, pushing mid-tone
    // regions onto the backing path unnecessarily.
    const midGrey = { r: 128, g: 128, b: 128 };
    expect(
      contrastRatio(FOREGROUND_CANDIDATES.dark, midGrey)
    ).toBeGreaterThanOrEqual(AA_CONTRAST_TARGET);
  });

  it("chooses a light foreground over a uniformly dark region", () => {
    const profile = luminanceProfile(uniform({ r: 18, g: 20, b: 16 }));
    const choice = chooseBackdropForeground(profile);
    expect(choice.polarity).toBe("light");
    expect(choice.contrast).toBeGreaterThanOrEqual(AA_CONTRAST_TARGET);
    expect(needsBacking(profile)).toBe(false);
  });

  it("picks an AA-satisfying polarity for a mid-grey region", () => {
    const profile = luminanceProfile(uniform({ r: 128, g: 128, b: 128 }));
    const choice = chooseBackdropForeground(profile);
    expect(choice.aaSatisfied).toBe(true);
    expect(choice.contrast).toBeGreaterThanOrEqual(AA_CONTRAST_TARGET);
  });

  it("uses worst-case, not mean, so a mixed bokeh region needs backing", () => {
    const samples = mixedBokeh();
    const profile = luminanceProfile(samples);

    // The mean of this region is mid-grey and would be fooled.
    const meanLuminance =
      samples.reduce((sum, c) => sum + relativeLuminanceOf(c), 0) / samples.length;
    expect(meanLuminance).toBeGreaterThan(0.1);
    expect(meanLuminance).toBeLessThan(0.7);

    // Worst case across the distribution is what governs.
    expect(profile.worst.dark).toBeLessThan(AA_CONTRAST_TARGET);
    expect(profile.worst.light).toBeLessThan(AA_CONTRAST_TARGET);

    const choice = chooseBackdropForeground(profile);
    expect(choice.aaSatisfied).toBe(false);
    expect(needsBacking(profile)).toBe(true);

    // It still chooses the better of the two, deterministically.
    const opposite = choice.polarity === "dark" ? "light" : "dark";
    expect(choice.contrast).toBeGreaterThanOrEqual(profile.worst[opposite]);
  });

  it("retains the full sample distribution for the backing solver", () => {
    const samples = mixedBokeh();
    const profile = luminanceProfile(samples);
    expect(profile.samples).toHaveLength(samples.length);
    expect(profile.samples).toEqual(expect.arrayContaining(samples));
  });

  it("handles an empty sample set without throwing", () => {
    const profile = luminanceProfile([]);
    expect(profile.count).toBe(0);
    expect(profile.samples).toEqual([]);
  });
});

describe("solveBackingAlpha", () => {
  it("returns 0 when the bare foreground already clears AA", () => {
    const profile = luminanceProfile(uniform({ r: 245, g: 245, b: 235 }));
    expect(solveBackingAlpha(profile, FOREGROUND_CANDIDATES.dark)).toBe(0);
  });

  it("solves a bright backdrop to an alpha that provably clears AA", () => {
    // Force the wrong polarity so backing has to do the work.
    const profile = luminanceProfile(uniform(WHITE));
    const alpha = solveBackingAlpha(profile, FOREGROUND_CANDIDATES.light);
    expect(alpha).toBeGreaterThan(0);
    const composited = compositeOver(BLACK, alpha, WHITE);
    expect(contrastRatio(composited, FOREGROUND_CANDIDATES.light)).toBeGreaterThanOrEqual(
      AA_CONTRAST_TARGET
    );
  });

  it("solves a dark backdrop to an alpha that provably clears AA", () => {
    const profile = luminanceProfile(uniform(BLACK));
    const alpha = solveBackingAlpha(profile, FOREGROUND_CANDIDATES.dark);
    expect(alpha).toBeGreaterThan(0);
    const composited = compositeOver(WHITE, alpha, BLACK);
    expect(contrastRatio(composited, FOREGROUND_CANDIDATES.dark)).toBeGreaterThanOrEqual(
      AA_CONTRAST_TARGET
    );
  });

  it("makes the mixed bokeh region safe — the screenshot case", () => {
    const samples = mixedBokeh();
    const profile = luminanceProfile(samples);
    const foreground = FOREGROUND_CANDIDATES.light;
    const solution = solveBacking(profile, foreground);

    expect(solution.alpha).toBeGreaterThan(0);
    // The alpha is only valid for the tint it was solved against; the pair
    // must be applied together.
    for (const sample of profile.samples) {
      const composited = compositeOver(solution.color, solution.alpha, sample);
      expect(contrastRatio(composited, foreground)).toBeGreaterThanOrEqual(
        AA_CONTRAST_TARGET
      );
    }
  });

  it("returns backing color and alpha as a matched pair", () => {
    const profile = luminanceProfile(mixedBokeh());
    const solution = solveBacking(profile, FOREGROUND_CANDIDATES.light);
    expect(solution.color).toMatchObject({
      r: expect.any(Number),
      g: expect.any(Number),
      b: expect.any(Number),
    });
    // Applying the pair always satisfies the target for this profile.
    for (const sample of profile.samples) {
      const composited = compositeOver(solution.color, solution.alpha, sample);
      expect(
        contrastRatio(composited, FOREGROUND_CANDIDATES.light)
      ).toBeGreaterThanOrEqual(AA_CONTRAST_TARGET);
    }
  });

  it("is monotonic: a more hostile backdrop never needs less alpha", () => {
    const foreground = FOREGROUND_CANDIDATES.light;
    const midGray = solveBackingAlpha(
      luminanceProfile(uniform({ r: 128, g: 128, b: 128 })),
      foreground
    );
    const hostile = solveBackingAlpha(luminanceProfile(mixedBokeh()), foreground);
    expect(hostile).toBeGreaterThanOrEqual(midGray);
  });

  it("returns 1 for an empty profile", () => {
    expect(solveBackingAlpha(luminanceProfile([]), FOREGROUND_CANDIDATES.light)).toBe(1);
  });

  it("clears AA for every sample including an interior foreground match", () => {
    // Contrast against a fixed foreground is V-shaped in luminance, with its
    // minimum AT the foreground's own luminance. A pixel matching the
    // foreground therefore scores 1.0 — worse than pure black (1.09) — and
    // sits strictly interior when the distribution straddles it.
    //
    // Note this is a *guarantee* test, not a reproduction of a live bug:
    // because compositing toward a constant backing is affine and monotone,
    // the worst sample is provably always at min-L or max-L, which the old
    // [darkest, median, brightest] subset already contained. The subset was
    // therefore relying on an unstated argument rather than being wrong, but
    // the solver now reads the full distribution and no longer depends on it.
    const samples: Rgb[] = [
      { r: 0, g: 0, b: 0 },
      FOREGROUND_CANDIDATES.dark, // contrast 1.00 — interior minimum
      { r: 60, g: 60, b: 60 },
      { r: 120, g: 120, b: 120 },
      { r: 180, g: 180, b: 180 },
      { r: 255, g: 255, b: 255 },
    ];
    const foreground = FOREGROUND_CANDIDATES.dark;

    expect(contrastRatio(FOREGROUND_CANDIDATES.dark, foreground)).toBeCloseTo(1, 3);

    const solution = solveBacking(luminanceProfile(samples), foreground);
    for (const sample of samples) {
      const composited = compositeOver(solution.color, solution.alpha, sample);
      expect(contrastRatio(composited, foreground)).toBeGreaterThanOrEqual(
        AA_CONTRAST_TARGET
      );
    }
  });

  it("guarantees AA across the whole distribution, not a subset", () => {
    // A four-point distribution where the limiting sample is strictly
    // interior: no min/max/median selection would capture it.
    const samples: Rgb[] = [
      { r: 5, g: 5, b: 5 },
      { r: 90, g: 90, b: 90 },
      { r: 130, g: 130, b: 130 },
      { r: 250, g: 250, b: 250 },
    ];
    const profile = luminanceProfile(samples);
    for (const foreground of [
      FOREGROUND_CANDIDATES.light,
      FOREGROUND_CANDIDATES.dark,
    ]) {
      const solution = solveBacking(profile, foreground);
      for (const sample of samples) {
        const composited = compositeOver(solution.color, solution.alpha, sample);
        expect(contrastRatio(composited, foreground)).toBeGreaterThanOrEqual(
          AA_CONTRAST_TARGET
        );
      }
    }
  });
});

describe("resolveBackdropPalette", () => {
  it("never emits a bare mode-derived foreground when sampling is unavailable", () => {
    for (const mode of ["light", "dark"] as const) {
      const result = resolveBackdropPalette({ profile: null, mode });
      expect(result.state).toBe("unavailable");
      expect(result.needsBacking).toBe(true);
      expect(result.backingAlpha).toBe(1);
    }
  });

  it("uses the mode foreground direction but guards it with backing", () => {
    const dark = resolveBackdropPalette({ profile: null, mode: "dark" });
    expect(dark.foreground).toEqual(FOREGROUND_CANDIDATES.light);

    const light = resolveBackdropPalette({ profile: null, mode: "light" });
    expect(light.foreground).toEqual(FOREGROUND_CANDIDATES.dark);
  });

  it("drops backing once a measurement clears AA", () => {
    const result = resolveBackdropPalette({
      profile: luminanceProfile(uniform({ r: 245, g: 245, b: 235 })),
      mode: "dark",
    });
    expect(result.state).toBe("measured");
    expect(result.needsBacking).toBe(false);
    expect(result.backingAlpha).toBe(0);
  });

  it("keeps solved backing when a measurement cannot clear AA", () => {
    const result = resolveBackdropPalette({
      profile: luminanceProfile(mixedBokeh()),
      mode: "dark",
    });
    expect(result.state).toBe("measured");
    expect(result.needsBacking).toBe(true);
    expect(result.backingAlpha).toBeGreaterThan(0);

    // The guarantee: foreground over the resolved backing clears AA against
    // every extreme sample.
    for (const sample of result.profile!.samples) {
      const composited = compositeOver(
        result.backing,
        result.backingAlpha,
        sample
      );
      expect(contrastRatio(composited, result.foreground)).toBeGreaterThanOrEqual(
        AA_CONTRAST_TARGET
      );
    }
  });
});