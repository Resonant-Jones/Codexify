import type { ShellViewportClass, ShellViewportProfile } from "./shellBreakpointContract";
import { isPhoneShellViewportClass } from "./shellBreakpointContract";

export type MobileShellProfile = {
  active: boolean;
  shellMode: "default" | "mobile";
  viewportClass: ShellViewportClass;
  topNav: {
    scrollable: boolean;
    width: string;
  };
  guardian: {
    singleLane: boolean;
    frameMaxWidth: string;
    drawerWidth: string;
  };
  workspace: {
    defaultOpen: boolean;
    autoOpenOnDocumentRequest: boolean;
  };
};

const DESKTOP_SHELL_PROFILE = {
  shellMode: "default",
  topNav: {
    scrollable: false,
    width: "auto",
  },
  guardian: {
    singleLane: false,
    frameMaxWidth: "1500px",
    drawerWidth: "min(360px, 90vw)",
  },
  workspace: {
    defaultOpen: true,
    autoOpenOnDocumentRequest: true,
  },
} as const satisfies Omit<MobileShellProfile, "active" | "viewportClass">;

const PHONE_SHELL_PROFILE = {
  shellMode: "mobile",
  topNav: {
    scrollable: true,
    width: "100%",
  },
  guardian: {
    singleLane: true,
    frameMaxWidth: "100%",
    drawerWidth: "min(360px, calc(100vw - (var(--edge-chrome) * 2)))",
  },
  workspace: {
    defaultOpen: false,
    autoOpenOnDocumentRequest: false,
  },
} as const satisfies Omit<MobileShellProfile, "active" | "viewportClass">;

export function getMobileShellProfile(
  shellViewportProfile: Pick<ShellViewportProfile, "viewportClass">
): MobileShellProfile {
  const active = isPhoneShellViewportClass(shellViewportProfile.viewportClass);
  const baseProfile = active ? PHONE_SHELL_PROFILE : DESKTOP_SHELL_PROFILE;

  return {
    active,
    viewportClass: shellViewportProfile.viewportClass,
    ...baseProfile,
  };
}
