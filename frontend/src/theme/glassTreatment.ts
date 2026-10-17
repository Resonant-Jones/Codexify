/**
 * Glass Treatment — a material axis orthogonal to every other appearance axis.
 *
 * ADR-064 establishes that Codexify material personalization is
 * multidimensional and additive, and that a personalization control represents
 * one stable visual transformation. Glass Treatment adds a new axis without
 * replacing or overloading an established one:
 *
 *   - it does NOT alter theme polarity;
 *   - it does NOT alter Surface Depth (density / lightness / weight);
 *   - it does NOT alter Surface Temperature or Paper Tone (chromatic bias);
 *   - it does NOT alter Accent Color (interaction / state signaling); and
 *   - it does NOT alter Background Treatment (wallpaper depth / fade).
 *
 * Persistence doctrine: ADR-064 prohibits semantic reuse of an existing key.
 * `cfy.glassTreatment` is a dedicated new key and never reads or writes
 * `cfy.surfaceDepth`, `cfy.surfaceWarmth`, `cfy.surfaceTemperature`,
 * `cfy.lightPaperTone`, or any accent key.
 *
 * Preference vs. effective treatment are deliberately separate concepts. The
 * saved preference records what the user chose; the *effective* treatment is
 * what actually renders after accessibility overrides. A reduced-transparency
 * system preference can suppress refraction and blur for readability without
 * rewriting the user's saved choice — the same discipline the toolbar uses
 * when a contrast backing overrides the optical effect.
 */

export type GlassTreatment = "refractive" | "frosted" | "solid";

export type GlassTreatmentOption = {
  id: GlassTreatment;
  label: string;
  description: string;
  /** True when this treatment mounts and runs the WebGL refraction renderer. */
  usesWebGL: boolean;
  /** True when this treatment relies on CSS backdrop blur. */
  usesBackdropBlur: boolean;
};

export const GLASS_TREATMENTS: readonly GlassTreatmentOption[] = [
  {
    id: "refractive",
    label: "Refractive",
    description:
      "Optical refraction: real image displacement with edge aberration and glass depth.",
    usesWebGL: true,
    usesBackdropBlur: false,
  },
  {
    id: "frosted",
    label: "Frosted",
    description:
      "Uniform translucent blur with no optical distortion.",
    usesWebGL: false,
    usesBackdropBlur: true,
  },
  {
    id: "solid",
    label: "Solid",
    description:
      "Opaque material with no background blur and no refraction.",
    usesWebGL: false,
    usesBackdropBlur: false,
  },
] as const;

/**
 * Dedicated preference key. Never overloads an existing appearance key.
 * `cfy.surfaceWarmth` in particular is documented in ADR-064 as a legacy
 * ambiguous key and must not be reused.
 */
export const GLASS_TREATMENT_STORAGE_KEY = "cfy.glassTreatment";

/** The shipped default preserves Codexify's existing refractive identity. */
export const DEFAULT_GLASS_TREATMENT: GlassTreatment = "refractive";

export function isGlassTreatment(value: unknown): value is GlassTreatment {
  return (
    value === "refractive" || value === "frosted" || value === "solid"
  );
}

export function getGlassTreatmentOption(
  treatment: GlassTreatment
): GlassTreatmentOption {
  return (
    GLASS_TREATMENTS.find((option) => option.id === treatment) ??
    GLASS_TREATMENTS[0]
  );
}

/**
 * Read and validate the persisted preference.
 * Anything unrecognized — missing, malformed, or a legacy/foreign value —
 * falls back to the default rather than throwing or rendering an unknown mode.
 */
export function readGlassTreatment(
  storage: Pick<Storage, "getItem"> | null | undefined =
  typeof window !== "undefined" ? window.localStorage : null
): GlassTreatment {
  if (!storage) return DEFAULT_GLASS_TREATMENT;
  try {
    const raw = storage.getItem(GLASS_TREATMENT_STORAGE_KEY);
    return isGlassTreatment(raw) ? raw : DEFAULT_GLASS_TREATMENT;
  } catch {
    // Private-mode / quota / disabled storage must not break the shell.
    return DEFAULT_GLASS_TREATMENT;
  }
}

/** Persist the preference. Returns false when storage is unavailable. */
export function writeGlassTreatment(
  treatment: GlassTreatment,
  storage: Pick<Storage, "setItem"> | null | undefined =
    typeof window !== "undefined" ? window.localStorage : null
): boolean {
  if (!storage) return false;
  try {
    storage.setItem(GLASS_TREATMENT_STORAGE_KEY, treatment);
    return true;
  } catch {
    return false;
  }
}

export type ResolvedGlassMaterial = {
  /** What the user saved. Never rewritten by accessibility overrides. */
  preference: GlassTreatment;
  /** What actually renders. May differ from `preference`. */
  effective: GlassTreatment;
  /** True when accessibility (not the user) forced a different mode. */
  overriddenForAccessibility: boolean;
  /** Why the effective treatment differs, for diagnostics and tests. */
  overrideReason: "none" | "reduced-transparency";
};

/**
 * Resolve the saved preference into the treatment that will actually render.
 *
 * System reduced-transparency is an accessibility signal, not a style
 * preference: users who enable it are asking for less optical processing of
 * what is behind their content. We honour it by falling back to the opaque
 * `solid` treatment — it is the only mode with neither refraction nor
 * backdrop blur. The saved preference is deliberately left untouched so the
 * user's choice is restored when the setting is turned back off.
 */
export function resolveGlassMaterial(
  preference: GlassTreatment,
  opts: { reducedTransparency?: boolean } = {}
): ResolvedGlassMaterial {
  if (opts.reducedTransparency && preference !== "solid") {
    return {
      preference,
      effective: "solid",
      overriddenForAccessibility: true,
      overrideReason: "reduced-transparency",
    };
  }
  return {
    preference,
    effective: preference,
    overriddenForAccessibility: false,
    overrideReason: "none",
  };
}

/**
 * Read the system reduced-transparency preference.
 * `prefers-reduced-transparency` is not universally supported; unsupported
 * browsers report no match and fall through to the user's saved preference.
 */
export function prefersReducedTransparency(): boolean {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return false;
  }
  try {
    return window.matchMedia("(prefers-reduced-transparency: reduce)").matches;
  } catch {
    return false;
  }
}

/** Subscribe to system reduced-transparency changes. Returns an unsubscribe. */
export function onReducedTransparencyChange(
  onChange: (reduced: boolean) => void
): () => void {
  if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
    return () => {};
  }
  let query: MediaQueryList;
  try {
    query = window.matchMedia("(prefers-reduced-transparency: reduce)");
  } catch {
    return () => {};
  }
  const handler = (event: MediaQueryListEvent | MediaQueryList) =>
    onChange(event.matches);
  if (typeof query.addEventListener === "function") {
    query.addEventListener("change", handler);
    return () => query.removeEventListener("change", handler);
  }
  // Safari < 14 legacy API.
  const legacy = query as unknown as {
    addListener?: (cb: () => void) => void;
    removeListener?: (cb: () => void) => void;
  };
  legacy.addListener?.(handler as unknown as () => void);
  return () => legacy.removeListener?.(handler as unknown as () => void);
}