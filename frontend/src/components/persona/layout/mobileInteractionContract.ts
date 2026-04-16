import type { CSSProperties } from "react";

import type { MobileShellProfile } from "./mobileShellProfile";
import type { MobileGestureState } from "./mobileMotionContract";

export type MobileWorkspaceSummonCopy = {
  label: string;
  ariaLabel: string;
  title: string;
};

export type MobileCompanionSurfaceState = "collapsed" | "open";

export const MOBILE_INTERACTION = {
  pressScale: 0.975,
  pressOpacity: 0.92,
  pressTone: "saturate(0.985) brightness(0.99)",
  releaseMs: 160,
  reducedMotionReleaseMs: 1,
  pressDragCancelDistancePx: 8,
  tapTargetMinHeight: "44px",
  tapTargetMinWidth: "44px",
} as const;

export const MOBILE_INTERACTION_CLASS = {
  pressFeedback: "mobile-press-feedback",
  tapTarget: "mobile-tap-target",
} as const;

export function getMobilePressFeedbackStyle(
  prefersReducedMotion: boolean
): CSSProperties {
  return {
    "--mobile-press-scale": String(MOBILE_INTERACTION.pressScale),
    "--mobile-press-opacity": String(MOBILE_INTERACTION.pressOpacity),
    "--mobile-press-tone": MOBILE_INTERACTION.pressTone,
    "--mobile-press-release-ms": `${
      prefersReducedMotion
        ? MOBILE_INTERACTION.reducedMotionReleaseMs
        : MOBILE_INTERACTION.releaseMs
    }ms`,
  } as CSSProperties;
}

export function getMobileTapTargetStyle(
  isPhoneShell: boolean,
  options: { square?: boolean } = {}
): CSSProperties {
  if (!isPhoneShell) {
    return {};
  }

  return {
    minHeight: MOBILE_INTERACTION.tapTargetMinHeight,
    minWidth: options.square ? MOBILE_INTERACTION.tapTargetMinWidth : undefined,
    touchAction: "manipulation",
    WebkitTapHighlightColor: "transparent",
  };
}

export function getMobilePressSurfaceStyle(
  isPhoneShell: boolean,
  prefersReducedMotion: boolean
): CSSProperties {
  if (!isPhoneShell) {
    return {};
  }

  return {
    transitionProperty: prefersReducedMotion
      ? "opacity, filter, background-color, border-color, box-shadow"
      : "transform, opacity, filter, background-color, border-color, box-shadow",
    transitionDuration: `${
      prefersReducedMotion
        ? MOBILE_INTERACTION.reducedMotionReleaseMs
        : MOBILE_INTERACTION.releaseMs
    }ms`,
    transitionTimingFunction: prefersReducedMotion
      ? "linear"
      : "cubic-bezier(0.22, 1, 0.36, 1)",
  };
}

export function getComposerSendButtonStyle(
  isPhoneShell: boolean,
  state: "idle" | "ready" | "pressed" | "disabled"
): CSSProperties {
  if (isPhoneShell) {
    return {};
  }

  const base: CSSProperties = {
    borderRadius: "9999px",
    borderWidth: "0px",
    borderStyle: "solid",
    boxShadow: "none",
    padding: "0px",
    width: "var(--composer-control-size, 2rem)",
    height: "var(--composer-control-size, 2rem)",
    alignItems: "center",
    justifyContent: "center",
    display: "inline-flex",
    transition: "background 160ms ease, opacity 160ms ease",
  };

  switch (state) {
    case "disabled":
      return { ...base, opacity: 0.5, cursor: "not-allowed" };
    case "pressed":
      return {
        ...base,
        transform: "scale(0.96)",
        background: "color-mix(in oklab, var(--accent-strong) 72%, white 28%)",
        color: "var(--text-on-accent, #111827)",
      };
    case "ready":
      return {
        ...base,
        background: "color-mix(in oklab, var(--accent-strong) 82%, white 18%)",
        color: "var(--text-on-accent, #111827)",
        cursor: "pointer",
      };
    case "idle":
    default:
      return {
        ...base,
        background: "var(--panel-bg)",
        color: "var(--muted)",
        cursor: "pointer",
      };
  }
}

export function getComposerSelectorSurfaceStyle(
  isPhoneShell: boolean
): CSSProperties {
  if (isPhoneShell) {
    return {};
  }

  return {
    borderStyle: "solid",
    borderWidth: "1px",
    borderRadius: "var(--card-radius,19px)",
    borderColor: "color-mix(in oklab, var(--panel-border) 76%, var(--text) 24%)",
    boxShadow:
      "inset 0 1px 0 color-mix(in oklab, var(--panel-border) 20%, transparent)",
    height: "var(--composer-control-size, 2rem)",
    minWidth: "0px",
  };
}

export function getComposerActionMenuSurfaceStyle(
  isPhoneShell: boolean
): CSSProperties {
  if (isPhoneShell) {
    return {};
  }

  return {
    borderStyle: "solid",
    borderWidth: "1px",
    borderRadius: "var(--card-radius,19px)",
    borderColor: "color-mix(in oklab, var(--panel-border) 84%, var(--text) 16%)",
    boxShadow:
      "inset 0 1px 0 color-mix(in oklab, var(--panel-border) 28%, transparent)",
    padding: "0px",
    width: "var(--composer-control-size, 2rem)",
    height: "var(--composer-control-size, 2rem)",
  };
}

export function getComposerControlRowStyle(
  isPhoneShell: boolean
): CSSProperties {
  return {
    display: "flex",
    alignItems: "center",
    gap: "var(--composer-control-gap, 12px)",
    width: "100%",
  };
}

export function getComposerSendSlotStyle(
  isPhoneShell: boolean
): CSSProperties {
  return {
    display: "flex",
    flexShrink: "0",
    alignItems: "center",
    justifyContent: "center",
  };
}

export function getComposerControlSurfaceStyle(
  isPhoneShell: boolean,
  options: { variant?: "rail" | "trigger" } = {}
): CSSProperties {
  if (isPhoneShell) {
    return {};
  }

  const variant = options.variant ?? "trigger";
  const isRail = variant === "rail";

  return {
    borderStyle: "solid",
    borderWidth: "1px",
    borderRadius: "var(--card-radius,19px)",
    borderColor: isRail
      ? "color-mix(in oklab, var(--panel-border) 84%, var(--text) 16%)"
      : "color-mix(in oklab, var(--panel-border) 76%, var(--text) 24%)",
    boxShadow: isRail
      ? "inset 0 1px 0 color-mix(in oklab, var(--panel-border) 28%, transparent)"
      : "inset 0 1px 0 color-mix(in oklab, var(--panel-border) 20%, transparent)",
    padding: isRail ? "calc(var(--composer-control-gap, 12px) / 2)" : undefined,
  };
}

export function getMobileCompanionSurfaceStyle(
  isPhoneShell: boolean,
  state: MobileCompanionSurfaceState
): CSSProperties {
  if (!isPhoneShell) {
    return {};
  }

  return {
    color: "var(--text)",
    background: state === "open" ? "var(--panel-bg)" : "var(--chip-bg)",
    borderColor:
      state === "open" ? "var(--panel-border-strong)" : "var(--chip-border)",
    boxShadow: "none",
  };
}

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
