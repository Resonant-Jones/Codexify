import type { CSSProperties } from "react";

import type { MobileGestureState } from "./mobileMotionContract";
import {
  getMobileTapTargetStyle,
  getMobileTopNavDockStyle,
  getMobileTopNavRailStyle,
  getMobileWorkspaceSummonCopy,
} from "./mobileInteractionContract";

export { getMobileTopNavDockStyle, getMobileTopNavRailStyle, getMobileWorkspaceSummonCopy };

export type MobileNavPillFeedbackContext = Pick<
  MobileGestureState,
  "isPhoneShell" | "isCoarsePointer" | "prefersReducedMotion"
>;

const MOBILE_NAV_FEEDBACK = {
  activeDurationMs: 180,
  inactiveDurationMs: 120,
  reducedMotionDurationMs: 80,
} as const;

export function getMobileNavigationControlStyle(
  isPhoneShell: boolean,
  options: { square?: boolean } = {}
): CSSProperties {
  return getMobileTapTargetStyle(isPhoneShell, options);
}

/**
 * Returns CSS properties for navigation pill selection feedback.
 * Provides a clearer active affordance with smoother state transitions.
 */
export function getMobileNavPillFeedbackStyle(
  context: MobileNavPillFeedbackContext,
  isActive: boolean
): CSSProperties {
  const { isPhoneShell, prefersReducedMotion, isCoarsePointer } = context;

  if (!isPhoneShell || !isCoarsePointer) {
    return {};
  }

  // Reduced motion: preserve clarity through opacity only
  if (prefersReducedMotion) {
    return {
      transitionDuration: `${MOBILE_NAV_FEEDBACK.reducedMotionDurationMs}ms`,
      transitionTimingFunction: "ease",
      opacity: isActive ? 1 : 0.75,
    };
  }

  // Full motion: spring-like transition for active state
  return {
    transitionProperty: "transform, opacity",
    transitionDuration: isActive
      ? `${MOBILE_NAV_FEEDBACK.activeDurationMs}ms`
      : `${MOBILE_NAV_FEEDBACK.inactiveDurationMs}ms`,
    transitionTimingFunction: isActive
      ? "cubic-bezier(0.34, 1.2, 0.64, 1)"
      : "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    transform: isActive ? "scale(1.02)" : "scale(1)",
  };
}

/**
 * Returns CSS properties for workspace summon/dismiss button feedback.
 * Subtle press feedback that reinforces workspace as a summoned surface.
 */
export function getMobileWorkspaceSummonFeedbackStyle(
  context: MobileNavPillFeedbackContext,
  isOpen: boolean
): CSSProperties {
  const { isPhoneShell, prefersReducedMotion, isCoarsePointer } = context;

  if (!isPhoneShell || !isCoarsePointer) {
    return {};
  }

  if (prefersReducedMotion) {
    return {
      transitionDuration: `${MOBILE_NAV_FEEDBACK.reducedMotionDurationMs}ms`,
      transitionTimingFunction: "ease",
      opacity: isOpen ? 0.9 : 0.8,
    };
  }

  return {
    transitionProperty: "transform, opacity",
    transitionDuration: `${MOBILE_NAV_FEEDBACK.inactiveDurationMs}ms`,
    transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    transform: isOpen ? "scale(1)" : "scale(1)",
  };
}
