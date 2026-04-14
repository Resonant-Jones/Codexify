import type { CSSProperties } from "react";

import type { WorkspaceLayoutMode } from "@/features/workspace/state/useWorkspaceLayoutMode";

export type MobileGestureState = {
  isPhoneShell: boolean;
  isCoarsePointer: boolean;
  prefersReducedMotion: boolean;
  isKeyboardOpen: boolean;
  keyboardInset: number;
  allowMomentumScroll: boolean;
};

export type MobileWorkspaceMotionState =
  | "collapsed"
  | "peek"
  | "open"
  | "focused";

export const MOBILE_MOTION = {
  workspaceSheetEnterMs: 240,
  workspaceSheetExitMs: 180,
  workspaceSheetSettleMs: 60,
  chromeMs: 180,
  reducedMs: 1,
  touchTargetMinHeight: "44px",
  touchTargetMinWidth: "44px",
} as const;

function getMobileMotionDurationMs(
  gestureState: MobileGestureState,
  phase: "enter" | "exit" | "chrome"
): number {
  if (gestureState.prefersReducedMotion) {
    return MOBILE_MOTION.reducedMs;
  }

  switch (phase) {
    case "exit":
      return MOBILE_MOTION.workspaceSheetExitMs;
    case "chrome":
      return gestureState.isKeyboardOpen ? 140 : MOBILE_MOTION.chromeMs;
    case "enter":
    default:
      return MOBILE_MOTION.workspaceSheetEnterMs;
  }
}

function getMobileMotionTimingFunction(
  gestureState: MobileGestureState,
  phase: "enter" | "exit" | "chrome" | "settle"
): string {
  if (gestureState.prefersReducedMotion) {
    return "linear";
  }

  switch (phase) {
    case "exit":
      // Deliberate exit - feels resolved rather than mechanically disappearing
      return "cubic-bezier(0.25, 0.46, 0.65, 0.8)";
    case "settle":
      // Subtle settle at the end - feels intentional
      return "cubic-bezier(0.34, 1.1, 0.64, 1)";
    case "chrome":
      // Quick but smooth chrome transitions
      return gestureState.isKeyboardOpen
        ? "cubic-bezier(0.25, 0.46, 0.45, 0.94)"
        : "cubic-bezier(0.22, 1, 0.36, 1)";
    case "enter":
    default:
      // Spring-like enter - feels responsive and natural
      return "cubic-bezier(0.22, 1, 0.36, 1)";
  }
}

export function getMobileWorkspaceMotionState(
  isPhoneShell: boolean,
  isOpen: boolean,
  layoutMode: WorkspaceLayoutMode
): MobileWorkspaceMotionState {
  if (!isPhoneShell || !isOpen) {
    return "collapsed";
  }

  switch (layoutMode) {
    case "workspace_focus":
      return "focused";
    case "balanced_split":
      return "open";
    case "chat_focus":
    default:
      return "peek";
  }
}

export function getMobileWorkspaceSheetStyle(
  gestureState: MobileGestureState,
  isOpen: boolean,
  isClosing: boolean = false
): CSSProperties {
  const phase = isOpen ? "enter" : isClosing ? "settle" : "exit";
  const durationMs = getMobileMotionDurationMs(gestureState, isOpen ? "enter" : "exit");

  return {
    opacity: gestureState.prefersReducedMotion ? 1 : isOpen ? 1 : 0,
    transform: gestureState.prefersReducedMotion
      ? "none"
      : isOpen
        ? "translate3d(0, 0, 0) scale(1)"
        : "translate3d(12px, 0, 0) scale(0.985)",
    transformOrigin: "center right",
    transitionProperty: gestureState.prefersReducedMotion
      ? "none"
      : "transform, opacity",
    transitionDuration: `${durationMs}ms`,
    transitionTimingFunction: getMobileMotionTimingFunction(gestureState, phase),
    willChange: gestureState.prefersReducedMotion ? undefined : "transform, opacity",
    pointerEvents: isOpen ? "auto" : "none",
  };
}

export function getMobileChromeMotionStyle(
  gestureState: MobileGestureState
): CSSProperties {
  const durationMs = getMobileMotionDurationMs(gestureState, "chrome");

  return {
    transitionProperty: gestureState.prefersReducedMotion
      ? "none"
      : "transform, opacity, box-shadow, border-color",
    transitionDuration: `${durationMs}ms`,
    transitionTimingFunction: getMobileMotionTimingFunction(
      gestureState,
      "chrome"
    ),
    willChange: gestureState.prefersReducedMotion ? undefined : "transform, opacity",
  };
}

export function getMobileTouchTargetStyle(
  gestureState: MobileGestureState,
  options: { square?: boolean } = {}
): CSSProperties {
  if (!gestureState.isPhoneShell) {
    return {};
  }

  return {
    minHeight: MOBILE_MOTION.touchTargetMinHeight,
    minWidth: options.square ? MOBILE_MOTION.touchTargetMinWidth : undefined,
    touchAction: "manipulation",
    WebkitTapHighlightColor: "transparent",
  };
}
