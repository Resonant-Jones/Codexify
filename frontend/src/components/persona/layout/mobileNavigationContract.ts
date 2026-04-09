import type { CSSProperties } from "react";

import type { MobileShellProfile } from "./mobileShellProfile";

export type MobileWorkspaceSummonCopy = {
  label: string;
  ariaLabel: string;
  title: string;
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
  mobileShellProfile: Pick<MobileShellProfile, "topNav">
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
    scrollPaddingInline: mobileShellProfile.topNav.scrollable
      ? mobileShellProfile.topNav.railEdgePadding
      : undefined,
    scrollbarWidth: mobileShellProfile.topNav.scrollable ? "none" : undefined,
    WebkitOverflowScrolling: mobileShellProfile.topNav.scrollable
      ? "touch"
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
