import { describe, expect, it } from "vitest"
import {
  DEFAULT_USER_ACCENT_TOKEN,
  USER_ACCENT_CSS_VARS,
  USER_ACCENT_LABELS,
  USER_ACCENT_TOKENS,
  isUserAccentToken,
  normalizeUserAccentToken,
} from "../../../src/contracts/userAccentTokens"

describe("User accent tokens (frontend registry)", () => {
  it("contains the exact canonical token set", () => {
    expect(USER_ACCENT_TOKENS).toEqual([
      "default",
      "blue",
      "cyan",
      "emerald",
      "amber",
      "rose",
      "violet",
      "slate",
    ])
  })

  it("has a default token that is a valid member", () => {
    expect(DEFAULT_USER_ACCENT_TOKEN).toBe("default")
    expect(USER_ACCENT_TOKENS).toContain(DEFAULT_USER_ACCENT_TOKEN)
  })

  it("has no duplicate tokens", () => {
    expect(USER_ACCENT_TOKENS.length).toBe(new Set(USER_ACCENT_TOKENS).size)
  })

  it("normalises unknown values to default", () => {
    expect(normalizeUserAccentToken(null)).toBe("default")
    expect(normalizeUserAccentToken(undefined)).toBe("default")
    expect(normalizeUserAccentToken("")).toBe("default")
    expect(normalizeUserAccentToken("#ff00ff")).toBe("default")
    expect(normalizeUserAccentToken("var(--accent)")).toBe("default")
    expect(normalizeUserAccentToken("url(https://example.com)")).toBe("default")
    expect(normalizeUserAccentToken("linear-gradient(red, blue)")).toBe("default")
    expect(normalizeUserAccentToken("invalid")).toBe("default")
  })

  it("normalises valid tokens through unchanged", () => {
    for (const token of USER_ACCENT_TOKENS) {
      expect(normalizeUserAccentToken(token)).toBe(token)
    }
  })

  it("isUserAccentToken rejects non-string and invalid input", () => {
    expect(isUserAccentToken(null)).toBe(false)
    expect(isUserAccentToken(undefined)).toBe(false)
    expect(isUserAccentToken(123)).toBe(false)
    expect(isUserAccentToken("")).toBe(false)
    expect(isUserAccentToken("#ff00ff")).toBe(false)
  })

  it("isUserAccentToken accepts all canonical tokens", () => {
    for (const token of USER_ACCENT_TOKENS) {
      expect(isUserAccentToken(token)).toBe(true)
    }
  })

  it("has accessible labels for every token", () => {
    for (const token of USER_ACCENT_TOKENS) {
      const label = USER_ACCENT_LABELS[token]
      expect(typeof label).toBe("string")
      expect(label.length).toBeGreaterThan(0)
    }
  })

  it("has complete CSS variable mappings for every token", () => {
    for (const token of USER_ACCENT_TOKENS) {
      expect(USER_ACCENT_CSS_VARS[token]).toBeDefined()
    }
  })

  it("default token has empty CSS variable map", () => {
    expect(USER_ACCENT_CSS_VARS.default).toEqual({})
  })

  it("non-default tokens have the required CSS variable keys", () => {
    const required = [
      "--user-accent-border",
      "--user-accent-surface",
      "--user-accent-label",
      "--user-accent-focus",
    ]
    for (const token of USER_ACCENT_TOKENS) {
      if (token === "default") continue
      const vars = USER_ACCENT_CSS_VARS[token]
      for (const key of required) {
        expect(vars[key]).toBeDefined()
        expect(typeof vars[key]).toBe("string")
      }
    }
  })

  it("CSS variable values never contain gradient or URL tokens", () => {
    for (const token of USER_ACCENT_TOKENS) {
      const vars = USER_ACCENT_CSS_VARS[token]
      for (const value of Object.values(vars)) {
        expect(value).not.toContain("linear-gradient(")
        expect(value).not.toContain("url(")
      }
    }
  })
})
