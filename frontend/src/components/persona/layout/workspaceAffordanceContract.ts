import { PanelLeftClose, PanelLeftOpen } from "lucide-react";
import type { CSSProperties } from "react";

import {
  getMobileCompanionSurfaceStyle,
  type MobileCompanionSurfaceState,
} from "./mobileInteractionContract";

export type WorkspaceAffordanceState = MobileCompanionSurfaceState;

export type WorkspaceAffordanceCopy = {
  label: string;
  ariaLabel: string;
  title: string;
};

export const WORKSPACE_AFFORDANCE = {
  iconClassName: "h-4 w-4 shrink-0",
  labelGap: "0.5rem",
} as const;

export function getWorkspaceAffordanceState({
  isPhoneShell,
  isOpen,
  isClosing,
}: {
  isPhoneShell: boolean;
  isOpen: boolean;
  isClosing?: boolean;
}): WorkspaceAffordanceState {
  if (isPhoneShell && (isOpen || isClosing)) {
    return "open";
  }

  return isOpen ? "open" : "collapsed";
}

export function getWorkspaceAffordanceCopy(
  state: WorkspaceAffordanceState
): WorkspaceAffordanceCopy {
  return state === "open"
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

export function getWorkspaceAffordanceSurfaceStyle(
  isPhoneShell: boolean,
  state: WorkspaceAffordanceState
): CSSProperties {
  return getMobileCompanionSurfaceStyle(isPhoneShell, state);
}

export function getWorkspaceAffordanceIcon(
  state: WorkspaceAffordanceState
): typeof PanelLeftClose {
  return state === "open" ? PanelLeftClose : PanelLeftOpen;
}
