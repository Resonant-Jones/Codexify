/**
 * Paper Tone — Light-mode-only material mapping for Codexify.
 *
 * Converts a scalar in [0, 100] to a perceptually smooth paper-color
 * progression using OKLCH interpolation:
 *
 *   neutral white → ivory → cream → parchment → pale legal-pad yellow
 *
 * Dark-mode surfaces MUST NOT consume this mapping.  Callers in AppShell
 * gate on `resolved === "light"` before calling applyPaperTone.
 *
 * Semantics:
 *   0   Neutral       (current light appearance, no shift)
 *   25  Ivory         (barely perceptible warmth)
 *   50  Cream         (warm off-white, still reads as paper)
 *   75  Parchment     (visible warm tone, old-paper association)
 *   100 Legal         (pale legal-pad yellow, restrained, not saturated)
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
 * Map a legacy surfaceWarmth value from the old [-100, 100] range
 * to the new [0, 100] paper-tone range.
 *
 * - Old 0 (neutral) → new 0 (Neutral)
 * - Old +100 (warmest) → new 100 (Legal)
 * - Old -100 (coolest) is clamped to 0 (Neutral) — we don't support cool paper
 *
 * If the stored value is already in [0, 100], it's returned as-is.
 */
export function normalizeLegacyWarmth(value: number): number {
  // Detect already-normalized: 0-100 with no negative.
  // We distinguish by checking if it's already >= 0 and <= 100.
  if (value >= 0 && value <= 100) return Math.round(value);

  // Old range [-100, 100]. Negative values → 0 (no "cool paper").
  if (value < 0) return 0;

  // Old positive values: linearly map [0, 100] → [0, 100] (already aligned)
  return Math.round(Math.max(0, Math.min(100, value)));
}
