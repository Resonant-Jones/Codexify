/**
 * Regional backdrop luminance sampling for wallpaper-facing chrome.
 *
 * Codexify paints the shell background as a wallpaper image with a
 * `cover` / `center` fit plus a 135deg fade/depth wash. Any foreground that
 * sits *directly on that background* — rather than on an opaque material
 * surface — cannot be legible if its color is chosen from the theme mode
 * alone. A bright photograph behind a dark-mode shell makes white text
 * invisible; that is the defect this module exists to prevent.
 *
 * Design rules:
 *  - **Regional.** Sample only the region behind the surface of interest,
 *    mapped through the real `cover` geometry. A whole-image mean is wrong.
 *  - **Mixed-luminance safe.** Bokeh wallpapers have blown-out highlights
 *    beside near-black foliage. The mean of such a region lands mid-grey and
 *    *neither* polarity clears AA anywhere, so polarity is chosen by
 *    **worst-case** contrast across the sample distribution.
 *  - **Contrast-safe backing.** Blur or a tasteful low-alpha scrim do not
 *    guarantee contrast — that is precisely how the original bug happened.
 *    When no trustworthy measurement exists (or no polarity clears AA), we
 *    *solve* for the minimum backing alpha that reaches the AA target.
 *  - **Never fatal.** Every DOM failure path degrades to a guaranteed-safe
 *    foreground plus backing. Sampling must never break the shell.
 */

import * as React from "react";

export type Rgb = { r: number; g: number; b: number };

export type Rect = { left: number; top: number; width: number; height: number };

export type SourceRect = { sx: number; sy: number; sw: number; sh: number };

export type Size = { width: number; height: number };

export type WashSpec = {
  /** Overlay color for the gradient's start (top-left) end. */
  color: Rgb;
  startAlpha: number;
  endAlpha: number;
};

export type LuminanceProfile = {
  /** Sample count backing these statistics. */
  count: number;
  /** p10 luminance — the darker tail of the local distribution. */
  dark: number;
  /** p90 luminance — the brighter tail. */
  light: number;
  /** Median luminance, for diagnostics only. Never used for contrast. */
  median: number;
  /**
   * The actual samples that bound this region's distribution (darkest,
   * median, brightest by luminance). Retained as colors — not luminances —
   * so the backing solver can composite real pixels instead of
   * reconstructing an out-of-gamut gray.
   */
  extremes: Rgb[];
  /**
   * Worst-case contrast ratio available in this region for each candidate
   * polarity, computed across the whole sample set rather than on a mean.
   */
  worst: Record<Polarity, number>;
};

export type Polarity = "light" | "dark";

export type ForegroundChoice = {
  polarity: Polarity;
  /** Worst-case contrast achieved by that polarity over this region. */
  contrast: number;
  aaSatisfied: boolean;
};

export type SamplingState = "idle" | "loading" | "measured" | "unavailable";

export type BackdropLuminanceResult = {
  state: SamplingState;
  /** Foreground to paint, always populated. */
  foreground: Rgb;
  /** Lower-emphasis companion foreground, always populated. */
  foregroundMuted: Rgb;
  /** Backing color behind the chrome. */
  backing: Rgb;
  /**
   * Backing opacity in [0, 1]. Solved to reach the AA target when the
   * sampled backdrop cannot be trusted; 0 once a measurement is AA-clean.
   */
  backingAlpha: number;
  /** True when backing must stay on (untrusted sample, or AA not met). */
  needsBacking: boolean;
  profile: LuminanceProfile | null;
};

/** WCAG AA normal-text threshold. */
export const AA_CONTRAST_TARGET = 4.5;

const LIGHT_FOREGROUND: Rgb = { r: 255, g: 255, b: 255 };
const DARK_FOREGROUND: Rgb = { r: 11, g: 15, b: 22 };

// ---------------------------------------------------------------------------
// Color math (numerically identical to utils/themeUtils so the two agree)
// ---------------------------------------------------------------------------

function srgbToLinear(channel: number): number {
  const c = channel / 255;
  return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
}

export function relativeLuminanceOf(color: Rgb): number {
  const R = srgbToLinear(color.r);
  const G = srgbToLinear(color.g);
  const B = srgbToLinear(color.b);
  return 0.2126 * R + 0.7152 * G + 0.0722 * B;
}

export function contrastRatio(a: Rgb, b: Rgb): number {
  const L1 = relativeLuminanceOf(a);
  const L2 = relativeLuminanceOf(b);
  const hi = L1 >= L2 ? L1 : L2;
  const lo = L1 >= L2 ? L2 : L1;
  return (hi + 0.05) / (lo + 0.05);
}

export function toHex(color: Rgb): string {
  const out = (n: number) =>
    Math.round(Math.max(0, Math.min(255, n)))
      .toString(16)
      .padStart(2, "0");
  return `#${out(color.r)}${out(color.g)}${out(color.b)}`;
}

export function toRgba(color: Rgb, alpha: number): string {
  const a = Math.max(0, Math.min(1, alpha)).toFixed(3);
  return `rgba(${Math.round(color.r)}, ${Math.round(color.g)}, ${Math.round(
    color.b
  )}, ${a})`;
}

/**
 * Candidate foregrounds.
 *
 * The dark candidate is deliberately deeper than the light-theme `--text`
 * literal (#111827). #111827 reaches only 4.49:1 against a 50% grey
 * backdrop — just under WCAG AA — which would push mid-tone regions onto the
 * backing path unnecessarily. #0b0f16 (the same value as the app's `:root`
 * `--panel-bg`) clears AA at 4.86:1, so it is both in-palette and correct.
 * The light candidate is pure white, which maximises the usable range of
 * dark backdrops.
 */
export const FOREGROUND_CANDIDATES: Record<Polarity, Rgb> = {
  light: LIGHT_FOREGROUND,
  dark: DARK_FOREGROUND,
};

// ---------------------------------------------------------------------------
// Cover geometry
// ---------------------------------------------------------------------------

/**
 * Map a region of the element (CSS px, element-relative) into source-image
 * pixel coordinates, reproducing `background-size: cover` with
 * `background-position: center`.
 *
 * `cover` scales the image by `max(elementW / imgW, elementH / imgH)` and
 * centers the overflow. We invert that mapping and clamp the result to the
 * image, so a region positioned over the cropped area still samples the
 * correct pixels.
 */
export function coverSourceRect(
  element: Size,
  image: Size,
  region: Rect
): SourceRect {
  const elementW = Math.max(1, element.width);
  const elementH = Math.max(1, element.height);
  const imageW = Math.max(1, image.width);
  const imageH = Math.max(1, image.height);

  const scale = Math.max(elementW / imageW, elementH / imageH);
  const drawnW = imageW * scale;
  const drawnH = imageH * scale;
  const offsetX = (elementW - drawnW) / 2;
  const offsetY = (elementH - drawnH) / 2;

  // Invert the cover mapping, then clamp the requested window to the image.
  const startX = (region.left - offsetX) / scale;
  const startY = (region.top - offsetY) / scale;
  const endX = (region.left + region.width - offsetX) / scale;
  const endY = (region.top + region.height - offsetY) / scale;

  const sx = Math.max(0, Math.min(imageW, startX));
  const sy = Math.max(0, Math.min(imageH, startY));
  const ex = Math.max(sx, Math.min(imageW, endX));
  const ey = Math.max(sy, Math.min(imageH, endY));

  return { sx, sy, sw: ex - sx, sh: ey - sy };
}

// ---------------------------------------------------------------------------
// Wash compositing
// ---------------------------------------------------------------------------

/**
 * Alpha of a 135deg CSS gradient at a normalized element position.
 *
 * A 135deg gradient runs diagonally, so its parameter is the normalized
 * projection onto the gradient axis. `startAlpha` applies at the start corner,
 * `endAlpha` at the opposite corner.
 */
export function washAlphaAt(
  normalizedX: number,
  normalizedY: number,
  startAlpha: number,
  endAlpha: number
): number {
  // 135deg points down-right, so progress increases with x and y together.
  const progress = Math.max(0, Math.min(1, (normalizedX + normalizedY) / 2));
  return startAlpha + (endAlpha - startAlpha) * progress;
}

/** Composite `overlay` over `base` at `alpha`. */
export function compositeOver(overlay: Rgb, alpha: number, base: Rgb): Rgb {
  const a = Math.max(0, Math.min(1, alpha));
  return {
    r: overlay.r * a + base.r * (1 - a),
    g: overlay.g * a + base.g * (1 - a),
    b: overlay.b * a + base.b * (1 - a),
  };
}

// ---------------------------------------------------------------------------
// Luminance profile
// ---------------------------------------------------------------------------

function percentile(sorted: number[], p: number): number {
  if (sorted.length === 0) return 0;
  if (sorted.length === 1) return sorted[0];
  const index = (sorted.length - 1) * p;
  const lower = Math.floor(index);
  const upper = Math.ceil(index);
  if (lower === upper) return sorted[lower];
  return sorted[lower] + (sorted[upper] - sorted[lower]) * (index - lower);
}

/**
 * Build a robust local profile. Deliberately percentile-based: the tails are
 * what determine whether text is readable, not the mean.
 */
export function luminanceProfile(samples: Rgb[]): LuminanceProfile {
  if (samples.length === 0) {
    return {
      count: 0,
      dark: 0,
      light: 0,
      median: 0,
      extremes: [],
      worst: { light: 1, dark: 1 },
    };
  }

  const ordered = [...samples].sort(
    (a, b) => relativeLuminanceOf(a) - relativeLuminanceOf(b)
  );
  const luminances = ordered.map(relativeLuminanceOf);

  // Worst case for each polarity is evaluated across the *entire* sample
  // distribution, so a single blown-out or near-black pixel caps the score.
  const worst: Record<Polarity, number> = {
    light: Infinity,
    dark: Infinity,
  };
  for (const color of samples) {
    worst.light = Math.min(
      worst.light,
      contrastRatio(color, FOREGROUND_CANDIDATES.light)
    );
    worst.dark = Math.min(
      worst.dark,
      contrastRatio(color, FOREGROUND_CANDIDATES.dark)
    );
  }

  return {
    count: samples.length,
    dark: percentile(luminances, 0.1),
    light: percentile(luminances, 0.9),
    median: percentile(luminances, 0.5),
    extremes: [
      ordered[0],
      ordered[Math.floor(ordered.length / 2)],
      ordered[ordered.length - 1],
    ],
    worst,
  };
}

/**
 * Choose the polarity with the higher **worst-case** contrast.
 *
 * This is what makes mixed wallpapers work: a mean-based choice would be
 * dominated by whichever color happens to cover more area, while the
 * worst-case choice refuses to commit until the *entire* region is legible.
 */
export function chooseBackdropForeground(
  profile: LuminanceProfile,
  target: number = AA_CONTRAST_TARGET
): ForegroundChoice {
  const polarity: Polarity =
    profile.worst.dark >= profile.worst.light ? "dark" : "light";
  const contrast = profile.worst[polarity];
  return { polarity, contrast, aaSatisfied: contrast >= target };
}

/** True when neither polarity is trustworthy on its own. */
export function needsBacking(profile: LuminanceProfile, target: number = AA_CONTRAST_TARGET): boolean {
  return !chooseBackdropForeground(profile, target).aaSatisfied;
}

// ---------------------------------------------------------------------------
// Contrast-safe backing
// ---------------------------------------------------------------------------

/**
 * Solve for the *minimum* backing alpha that lifts the worst local sample to
 * `target` contrast against `foreground`.
 *
 * Composite is monotonic in alpha, so a bisection converges reliably. Returns
 * 0 when the bare foreground already clears the target. Backing is tinted
 * toward whichever of black/white the foreground needs — the direction that
 * buys the most contrast per unit alpha — so the result stays visually
 * consistent with the glass material instead of introducing a hue.
 */
export type BackingSolution = { color: Rgb; alpha: number };

const BLACK_BACKING: Rgb = { r: 0, g: 0, b: 0 };
const WHITE_BACKING: Rgb = { r: 255, g: 255, b: 255 };

/**
 * Solve for the minimum backing that lifts the worst local sample to
 * `target` contrast against `foreground`.
 *
 * Returns the backing **color together with** its alpha. Returning them as a
 * pair is essential: the alpha is only meaningful for the tint it was solved
 * against, and pairing a black-solved alpha with a white backing (or vice
 * versa) silently fails to reach the target.
 */
export function solveBacking(
  profile: LuminanceProfile,
  foreground: Rgb,
  target: number = AA_CONTRAST_TARGET
): BackingSolution {
  const extremes = profile.extremes;
  if (profile.count === 0 || extremes.length === 0) {
    return { color: BLACK_BACKING, alpha: 1 };
  }

  const bare = worstContrastWithBacking(extremes, foreground, BLACK_BACKING, 0);
  if (bare >= target) return { color: BLACK_BACKING, alpha: 0 };

  const solveFor = (backing: Rgb): number => {
    const reaches = (alpha: number) =>
      worstContrastWithBacking(extremes, foreground, backing, alpha) >= target;
    if (!reaches(1)) return 1;
    let lo = 0;
    let hi = 1;
    for (let i = 0; i < 24; i += 1) {
      const mid = (lo + hi) / 2;
      if (reaches(mid)) {
        hi = mid;
      } else {
        lo = mid;
      }
    }
    return hi;
  };

  const blackAlpha = solveFor(BLACK_BACKING);
  const whiteAlpha = solveFor(WHITE_BACKING);

  return whiteAlpha < blackAlpha
    ? { color: WHITE_BACKING, alpha: whiteAlpha }
    : { color: BLACK_BACKING, alpha: blackAlpha };
}

/** Alpha-only convenience wrapper over {@link solveBacking}. */
export function solveBackingAlpha(
  profile: LuminanceProfile,
  foreground: Rgb,
  target: number = AA_CONTRAST_TARGET
): number {
  return solveBacking(profile, foreground, target).alpha;
}

/** Worst contrast across the extreme samples once backing is applied. */
function worstContrastWithBacking(
  extremes: Rgb[],
  foreground: Rgb,
  backing: Rgb,
  alpha: number
): number {
  let worst = Infinity;
  for (const sample of extremes) {
    const composited = compositeOver(backing, alpha, sample);
    worst = Math.min(worst, contrastRatio(composited, foreground));
  }
  return worst;
}

/**
 * Build the full result for a region, given samples and the mode fallback.
 *
 * `mode` is only consulted when there is no trustworthy measurement. This is
 * the contrast-safe fallback required by the bug report: mode color is always
 * paired with solved backing, never emitted bare.
 */
export function resolveBackdropPalette({
  profile,
  mode,
  target = AA_CONTRAST_TARGET,
}: {
  profile: LuminanceProfile | null;
  mode: "light" | "dark";
  target?: number;
}): BackdropLuminanceResult {
  // Untrusted sample: mode-derived foreground, but never unguarded.
  if (!profile || profile.count === 0) {
    const foreground =
      mode === "dark" ? FOREGROUND_CANDIDATES.light : FOREGROUND_CANDIDATES.dark;
    return {
      state: "unavailable",
      foreground,
      foregroundMuted: foreground,
      backing: mode === "dark" ? BLACK_BACKING : WHITE_BACKING,
      // No measurement exists, so assume the worst possible backdrop and
      // back fully. This is what makes the fallback demonstrably safe.
      backingAlpha: 1,
      needsBacking: true,
      profile: null,
    };
  }

  const choice = chooseBackdropForeground(profile, target);
  const foreground = FOREGROUND_CANDIDATES[choice.polarity];

  if (choice.aaSatisfied) {
    return {
      state: "measured",
      foreground,
      foregroundMuted: foreground,
      backing: BLACK_BACKING,
      backingAlpha: 0,
      needsBacking: false,
      profile,
    };
  }

  // Take the backing color *and* alpha from the solver together — pairing a
  // black-solved alpha with a white tint (or the reverse) would not actually
  // reach the AA target.
  const solution = solveBacking(profile, foreground, target);
  return {
    state: "measured",
    foreground,
    foregroundMuted: foreground,
    backing: solution.color,
    backingAlpha: solution.alpha,
    needsBacking: true,
    profile,
  };
}

// ---------------------------------------------------------------------------
// Sampling hook
// ---------------------------------------------------------------------------

type UseBackdropLuminanceArgs = {
  src: string | null;
  /** Element carrying the wallpaper background (the shell). */
  elementRef: React.RefObject<HTMLElement | null>;
  /** Region whose backdrop matters (the utility cluster). */
  regionRef: React.RefObject<HTMLElement | null>;
  wash: WashSpec;
  mode: "light" | "dark";
  enabled?: boolean;
};

const SAMPLE_EDGE = 48;

function modeFallback(mode: "light" | "dark"): BackdropLuminanceResult {
  return resolveBackdropPalette({ profile: null, mode });
}

/**
 * Sample the backdrop behind `regionRef` and derive a contrast-safe palette.
 *
 * Concurrency: sampling is asynchronous and the wallpaper can change
 * mid-flight. A monotonically increasing token guards every commit so a slow
 * earlier decode can never overwrite a newer wallpaper's result.
 */
export function useBackdropLuminance({
  src,
  elementRef,
  regionRef,
  wash,
  mode,
  enabled = true,
}: UseBackdropLuminanceArgs): BackdropLuminanceResult {
  const fallback = React.useMemo(() => modeFallback(mode), [mode]);
  const [result, setResult] = React.useState<BackdropLuminanceResult>(fallback);
  const tokenRef = React.useRef(0);
  const committedSrcRef = React.useRef<string | null>(null);

  const washKey = `${wash.color.r},${wash.color.g},${wash.color.b},${wash.startAlpha},${wash.endAlpha}`;

  React.useEffect(() => {
    if (!enabled) {
      setResult(modeFallback(mode));
      return;
    }
    if (!src) {
      tokenRef.current += 1;
      committedSrcRef.current = null;
      setResult(modeFallback(mode));
      return;
    }

    const token = (tokenRef.current += 1);
    setResult((previous) =>
      previous.state === "unavailable" ? previous : { ...previous, state: "loading" }
    );

    const image = new Image();
    image.crossOrigin = "anonymous";
    image.decoding = "async";

    let cancelled = false;

    const commit = (next: BackdropLuminanceResult) => {
      if (cancelled || token !== tokenRef.current) return;
      committedSrcRef.current = src;
      setResult(next);
    };

    image.onload = () => {
      if (cancelled || token !== tokenRef.current) return;
      try {
        const element = elementRef.current;
        const region = regionRef.current;
        if (!element || !region) {
          commit(resolveBackdropPalette({ profile: null, mode }));
          return;
        }

        const elementRect = element.getBoundingClientRect();
        const regionRect = region.getBoundingClientRect();
        if (
          elementRect.width < 1 ||
          elementRect.height < 1 ||
          regionRect.width < 1 ||
          regionRect.height < 1
        ) {
          commit(resolveBackdropPalette({ profile: null, mode }));
          return;
        }

        const relative = {
          left: regionRect.left - elementRect.left,
          top: regionRect.top - elementRect.top,
          width: regionRect.width,
          height: regionRect.height,
        };

        const source = coverSourceRect(
          { width: elementRect.width, height: elementRect.height },
          { width: image.width, height: image.height },
          relative
        );

        const canvas = document.createElement("canvas");
        const scale = Math.min(
          1,
          SAMPLE_EDGE / Math.max(1, Math.max(source.sw, source.sh))
        );
        canvas.width = Math.max(1, Math.round(source.sw * scale));
        canvas.height = Math.max(1, Math.round(source.sh * scale));
        const ctx = canvas.getContext("2d");
        if (!ctx) {
          commit(resolveBackdropPalette({ profile: null, mode }));
          return;
        }
        ctx.drawImage(
          image,
          source.sx,
          source.sy,
          Math.max(1, source.sw),
          Math.max(1, source.sh),
          0,
          0,
          canvas.width,
          canvas.height
        );

        const data = ctx.getImageData(0, 0, canvas.width, canvas.height).data;
        const samples: Rgb[] = [];
        for (let i = 0; i < data.length; i += 4) {
          // Position of this sample inside the element, for the wash.
          const px = (i / 4) % canvas.width;
          const py = Math.floor(i / 4 / canvas.width);
          const nx = (relative.left + (px / canvas.width) * relative.width) / elementRect.width;
          const ny = (relative.top + (py / canvas.height) * relative.height) / elementRect.height;
          const alpha = washAlphaAt(nx, ny, wash.startAlpha, wash.endAlpha);
          samples.push(
            compositeOver(
              wash.color,
              alpha,
              { r: data[i], g: data[i + 1], b: data[i + 2] }
            )
          );
        }

        commit(
          resolveBackdropPalette({ profile: luminanceProfile(samples), mode })
        );
      } catch {
        // Tainted canvas or any other sampling failure: guaranteed-safe fallback.
        commit(resolveBackdropPalette({ profile: null, mode }));
      }
    };

    image.onerror = () => {
      commit(resolveBackdropPalette({ profile: null, mode }));
    };

    image.src = src;

    return () => {
      cancelled = true;
      image.onload = null;
      image.onerror = null;
      if (committedSrcRef.current !== src) image.src = "";
    };
    // Refs are intentionally excluded: they are stable objects, and reading
    // them at sample time is what we want. Including them would re-run this
    // effect on every render for any caller that builds them inline.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [src, washKey, mode, enabled]);

  return result;
}