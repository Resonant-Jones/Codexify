/**
 * Settings Density Contract
 *
 * Centralizes repeated spacing, typography, and alignment semantics for
 * the Settings surface. This keeps Settings consistent with the broader
 * mobile shell token system without local improvisation.
 *
 * Usage:
 *   import { SETTINGS_DENSITY } from "./settingsDensityContract";
 *   style={{ ...SETTINGS_DENSITY.SECTION_HEADING }}
 */

export const SETTINGS_DENSITY = {
  /**
   * Space between major sections within a SettingsSectionCard.
   * Corresponds to the outer shell gap rhythm (var(--shell-gap) = 16px).
   */
  sectionGap: "var(--shell-gap)",

  /**
   * Space between a section title and its description/helper text.
   * Tighter than sectionGap to keep heading and description cohesive.
   */
  headingDescriptionGap: "calc(var(--radius-micro) / 2)", // 6px

  /**
   * Space between description and its first control group.
   * Tight — follows immediately after explanatory text.
   */
  descriptionControlGap: "calc(var(--radius-micro) / 2)", // 6px

  /**
   * Space between grouped controls within a section.
   */
  controlGroupGap: "var(--radius-micro)", // 12px

  /**
   * Section title — consistent size across all Settings tabs.
   * Uses sm scale (14px) rather than base (16px) to stay dense.
   */
  sectionTitle: {
    fontSize: "0.875rem", // 14px / text-sm
    fontWeight: 600,
    lineHeight: 1.25,
    color: "var(--text)",
  },

  /**
   * Section subtitle / description body text.
   * Muted tone, compact line height for density.
   */
  sectionDescription: {
    fontSize: "0.75rem", // 12px / text-xs
    lineHeight: 1.5, // ~leading-5 equivalent
    color: "var(--muted)",
  },

  /**
   * Metadata label (e.g., uppercase tracking labels inside panels).
   */
  metaLabel: {
    fontSize: "0.688rem", // ~11px
    textTransform: "uppercase",
    letterSpacing: "0.16em",
    color: "var(--muted)",
  },

  /**
   * Standard inner card padding for settings sub-panels.
   * Mirrors var(--card-pad) for consistency inside nested cards.
   */
  innerPad: "var(--card-pad)",

  /**
   * Standard inner card border-radius.
   */
  innerRadius: "var(--card-radius)",

  /**
   * Consistent border color for settings inner elements.
   */
  innerBorderColor: "var(--panel-border)",

  /**
   * Consistent background for settings inner elements.
   */
  innerBackground: "color-mix(in srgb, var(--panel-bg) 92%, transparent)",
} as const;

/**
 * Helper: returns inline styles for a settings section heading row
 * (icon + label, vertically centered).
 */
export function getSettingsHeadingRowStyle(): {
  display: "flex";
  alignItems: "center";
  gap: "var(--radius-micro)";
} {
  return {
    display: "flex",
    alignItems: "center",
    gap: "var(--radius-micro)",
  };
}
