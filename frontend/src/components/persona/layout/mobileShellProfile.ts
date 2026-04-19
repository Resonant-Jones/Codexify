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
  surfaceActions: {
    clusterPaddingX: string;
    clusterPaddingY: string;
  };
  documents: {
    layout: "grid" | "list";
    itemWidth: string;
    contentGap: string;
    contentPadding: string;
  };
  dashboard: {
    layout: "split" | "stack";
    sectionGap: string;
    threadColumns: 1 | 2;
    documentColumns: 1 | 4;
    contentPadding: string;
  };
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
      shellMaxHeight: string;
      bottomSafeArea: string;
    };
  };
  bottomEdge: {
    suppressOnKeyboard: boolean;
  };
};

const DESKTOP_SHELL_PROFILE = {
  shellMode: "default",
  surfaceActions: {
    clusterPaddingX: "calc(var(--card-pad) / 2)",
    clusterPaddingY: "calc(var(--card-pad) / 4)",
  },
  documents: {
    layout: "grid",
    itemWidth: "127px",
    contentGap: "var(--shell-gap)",
    contentPadding: "var(--card-pad)",
  },
  dashboard: {
    layout: "split",
    sectionGap: "var(--shell-gap)",
    threadColumns: 2,
    documentColumns: 4,
    contentPadding: "var(--card-pad)",
  },
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
      shellMaxHeight: "60vh",
      bottomSafeArea: "0px",
    },
  },
  bottomEdge: {
    suppressOnKeyboard: false,
  },
} as const satisfies Omit<MobileShellProfile, "active" | "viewportClass">;

const PHONE_SHELL_PROFILE = {
  shellMode: "mobile",
  surfaceActions: {
    clusterPaddingX: "calc(var(--card-pad) / 2)",
    clusterPaddingY: "calc(var(--card-pad) / 4)",
  },
  documents: {
    layout: "list",
    itemWidth: "100%",
    contentGap: "var(--shell-gap)",
    contentPadding: "var(--card-pad)",
  },
  dashboard: {
    layout: "stack",
    sectionGap: "var(--shell-gap)",
    threadColumns: 1,
    documentColumns: 1,
    contentPadding: "var(--card-pad)",
  },
  topNav: {
    scrollable: true,
    width: "100%",
    railEdgePadding: "12px",
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
      controlGap: "10px",
      controlSize: "44px",
      shellMaxHeight: "calc(var(--shell-viewport-height, 100vh) * 0.6)",
      bottomSafeArea: "env(safe-area-inset-bottom, 0px)",
    },
  },
  bottomEdge: {
    suppressOnKeyboard: true,
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
