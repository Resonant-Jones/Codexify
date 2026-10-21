import { describe, expect, it, vi } from "vitest";

import {
  DEFAULT_GLASS_TREATMENT,
  GLASS_TREATMENTS,
  GLASS_TREATMENT_STORAGE_KEY,
  isGlassTreatment,
  readGlassTreatment,
  resolveGlassMaterial,
  writeGlassTreatment,
  type GlassTreatment,
} from "./glassTreatment";

function memoryStorage(initial: Record<string, string> = {}) {
  const map = new Map(Object.entries(initial));
  return {
    getItem: (k: string) => (map.has(k) ? map.get(k)! : null),
    setItem: (k: string, v: string) => void map.set(k, v),
    _map: map,
  };
}

describe("glass treatment option catalog", () => {
  it("exposes exactly three treatments", () => {
    expect(GLASS_TREATMENTS.map((o) => o.id)).toEqual([
      "refractive",
      "frosted",
      "solid",
    ]);
  });

  it("defaults to refractive so shipped behaviour is preserved", () => {
    expect(DEFAULT_GLASS_TREATMENT).toBe("refractive");
  });

  it("only refractive mounts WebGL", () => {
    for (const option of GLASS_TREATMENTS) {
      expect(option.usesWebGL).toBe(option.id === "refractive");
    }
  });

  it("only frosted uses backdrop blur", () => {
    for (const option of GLASS_TREATMENTS) {
      expect(option.usesBackdropBlur).toBe(option.id === "frosted");
    }
  });

  it("gives each treatment a distinct rendering contract", () => {
    const contracts = new Set(
      GLASS_TREATMENTS.map((o) => `${o.usesWebGL}:${o.usesBackdropBlur}`)
    );
    // Blur radius alone must not be what distinguishes them.
    expect(contracts.size).toBe(3);
  });
});

describe("isGlassTreatment", () => {
  it("accepts only the three known ids", () => {
    expect(isGlassTreatment("refractive")).toBe(true);
    expect(isGlassTreatment("frosted")).toBe(true);
    expect(isGlassTreatment("solid")).toBe(true);
  });

  it("rejects unknown, legacy and non-string values", () => {
    for (const bad of [
      "matte",
      "",
      "REFRACTIVE",
      null,
      undefined,
      3,
      {},
      ["solid"],
    ]) {
      expect(isGlassTreatment(bad)).toBe(false);
    }
  });
});

describe("persistence", () => {
  it("uses a dedicated key that never collides with ADR-064 appearance keys", () => {
    expect(GLASS_TREATMENT_STORAGE_KEY).toBe("cfy.glassTreatment");
    // ADR-064 forbids semantic reuse of these keys.
    for (const reserved of [
      "cfy.surfaceDepth",
      "cfy.surfaceWarmth",
      "cfy.surfaceTemperature",
      "cfy.lightPaperTone",
    ]) {
      expect(GLASS_TREATMENT_STORAGE_KEY).not.toBe(reserved);
    }
  });

  it("round-trips every treatment", () => {
    const storage = memoryStorage();
    for (const option of GLASS_TREATMENTS) {
      expect(writeGlassTreatment(option.id, storage)).toBe(true);
      expect(readGlassTreatment(storage)).toBe(option.id);
    }
  });

  it("falls back to the default when the stored value is invalid", () => {
    expect(readGlassTreatment(memoryStorage())).toBe(DEFAULT_GLASS_TREATMENT);
    for (const bad of ["matte", "", "SOLID", "1"]) {
      expect(readGlassTreatment(memoryStorage({ [GLASS_TREATMENT_STORAGE_KEY]: bad })))
        .toBe(DEFAULT_GLASS_TREATMENT);
    }
  });

  it("returns the default when storage is unavailable", () => {
    expect(readGlassTreatment(null)).toBe(DEFAULT_GLASS_TREATMENT);
    expect(readGlassTreatment(undefined)).toBe(DEFAULT_GLASS_TREATMENT);
    expect(writeGlassTreatment("solid", null)).toBe(false);
  });

  it("survives storage that throws", () => {
    const hostile = {
      getItem: () => {
        throw new Error("SecurityError");
      },
      setItem: () => {
        throw new Error("QuotaExceededError");
      },
    };
    expect(readGlassTreatment(hostile)).toBe(DEFAULT_GLASS_TREATMENT);
    expect(writeGlassTreatment("frosted", hostile)).toBe(false);
  });

  it("does not read or write any other appearance key", () => {
    const storage = memoryStorage();
    writeGlassTreatment("solid", storage);
    expect([...storage._map.keys()]).toEqual([GLASS_TREATMENT_STORAGE_KEY]);
  });
});

describe("resolveGlassMaterial", () => {
  it("passes the preference through when no override applies", () => {
    for (const option of GLASS_TREATMENTS) {
      const resolved = resolveGlassMaterial(option.id);
      expect(resolved.effective).toBe(option.id);
      expect(resolved.preference).toBe(option.id);
      expect(resolved.overriddenForAccessibility).toBe(false);
      expect(resolved.overrideReason).toBe("none");
    }
  });

  it("falls back to solid under reduced transparency without rewriting the preference", () => {
    const resolved = resolveGlassMaterial("refractive", {
      reducedTransparency: true,
    });
    expect(resolved.effective).toBe("solid");
    // The user's saved choice survives the accessibility override.
    expect(resolved.preference).toBe("refractive");
    expect(resolved.overriddenForAccessibility).toBe(true);
    expect(resolved.overrideReason).toBe("reduced-transparency");
  });

  it("overrides frosted too, since it still uses backdrop blur", () => {
    expect(
      resolveGlassMaterial("frosted", { reducedTransparency: true }).effective
    ).toBe("solid");
  });

  it("leaves an explicit solid preference untouched", () => {
    const resolved = resolveGlassMaterial("solid", {
      reducedTransparency: true,
    });
    expect(resolved.effective).toBe("solid");
    expect(resolved.overriddenForAccessibility).toBe(false);
  });

  it("restores the saved preference when reduced transparency is turned off", () => {
    const preference: GlassTreatment = "refractive";
    expect(
      resolveGlassMaterial(preference, { reducedTransparency: true }).effective
    ).toBe("solid");
    expect(
      resolveGlassMaterial(preference, { reducedTransparency: false }).effective
    ).toBe("refractive");
  });
});

describe("orthogonality (ADR-064)", () => {
  it("resolves independently of theme polarity and other material axes", () => {
    // The resolver takes only the treatment; it cannot observe or derive from
    // polarity, depth, warmth, paper tone, accent or wallpaper state. That is
    // the structural guarantee of orthogonality.
    const source = resolveGlassMaterial.toString();
    for (const forbidden of [
      "resolved",
      "mode",
      "surfaceDepth",
      "surfaceWarmth",
      "paperTone",
      "accent",
      "wallpaper",
    ]) {
      expect(source.toLowerCase()).not.toContain(forbidden.toLowerCase());
    }
  });
});