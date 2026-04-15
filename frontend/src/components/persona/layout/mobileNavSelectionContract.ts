import type { CSSProperties } from "react";

import { MOBILE_MOTION, type MobileGestureState } from "./mobileMotionContract";

export type MobileNavSelectionContext = Pick<
  MobileGestureState,
  "isPhoneShell" | "isCoarsePointer" | "prefersReducedMotion"
>;

export const MOBILE_NAV_SELECTION = {
  activeBackground:
    "color-mix(in oklab, var(--accent-strong) 90%, var(--panel-bg) 10%)",
  activeBorderColor:
    "color-mix(in oklab, var(--accent-strong) 54%, var(--panel-border) 46%)",
  activeShadow:
    "0 10px 18px color-mix(in oklab, var(--accent-strong) 24%, transparent), inset 0 0 0 1px color-mix(in oklab, var(--panel-border) 72%, var(--accent-strong) 28%)",
  activeText: "var(--pill-active-text, var(--text))",
  transitionDurationMs: MOBILE_MOTION.navSelectionMs,
  reducedTransitionDurationMs: MOBILE_MOTION.reducedMs,
  transitionTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
  reducedTransitionTimingFunction: "linear",
  transitionProperty: "color, background, border-color, box-shadow, transform, opacity, filter",
} as const;

export function getMobileNavPillSelectionStyle(
  context: MobileNavSelectionContext,
  isActive: boolean
): CSSProperties {
  if (!context.isPhoneShell) {
    return {};
  }

  return {
    transitionProperty: MOBILE_NAV_SELECTION.transitionProperty,
    transitionDuration: `${context.prefersReducedMotion
      ? MOBILE_NAV_SELECTION.reducedTransitionDurationMs
      : MOBILE_NAV_SELECTION.transitionDurationMs}ms`,
    transitionTimingFunction: context.prefersReducedMotion
      ? MOBILE_NAV_SELECTION.reducedTransitionTimingFunction
      : MOBILE_NAV_SELECTION.transitionTimingFunction,
    ...(isActive
      ? {
          color: MOBILE_NAV_SELECTION.activeText,
          background: MOBILE_NAV_SELECTION.activeBackground,
          borderColor: MOBILE_NAV_SELECTION.activeBorderColor,
          boxShadow: MOBILE_NAV_SELECTION.activeShadow,
        }
      : {}),
  };
}
