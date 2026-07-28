/**
 * Bounded canonical user-accent-preference tokens.
 *
 * These values mirror ``guardian/user_profile_tokens.py`` exactly and must
 * stay in sync.  They describe account-scoped presentation-preference
 * identity, not raw CSS colours.
 */

export const USER_ACCENT_TOKENS = [
  "default",
  "blue",
  "cyan",
  "emerald",
  "amber",
  "rose",
  "violet",
  "slate",
] as const

export type UserAccentToken = (typeof USER_ACCENT_TOKENS)[number]

export const DEFAULT_USER_ACCENT_TOKEN: UserAccentToken = "default"

/** Return ``true`` when *value* is a recognised accent token. */
export function isUserAccentToken(value: unknown): value is UserAccentToken {
  if (typeof value !== "string") return false
  return (USER_ACCENT_TOKENS as readonly string[]).includes(value)
}

/**
 * Normalise an arbitrary accent string into a canonical token.
 *
 * Unknown, missing, or non-string input always resolves to ``"default"``.
 */
export function normalizeUserAccentToken(value: unknown): UserAccentToken {
  return isUserAccentToken(value) ? value : DEFAULT_USER_ACCENT_TOKEN
}

/** Human-readable labels for the selector UI. */
export const USER_ACCENT_LABELS: Record<UserAccentToken, string> = {
  default: "Default",
  blue: "Blue",
  cyan: "Cyan",
  emerald: "Emerald",
  amber: "Amber",
  rose: "Rose",
  violet: "Violet",
  slate: "Slate",
}

/**
 * CSS custom-property mappings for each canonical accent token.
 *
 * Tokens are clean colour names, never raw hex, ``var(...)``, gradients, or
 * URL values.  CSS definitions are appended to ``:root`` when the accent
 * changes so selectors never interpolate untrusted backend data directly.
 */
export const USER_ACCENT_CSS_VARS: Record<UserAccentToken, Record<string, string>> = {
  default: {},
  blue: {
    "--user-accent-border": "color-mix(in oklab, #60a5fa 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #60a5fa 8%, var(--chip-bg))",
    "--user-accent-label": "#bfdbfe",
    "--user-accent-focus": "#60a5fa",
  },
  cyan: {
    "--user-accent-border": "color-mix(in oklab, #22d3ee 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #22d3ee 8%, var(--chip-bg))",
    "--user-accent-label": "#cffafe",
    "--user-accent-focus": "#22d3ee",
  },
  emerald: {
    "--user-accent-border": "color-mix(in oklab, #34d399 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #34d399 8%, var(--chip-bg))",
    "--user-accent-label": "#d1fae5",
    "--user-accent-focus": "#34d399",
  },
  amber: {
    "--user-accent-border": "color-mix(in oklab, #fbbf24 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #fbbf24 8%, var(--chip-bg))",
    "--user-accent-label": "#fef3c7",
    "--user-accent-focus": "#fbbf24",
  },
  rose: {
    "--user-accent-border": "color-mix(in oklab, #fb7185 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #fb7185 8%, var(--chip-bg))",
    "--user-accent-label": "#ffe4e6",
    "--user-accent-focus": "#fb7185",
  },
  violet: {
    "--user-accent-border": "color-mix(in oklab, #a78bfa 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #a78bfa 8%, var(--chip-bg))",
    "--user-accent-label": "#ede9fe",
    "--user-accent-focus": "#a78bfa",
  },
  slate: {
    "--user-accent-border": "color-mix(in oklab, #94a3b8 40%, var(--chip-border))",
    "--user-accent-surface": "color-mix(in oklab, #94a3b8 8%, var(--chip-bg))",
    "--user-accent-label": "#e2e8f0",
    "--user-accent-focus": "#94a3b8",
  },
}
