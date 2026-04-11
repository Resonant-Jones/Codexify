import type { CSSProperties } from "react";

import type { MobileShellProfile } from "./mobileShellProfile";
import type { MobileGestureState } from "./mobileMotionContract";
import { MOBILE_INTERACTION } from "./mobileInteractionContract";

export type MobileWorkspaceSummonCopy = {
  label: string;
  ariaLabel: string;
  title: string;
};

export type MobileNavPillFeedbackContext = {
  isPhoneShell: boolean;
  prefersReducedMotion: boolean;
  isCoarsePointer: boolean;
};

export function getMobileTopNavDockStyle(
  mobileShellProfile: Pick<MobileShellProfile, "topNav">
): CSSProperties {
  return {
    paddingTop: "var(--pill-pad-y)",
    paddingBottom: "var(--pill-pad-y)",
    width: mobileShellProfile.topNav.width,
    maxWidth: "100%",
    minWidth: 0,
    display: "flex",
    alignItems: "center",
    overflow: "hidden",
    boxSizing: "border-box",
  };
}

export function getMobileTopNavRailStyle(
  mobileShellProfile: Pick<MobileShellProfile, "topNav">,
  gestureState?: Pick<MobileGestureState, "isPhoneShell" | "allowMomentumScroll">
): CSSProperties {
  return {
    flex: "1 1 auto",
    minWidth: 0,
    display: "flex",
    alignItems: "center",
    flexWrap: "nowrap",
    gap: mobileShellProfile.topNav.railGap,
    paddingInline: mobileShellProfile.topNav.railEdgePadding,
    overflowX: mobileShellProfile.topNav.scrollable ? "auto" : undefined,
    overflowY: mobileShellProfile.topNav.scrollable ? "hidden" : undefined,
    overscrollBehaviorX: mobileShellProfile.topNav.scrollable
      ? "contain"
      : undefined,
    touchAction:
      mobileShellProfile.topNav.scrollable && gestureState?.isPhoneShell
        ? "pan-x"
        : undefined,
    scrollPaddingInline: mobileShellProfile.topNav.scrollable
      ? mobileShellProfile.topNav.railEdgePadding
      : undefined,
    scrollbarWidth: mobileShellProfile.topNav.scrollable ? "none" : undefined,
    WebkitOverflowScrolling: mobileShellProfile.topNav.scrollable
      ? gestureState?.allowMomentumScroll === false
        ? undefined
        : "touch"
      : undefined,
    whiteSpace: "nowrap",
    boxSizing: "border-box",
  };
}

export function getMobileWorkspaceSummonCopy(
  isOpen: boolean
): MobileWorkspaceSummonCopy {
  return isOpen
    ? {
        label: "Close Workspace",
        ariaLabel: "Close Workspace",
        title: "Hide the Workspace drawer",
      }
    : {
        label: "Open Workspace",
        ariaLabel: "Open Workspace",
        title: "Open the Workspace drawer",
      };
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
      transitionDuration: "80ms",
      transitionTimingFunction: "ease",
      opacity: isActive ? 1 : 0.75,
    };
  }

  // Full motion: spring-like transition for active state
  return {
    transitionDuration: isActive
      ? `${MOBILE_INTERACTION.pressReleaseMs + MOBILE_INTERACTION.settleMs}ms`
      : `${MOBILE_INTERACTION.pressScaleDownMs}ms`,
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
      transitionDuration: "80ms",
      transitionTimingFunction: "ease",
      opacity: isOpen ? 0.9 : 0.8,
    };
  }

  return {
    transitionDuration: `${MOBILE_INTERACTION.pressScaleDownMs}ms`,
    transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
    transform: isOpen ? "scale(1)" : "scale(1)",
  };
}
