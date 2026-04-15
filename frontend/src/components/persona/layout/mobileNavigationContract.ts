import type { CSSProperties } from "react";

import {
  MOBILE_INTERACTION,
  getMobileTapTargetStyle,
  getMobileTopNavDockStyle,
  getMobileTopNavRailStyle,
  getMobileWorkspaceSummonCopy,
} from "./mobileInteractionContract";
import {
  getMobileNavigationRailPillStyle,
  type MobileNavigationRailFeedbackContext,
} from "./navigationRailFeedbackContract";
import { getMobileNavPillSelectionStyle } from "./mobileNavSelectionContract";

export {
  getMobileNavPillSelectionStyle,
  getMobileTopNavDockStyle,
  getMobileTopNavRailStyle,
  getMobileWorkspaceSummonCopy,
};

export type MobileNavPillFeedbackContext = MobileNavigationRailFeedbackContext;

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
  return getMobileNavigationRailPillStyle(context, isActive);
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
      transitionDuration: `${MOBILE_INTERACTION.reducedMotionReleaseMs}ms`,
      transitionTimingFunction: "ease",
      opacity: isOpen ? 0.9 : 0.8,
    };
  }

  return {
    transitionProperty: "transform, opacity",
    transitionDuration: `${MOBILE_INTERACTION.releaseMs}ms`,
    transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    opacity: isOpen ? 1 : 0.96,
    transform: isOpen ? "scale(1)" : "scale(0.99)",
  };
}
