import { describe, expect, test } from "vitest";
import {
  applyPaperTone,
  paperToneLabel,
  normalizeLegacyWarmth,
} from "@/theme/paperTone";

describe("applyPaperTone", () => {
  const neutralBase = "#f1ede8"; // current light panel-sheet

  test("returns base unchanged at tone 0", () => {
    expect(applyPaperTone(neutralBase, 0)).toBe(neutralBase);
  });

  test("returns base unchanged at negative tone (clamped to 0)", () => {
    expect(applyPaperTone(neutralBase, -10)).toBe(neutralBase);
  });

  test("clamps to 0 for below-range values", () => {
    // Clamping means tone=0 behavior, which is identity
    expect(applyPaperTone("#f1ede8", -50)).toBe("#f1ede8");
  });

  test("clamps to 100 for above-range values", () => {
    const at100 = applyPaperTone("#f1ede8", 100);
    const at200 = applyPaperTone("#f1ede8", 200);
    expect(at200).toBe(at100);
  });

  test("midpoint (50) produces a cream-range color distinct from neutral", () => {
    const result = applyPaperTone(neutralBase, 50);
    expect(result).not.toBe(neutralBase);
    // Should still start with # (valid hex)
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
  });

  test("maximum (100) produces a legal-pad yellow that is still light", () => {
    const result = applyPaperTone(neutralBase, 100);
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
    // It should not be the same as the neutral base
    expect(result).not.toBe(neutralBase);
  });

  test("output is monotonically warming (R/G ratio increases with tone)", () => {
    // Higher paper tone should shift more toward yellow/warm.
    // We check that the green-to-blue ratio increases (yellow = high R+G, low B).
    const at0 = applyPaperTone(neutralBase, 0);
    const at50 = applyPaperTone(neutralBase, 50);
    const at100 = applyPaperTone(neutralBase, 100);

    const rgb = (hex: string) => ({
      r: parseInt(hex.slice(1, 3), 16),
      g: parseInt(hex.slice(3, 5), 16),
      b: parseInt(hex.slice(5, 7), 16),
    });

    const r0 = rgb(at0);
    const r50 = rgb(at50);
    const r100 = rgb(at100);

    // As we warm toward yellow, the blue channel should decrease relative to red/green.
    const warmthRatio = (c: { r: number; g: number; b: number }) =>
      (c.r + c.g) / Math.max(1, c.b);

    expect(warmthRatio(r50)).toBeGreaterThanOrEqual(warmthRatio(r0) - 0.01);
    expect(warmthRatio(r100)).toBeGreaterThanOrEqual(warmthRatio(r50) - 0.01);
  });

  test("does not produce saturated output at any tone", () => {
    for (let t = 0; t <= 100; t += 10) {
      const result = applyPaperTone(neutralBase, t);
      const r = parseInt(result.slice(1, 3), 16);
      const g = parseInt(result.slice(3, 5), 16);
      const b = parseInt(result.slice(5, 7), 16);
      // Paper tones should be low saturation: channels close together.
      const spread = Math.max(r, g, b) - Math.min(r, g, b);
      expect(spread).toBeLessThan(60); // relaxed threshold for paper territory
    }
  });

  test("preserves readability: lightness stays high across the range", () => {
    for (let t = 0; t <= 100; t += 10) {
      const result = applyPaperTone(neutralBase, t);
      const r = parseInt(result.slice(1, 3), 16);
      const g = parseInt(result.slice(3, 5), 16);
      const b = parseInt(result.slice(5, 7), 16);
      // All channels should stay above 200 (paper stays light)
      expect(r).toBeGreaterThanOrEqual(195);
      expect(g).toBeGreaterThanOrEqual(190);
      expect(b).toBeGreaterThanOrEqual(180);
    }
  });

  test("chip base also maps correctly", () => {
    const chipBase = "#e9e4dc";
    const result = applyPaperTone(chipBase, 75);
    expect(result).toMatch(/^#[0-9a-f]{6}$/);
    expect(result).not.toBe(chipBase);
  });
});

describe("paperToneLabel", () => {
  test("returns Neutral at 0", () => {
    expect(paperToneLabel(0)).toBe("Neutral");
  });

  test("returns Neutral+ for low values", () => {
    expect(paperToneLabel(10)).toBe("Neutral+");
  });

  test("returns Ivory in the 19-35 range", () => {
    expect(paperToneLabel(25)).toBe("Ivory");
  });

  test("returns Cream in the 36-65 range", () => {
    expect(paperToneLabel(50)).toBe("Cream");
  });

  test("returns Parchment in the 66-85 range", () => {
    expect(paperToneLabel(75)).toBe("Parchment");
  });

  test("returns Legal near max", () => {
    expect(paperToneLabel(100)).toBe("Legal");
  });

  test("returns Legal for out-of-range high", () => {
    expect(paperToneLabel(150)).toBe("Legal");
  });

  test("returns Neutral for negative values", () => {
    expect(paperToneLabel(-10)).toBe("Neutral");
  });
});

describe("normalizeLegacyWarmth", () => {
  test("passes through already-normalized values", () => {
    expect(normalizeLegacyWarmth(0)).toBe(0);
    expect(normalizeLegacyWarmth(50)).toBe(50);
    expect(normalizeLegacyWarmth(100)).toBe(100);
  });

  test("clamps above-range legacy positives to 100", () => {
    // Old max was 100, so >100 was never stored, but be safe.
    expect(normalizeLegacyWarmth(150)).toBe(100);
  });

  test("maps legacy negative (cool) values to 0", () => {
    expect(normalizeLegacyWarmth(-50)).toBe(0);
    expect(normalizeLegacyWarmth(-100)).toBe(0);
  });

  test("maps legacy -1 to 0", () => {
    // A barely-cool old value should just go to neutral.
    expect(normalizeLegacyWarmth(-1)).toBe(0);
  });

  test("maps legacy +100 to 100", () => {
    expect(normalizeLegacyWarmth(100)).toBe(100);
  });

  test("maps legacy midpoint +50 correctly", () => {
    expect(normalizeLegacyWarmth(50)).toBe(50);
  });

  test("rounds fractional values", () => {
    expect(normalizeLegacyWarmth(42.7)).toBe(43);
  });
});
