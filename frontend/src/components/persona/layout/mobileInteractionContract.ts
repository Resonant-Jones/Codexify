/**
 * Mobile Interaction Contract
 *
 * Centralizes micro-interaction semantics for phone-class controls.
 * Provides press/active/release feedback patterns that are:
 * - reduced-motion safe
 * - token-driven (not inline improvised styles)
 * - consistent across nav, workspace, composer, and utility controls
 */

import type { CSSProperties } from "react";
import { MOBILE_MOTION } from "./mobileMotionContract";

/* ─────────────────────────────────────────────────────────────────────────────
   Press Feedback Types
   ───────────────────────────────────────────────────────────────────────────── */

export type PressFeedbackState = "idle" | "pressed" | "released";

export type MobileInteractionContext = {
  isPhoneShell: boolean;
  prefersReducedMotion: boolean;
  coarsePointer: boolean;
};

/* ─────────────────────────────────────────────────────────────────────────────
   Press Feedback Timing Constants
   ───────────────────────────────────────────────────────────────────────────── */

export const MOBILE_INTERACTION = {
  /** Duration for press scale-down on touch start */
  pressScaleDownMs: 60,
  /** Duration for release scale-up animation */
  pressReleaseMs: 120,
  /** Duration for settle/confirm feedback */
  settleMs: 80,
  /** Scale factor when pressed (relative to 1) */
  pressScale: 0.94,
  /** Scale factor when actively selected */
  activeScale: 1.0,
  /** Minimum opacity when pressed */
  pressOpacity: 0.82,
  /** Opacity for submit confirmation flash */
  submitFlashOpacity: 0.6,
} as const;

/* ─────────────────────────────────────────────────────────────────────────────
   Reduced-Motion Safe Interaction Helpers
   ───────────────────────────────────────────────────────────────────────────── */

/**
 * Returns CSS properties for press feedback.
 * When reduced-motion is preferred, returns opacity-only feedback.
 * Otherwise returns both scale and opacity transitions.
 */
export function getMobilePressFeedbackStyle(
  context: MobileInteractionContext,
  state: PressFeedbackState
): CSSProperties {
  const { prefersReducedMotion, coarsePointer } = context;

  // Non-touch or non-phone contexts get minimal feedback
  if (!coarsePointer || !context.isPhoneShell) {
    return {};
  }

  // Reduced motion: only opacity changes
  if (prefersReducedMotion) {
    switch (state) {
      case "pressed":
        return { opacity: MOBILE_INTERACTION.pressOpacity };
      case "released":
        return { opacity: 1 };
      default:
        return { opacity: 1 };
    }
  }

  // Full motion feedback
  switch (state) {
    case "pressed":
      return {
        transform: `scale(${MOBILE_INTERACTION.pressScale})`,
        opacity: MOBILE_INTERACTION.pressOpacity,
        transitionDuration: `${MOBILE_INTERACTION.pressScaleDownMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
      };
    case "released":
      return {
        transform: `scale(${MOBILE_INTERACTION.activeScale})`,
        opacity: 1,
        transitionDuration: `${MOBILE_INTERACTION.pressReleaseMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      };
    default:
      return {
        transform: `scale(${MOBILE_INTERACTION.activeScale})`,
        opacity: 1,
        transitionDuration: `${MOBILE_INTERACTION.pressReleaseMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      };
  }
}

/**
 * Returns CSS properties for nav pill selection feedback.
 * Provides a clearer active affordance with a subtle settle animation.
 */
export function getMobileNavPillFeedbackStyle(
  context: MobileInteractionContext,
  isActive: boolean
): CSSProperties {
  const { prefersReducedMotion, coarsePointer, isPhoneShell } = context;

  if (!coarsePointer || !isPhoneShell) {
    return {};
  }

  if (prefersReducedMotion) {
    return isActive
      ? { opacity: 1 }
      : { opacity: 0.75 };
  }

  return {
    transitionDuration: isActive
      ? `${MOBILE_INTERACTION.settleMs + MOBILE_INTERACTION.pressReleaseMs}ms`
      : `${MOBILE_INTERACTION.pressScaleDownMs}ms`,
    transitionTimingFunction: isActive
      ? "cubic-bezier(0.34, 1.2, 0.64, 1)"
      : "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
  };
}

/**
 * Returns CSS properties for workspace sheet settle/dismiss.
 * Adds a subtle overshoot-ease to the final frame so the motion
 * feels "resolved" rather than mechanically stopping.
 */
export function getMobileWorkspaceSettleStyle(
  context: MobileInteractionContext,
  motionState: "open" | "closed" | "settling"
): CSSProperties {
  const { prefersReducedMotion, isPhoneShell } = context;

  if (!isPhoneShell) {
    return {};
  }

  if (prefersReducedMotion) {
    // For reduced motion, just ensure visibility state is clear
    return motionState === "closed"
      ? { opacity: 0 }
      : { opacity: 1 };
  }

  switch (motionState) {
    case "open":
      return {
        transform: "translateX(0%)",
        transitionDuration: `${MOBILE_MOTION.workspaceSheetEnterMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.22, 1, 0.36, 1)",
      };
    case "settling":
      // Subtle settle at the end of dismiss - feels deliberate
      return {
        transform: "translateX(0%)",
        transitionDuration: `${MOBILE_MOTION.workspaceSheetExitMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.65, 0.8)",
      };
    case "closed":
    default:
      return {
        transform: "translateX(100%)",
        transitionDuration: `${MOBILE_MOTION.workspaceSheetExitMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.65, 0.8)",
      };
  }
}

/**
 * Returns CSS properties for composer send submit confirmation.
 * Provides immediate tactile feedback before streaming begins.
 */
export function getMobileComposerSubmitFeedbackStyle(
  context: MobileInteractionContext,
  phase: "idle" | "submitting" | "submitted"
): CSSProperties {
  const { prefersReducedMotion, coarsePointer, isPhoneShell } = context;

  if (!coarsePointer || !isPhoneShell) {
    return {};
  }

  if (prefersReducedMotion) {
    switch (phase) {
      case "submitting":
        return { opacity: MOBILE_INTERACTION.submitFlashOpacity };
      case "submitted":
        return { opacity: 0.9 };
      default:
        return { opacity: 1 };
    }
  }

  switch (phase) {
    case "submitting":
      // Brief flash confirmation before streaming response
      return {
        transform: `scale(${MOBILE_INTERACTION.pressScale})`,
        opacity: MOBILE_INTERACTION.submitFlashOpacity,
        transitionDuration: `${MOBILE_INTERACTION.pressScaleDownMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.25, 0.46, 0.45, 0.94)",
      };
    case "submitted":
      // Settle back with slight overshoot
      return {
        transform: `scale(${MOBILE_INTERACTION.activeScale})`,
        opacity: 0.9,
        transitionDuration: `${MOBILE_INTERACTION.settleMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.2, 0.64, 1)",
      };
    default:
      return {
        transform: `scale(${MOBILE_INTERACTION.activeScale})`,
        opacity: 1,
        transitionDuration: `${MOBILE_INTERACTION.pressReleaseMs}ms`,
        transitionTimingFunction: "cubic-bezier(0.34, 1.56, 0.64, 1)",
      };
  }
}

/**
 * Returns the transition duration for workspace sheet based on motion preference.
 */
export function getMobileWorkspaceTransitionMs(
  prefersReducedMotion: boolean,
  enter: boolean
): number {
  if (prefersReducedMotion) {
    return MOBILE_MOTION.reducedMs;
  }
  return enter
    ? MOBILE_MOTION.workspaceSheetEnterMs
    : MOBILE_MOTION.workspaceSheetExitMs;
}
