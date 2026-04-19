import type { CSSProperties } from "react";

import {
  MOBILE_INTERACTION,
  type MobileCompanionSurfaceState,
} from "./mobileInteractionContract";
import type { MobileGestureState } from "./mobileMotionContract";

export type MobileNavigationRailFeedbackContext = Pick<
  MobileGestureState,
  "isPhoneShell" | "isCoarsePointer" | "prefersReducedMotion"
>;

export const NAVIGATION_RAIL_FEEDBACK = {
  activeScale: 1.015,
  inactiveOpacity: 0.8,
  activeOpacity: 1,
  reducedMotionInactiveOpacity: 0.78,
  transitionTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
} as const;

export function getMobileNavigationRailPillStyle(
  context: MobileNavigationRailFeedbackContext,
  isActive: boolean
): CSSProperties {
  const { isPhoneShell, prefersReducedMotion, isCoarsePointer } = context;

  if (!isPhoneShell || !isCoarsePointer) {
    return {};
  }

  if (prefersReducedMotion) {
    return {
      transitionDuration: `${MOBILE_INTERACTION.reducedMotionReleaseMs}ms`,
      transitionTimingFunction: "ease",
      opacity: isActive
        ? NAVIGATION_RAIL_FEEDBACK.activeOpacity
        : NAVIGATION_RAIL_FEEDBACK.reducedMotionInactiveOpacity,
    };
  }

  return {
    transitionDuration: `${MOBILE_INTERACTION.releaseMs}ms`,
    transitionTimingFunction: NAVIGATION_RAIL_FEEDBACK.transitionTimingFunction,
    transitionProperty: "transform, opacity, color, background-color, border-color, box-shadow, filter",
    transform: isActive ? `scale(${NAVIGATION_RAIL_FEEDBACK.activeScale})` : "scale(1)",
    opacity: isActive
      ? NAVIGATION_RAIL_FEEDBACK.activeOpacity
      : NAVIGATION_RAIL_FEEDBACK.inactiveOpacity,
    filter: isActive ? "saturate(1.01)" : "saturate(0.985)",
  };
}

export function getMobileNavigationRailSurfaceState(
  isActive: boolean
): MobileCompanionSurfaceState {
  return isActive ? "open" : "collapsed";
}
