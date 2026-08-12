/**
 * Surface Warmth — bidirectional material mapping for Codexify.
 *
 * The shared control spans [-100, 100]. Negative values retain the original
 * graphite/steel HSL shift in both themes. Positive values retain the original
 * warm/olive shift in dark mode, while light mode uses a perceptually smooth
 * paper-color progression via OKLCH interpolation:
 *
 *   neutral white → ivory → cream → parchment → pale legal-pad yellow
 *
 * This keeps the dynamic dark-mode color interactions from the original
 * Surface Warmth control and makes the light-mode warm endpoint reach cream,
 * parchment, and pale yellow instead of replacing the cool half of the range.
 */

// ---------------------------------------------------------------------------
// sRGB ↔ linear-sRGB helpers
// ---------------------------------------------------------------------------

function srgbToLinear(c: number): number {
  const v = c / 255;
  return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
}

function linearToSrgb(v: number): number {
  const c = v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055;
  return Math.round(Math.max(0, Math.min(1, c)) * 255);
}

function hexToRgb(hex: string): { r: number; g: number; b: number } {
  const clean = hex.replace("#", "");
  const value = parseInt(clean, 16);
  return {
    r: (value >> 16) & 255,
    g: (value >> 8) & 255,
    b: value & 255,
  };
}

function rgbToHsl(r: number, g: number, b: number) {
  const red = r / 255;
  const green = g / 255;
  const blue = b / 255;
  const max = Math.max(red, green, blue);
  const min = Math.min(red, green, blue);
  const lightness = (max + min) / 2;
  let hue = 0;
  let saturation = 0;

  if (max !== min) {
    const delta = max - min;
    saturation =
      lightness > 0.5
        ? delta / (2 - max - min)
        : delta / (max + min);
    if (max === red) hue = (green - blue) / delta + (green < blue ? 6 : 0);
    if (max === green) hue = (blue - red) / delta + 2;
    if (max === blue) hue = (red - green) / delta + 4;
    hue /= 6;
  }

  return {
    h: hue * 360,
    s: saturation * 100,
    l: lightness * 100,
  };
}

function hslToHex(h: number, s: number, l: number): string {
  const saturation = s / 100;
  const lightness = l / 100;
  const chroma = (1 - Math.abs(2 * lightness - 1)) * saturation;
  const intermediate = chroma * (1 - Math.abs(((h / 60) % 2) - 1));
  const offset = lightness - chroma / 2;
  let red = 0;
  let green = 0;
  let blue = 0;

  if (h < 60) {
    red = chroma;
    green = intermediate;
  } else if (h < 120) {
    red = intermediate;
    green = chroma;
  } else if (h < 180) {
    green = chroma;
    blue = intermediate;
  } else if (h < 240) {
    green = intermediate;
    blue = chroma;
  } else if (h < 300) {
    red = intermediate;
    blue = chroma;
  } else {
    red = chroma;
    blue = intermediate;
  }

  const toHex = (channel: number) =>
    Math.round((channel + offset) * 255)
      .toString(16)
      .padStart(2, "0");
  return `#${toHex(red)}${toHex(green)}${toHex(blue)}`;
}

// ---------------------------------------------------------------------------
// OKLab / OKLCH
// ---------------------------------------------------------------------------

interface Oklch {
  l: number; // lightness 0-1
  c: number; // chroma    0-~0.37
  h: number; // hue       0-360
}

function hexToOklch(hex: string): Oklch {
  const clean = hex.replace("#", "");
  const r = parseInt(clean.slice(0, 2), 16);
  const g = parseInt(clean.slice(2, 4), 16);
  const b = parseInt(clean.slice(4, 6), 16);

  // sRGB → linear
  const lr = srgbToLinear(r);
  const lg_ = srgbToLinear(g);
  const lb = srgbToLinear(b);

  // Linear → LMS (OKLab matrix)
  const l_ = 0.4122214708 * lr + 0.5363325363 * lg_ + 0.0514459929 * lb;
  const m = 0.2119034982 * lr + 0.6806995451 * lg_ + 0.1073969566 * lb;
  const s = 0.0883024619 * lr + 0.2817188376 * lg_ + 0.6299787005 * lb;

  // LMS → L'M'S' (cube root)
  const lp = Math.cbrt(l_);
  const mp = Math.cbrt(m);
  const sp = Math.cbrt(s);

  // L'M'S' → OKLab
  const labL = 0.2104542553 * lp + 0.7936177850 * mp - 0.0040720468 * sp;
  const labA = 1.9779984951 * lp - 2.4285922050 * mp + 0.4505937099 * sp;
  const labB = 0.0259040371 * lp + 0.7827717662 * mp - 0.8086757660 * sp;

  const ln = Math.max(0, Math.min(1, labL));
  const an = labA;
  const bn = labB;
  const chroma = Math.sqrt(an * an + bn * bn);
  let hue = (Math.atan2(bn, an) * 180) / Math.PI;
  if (hue < 0) hue += 360;

  return { l: ln, c: chroma, h: hue };
}

function oklchToHex(l: number, c: number, h: number): string {
  const hRad = (h * Math.PI) / 180;
  const a = c * Math.cos(hRad);
  const b_ = c * Math.sin(hRad);

  // OKLab → L'M'S'
  const lp = l + 0.3963377774 * a + 0.2158037573 * b_;
  const mp = l - 0.1055613458 * a - 0.0638541728 * b_;
  const sp = l - 0.0894841775 * a - 1.2914855480 * b_;

  // Cube back
  const lLin = lp * lp * lp;
  const mLin = mp * mp * mp;
  const sLin = sp * sp * sp;

  // LMS → linear sRGB
  const lr =
    4.0767416621 * lLin - 3.3077115913 * mLin + 0.2309699292 * sLin;
  const lg_ =
    -1.2684380046 * lLin + 2.6097574011 * mLin - 0.3413193965 * sLin;
  const lb =
    -0.0041960863 * lLin - 0.7034186147 * mLin + 1.7076147010 * sLin;

  const r = linearToSrgb(lr);
  const g = linearToSrgb(lg_);
  const b = linearToSrgb(lb);

  return `#${[r, g, b].map((v) => v.toString(16).padStart(2, "0")).join("")}`;
}

// ---------------------------------------------------------------------------
// Paper tone application
// ---------------------------------------------------------------------------

/**
 * Apply the paper-tone scalar to a light-mode surface color.
 *
 * @param baseHex  The neutral (tone=0) color in hex, e.g. "#f1ede8".
 * @param tone     Paper tone in [0, 100].  Values outside are clamped.
 * @returns        Adjusted hex color.
 *
 * The mapping uses OKLCH interpolation so the progression is perceptually
 * even.  Hue moves gently from the base's native hue toward a pale yellow
 * (~95°), chroma increases subtly, and lightness decreases slightly for
 * depth.  The result stays in paper-material territory — never saturated
 * or dark.
 */
export function applyPaperTone(baseHex: string, tone: number): string {
  const t = Math.max(0, Math.min(100, tone));
  if (t === 0) return baseHex;

  const src = hexToOklch(baseHex);

  // Fraction [0, 1]
  const f = t / 100;

  // Target OKLCH for legal-pad yellow (tone=100).
  // These were chosen empirically so that:
  //   - The endpoint still reads as "paper" (light, low chroma).
  //   - It's unmistakably yellow-tinted but not saturated.
  const targetH = 95; // yellow hue in OKLab
  const targetC = 0.05; // restrained chroma
  const targetL = src.l * 0.95; // slight darkening for depth

  // Interpolate with shortest-path for hue.
  let dh = targetH - src.h;
  // Normalize to [-180, 180]
  while (dh > 180) dh -= 360;
  while (dh < -180) dh += 360;

  const l = src.l + (targetL - src.l) * f;
  const c = src.c + (targetC - src.c) * f;
  const h = src.h + dh * f;

  // Clamp lightness so we never go below paper-readable territory
  const clampedL = Math.max(0.82, Math.min(1, l));
  const clampedC = Math.max(0, Math.min(0.08, c));

  return oklchToHex(clampedL, clampedC, ((h % 360) + 360) % 360);
}

/**
 * Apply the restored bidirectional Surface Warmth control to a neutral surface.
 *
 * Light + warm uses the expanded paper curve. Every other combination uses the
 * original subtle HSL hue pull, including the olive interaction in dark mode.
 */
export function applySurfaceWarmth(
  baseHex: string,
  warmth: number,
  mode: "light" | "dark"
): string {
  const clampedWarmth = normalizeSurfaceWarmth(warmth);
  if (clampedWarmth === 0) return baseHex;
  if (mode === "light" && clampedWarmth > 0) {
    return applyPaperTone(baseHex, clampedWarmth);
  }

  const warmthNorm = clampedWarmth / 100;
  const { r, g, b } = hexToRgb(baseHex);
  const { h, s, l } = rgbToHsl(r, g, b);
  const targetHue = warmthNorm > 0 ? 35 : 210;
  const pull = Math.abs(warmthNorm) * 0.7;
  const hue = ((h + (targetHue - h) * pull) % 360 + 360) % 360;
  const saturation = Math.min(22, s + Math.abs(warmthNorm) * 10);
  return hslToHex(hue, saturation, l);
}

/**
 * Return a short human-readable descriptor for the current paper tone.
 */
export function paperToneLabel(tone: number): string {
  if (tone <= 5) return "Neutral";
  if (tone <= 18) return "Neutral+";
  if (tone <= 35) return "Ivory";
  if (tone <= 65) return "Cream";
  if (tone <= 85) return "Parchment";
  return "Legal";
}

/**
 * Normalize persisted Surface Warmth without discarding the restored cool range.
 */
export function normalizeSurfaceWarmth(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.round(Math.max(-100, Math.min(100, value)));
}
