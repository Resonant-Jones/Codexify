import { useMemo } from "react";

import type { ShellViewportClass, ShellViewportProfile } from "./shellBreakpointContract";
import {
  isPhoneShellViewportClass,
  useShellViewportProfile,
} from "./shellBreakpointContract";

export type MobileShellProfile = {
  active: boolean;
  shellMode: "default" | "mobile";
  viewportClass: ShellViewportClass;
  topNav: {
    scrollable: boolean;
    width: string;
    railEdgePadding: string;
    railGap: string;
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
  chat: {
    composer: {
      padX: string;
      padY: string;
      textPadX: string;
      textPadY: string;
      controlGap: string;
      controlSize: string;
      bottomSafeArea: string;
    };
  };
};

const DESKTOP_SHELL_PROFILE = {
  shellMode: "default",
  topNav: {
    scrollable: false,
    width: "auto",
    railEdgePadding: "0px",
    railGap: "var(--pill-gap)",
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
  chat: {
    composer: {
      padX: "12px",
      padY: "12px",
      textPadX: "14px",
      textPadY: "10px",
      controlGap: "12px",
      controlSize: "32px",
      bottomSafeArea: "0px",
    },
  },
} as const satisfies Omit<MobileShellProfile, "active" | "viewportClass">;

const PHONE_SHELL_PROFILE = {
  shellMode: "mobile",
  topNav: {
    scrollable: true,
    width: "100%",
    railEdgePadding: "10px",
    railGap: "var(--pill-gap)",
  },
  guardian: {
    singleLane: true,
    frameMaxWidth: "100%",
    drawerWidth: "min(360px, calc(100vw - (var(--edge-chrome) * 2)))",
  },
  workspace: {
    defaultOpen: false,
    autoOpenOnDocumentRequest: true,
  },
  chat: {
    composer: {
      padX: "10px",
      padY: "10px",
      textPadX: "12px",
      textPadY: "8px",
      controlGap: "8px",
      controlSize: "40px",
      bottomSafeArea: "env(safe-area-inset-bottom, 0px)",
    },
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

export function useMobileShellProfile(): MobileShellProfile {
  const shellViewportProfile = useShellViewportProfile();
  return useMemo(
    () => getMobileShellProfile(shellViewportProfile),
    [shellViewportProfile]
  );
}
