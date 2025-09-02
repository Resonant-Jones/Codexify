// src/hooks/useThemeVars.ts
import { useEffect } from "react";

// tiny color helpers (hex <-> rgb + mix)
function hexToRgb(hex: string) {
  const m = hex.replace("#", "");
  const n = m.length === 3 ? m.split("").map((c) => c + c).join("") : m;
  const i = parseInt;
  return [i(n.slice(0, 2), 16), i(n.slice(2, 4), 16), i(n.slice(4, 6), 16)];
}
function rgbToHex([r, g, b]: number[]) {
  const h = (n: number) => n.toString(16).padStart(2, "0");
  return `#${h(Math.round(r))}${h(Math.round(g))}${h(Math.round(b))}`;
}
function mix(aHex: string, bHex: string, t: number) {
  const a = hexToRgb(aHex);
  const b = hexToRgb(bHex);
  return rgbToHex([0, 1, 2].map((i) => a[i] * (1 - t) + b[i] * t));
}

type Args = {
  resolved: "light" | "dark";
  baseColor: string; // hex
  depth: number; // 0..1 (kept for future nuance)
  fade: number; // 0..1 (kept for future nuance)
};

/**
 * Writes CSS variables to shape the page background.
 * Requirement:
 *  - LIGHT: top 25% ~ near white, then saturated color takes over.
 *  - DARK:  top ~ saturated color, bottom 25% ~ near black (inverted).
 */
export default function useThemeVars({ resolved, baseColor }: Args) {
  useEffect(() => {
    const root = document.documentElement;

    const white = "#ffffff";
    const black = "#000000";

    let topColor = white;
    let bottomColor = white;
    let stopPct = "25%"; // where the color takes over (light) or black begins (dark)

    if (resolved === "light") {
      // Light: 0–25% is near-white; 25–100% is saturated color.
      const nearWhite = mix(white, baseColor, 0.06);   // just a kiss of tint
      const saturated = mix(white, baseColor, 0.92);   // rich color without going neon
      topColor = nearWhite;
      bottomColor = saturated;
      stopPct = "25%"; // white occupies the top quarter
    } else {
      // Dark: 0–75% is saturated color; 75–100% is near-black.
      const colored = mix(black, baseColor, 0.72);     // strong color on dark base
      const nearBlack = black;                          // true black for the bottom quarter
      topColor = colored;
      bottomColor = nearBlack;
      stopPct = "75%"; // black only in the bottom quarter
    }

    // New vars for explicit stops
    root.style.setProperty("--bg-top-color", topColor);
    root.style.setProperty("--bg-bottom-color", bottomColor);
    root.style.setProperty("--bg-stop", stopPct);

    // Back-compat with older styles that still read these two
    root.style.setProperty("--gradient-from", topColor);
    root.style.setProperty("--gradient-to", bottomColor);
  }, [resolved, baseColor]);
}
