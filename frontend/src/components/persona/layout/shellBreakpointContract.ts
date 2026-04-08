import { useEffect, useMemo, useState } from "react";

export const SHELL_BREAKPOINTS = {
  phone: 767,
  smallTablet: 1023,
  desktop: 1024,
} as const;

export type ShellViewportClass = "phone" | "small_tablet" | "desktop";

export type ShellViewportProfile = {
  viewportClass: ShellViewportClass;
  shellMinWidth: string;
  shellMinHeight: string;
  contentMinHeight: string;
  shellEdgeChrome: string;
  shellGap: string;
  shellCardPad: string;
  shellPageGutterTop: string;
  viewportRadius: string;
  documentsGridColumns: 1 | 2 | 4;
  workspaceArrangement: "stack" | "split";
  sidebarArrangement: "collapse" | "split";
};

const SHELL_VIEWPORT_PROFILES: Record<ShellViewportClass, ShellViewportProfile> = {
  phone: {
    viewportClass: "phone",
    shellMinWidth: "0px",
    shellMinHeight: "0px",
    contentMinHeight: "0px",
    shellEdgeChrome: "4px",
    shellGap: "12px",
    shellCardPad: "10px",
    shellPageGutterTop: "12px",
    viewportRadius: "20px",
    documentsGridColumns: 1,
    workspaceArrangement: "stack",
    sidebarArrangement: "collapse",
  },
  small_tablet: {
    viewportClass: "small_tablet",
    shellMinWidth: "0px",
    shellMinHeight: "0px",
    contentMinHeight: "0px",
    shellEdgeChrome: "6px",
    shellGap: "14px",
    shellCardPad: "12px",
    shellPageGutterTop: "16px",
    viewportRadius: "20px",
    documentsGridColumns: 2,
    workspaceArrangement: "split",
    sidebarArrangement: "collapse",
  },
  desktop: {
    viewportClass: "desktop",
    shellMinWidth: "608px",
    shellMinHeight: "548px",
    contentMinHeight: "clamp(520px, 70vh, 1000px)",
    shellEdgeChrome: "6px",
    shellGap: "16px",
    shellCardPad: "12px",
    shellPageGutterTop: "24px",
    viewportRadius: "20px",
    documentsGridColumns: 4,
    workspaceArrangement: "split",
    sidebarArrangement: "split",
  },
};

function getViewportWidth(): number {
  if (typeof window === "undefined") {
    return SHELL_BREAKPOINTS.desktop;
  }

  return window.innerWidth;
}

export function isPhoneShellWidth(width: number): boolean {
  return width <= SHELL_BREAKPOINTS.phone;
}

export function isSmallTabletShellWidth(width: number): boolean {
  return width > SHELL_BREAKPOINTS.phone && width <= SHELL_BREAKPOINTS.smallTablet;
}

export function isDesktopShellWidth(width: number): boolean {
  return width >= SHELL_BREAKPOINTS.desktop;
}

export function getShellViewportClass(width: number = getViewportWidth()): ShellViewportClass {
  if (isPhoneShellWidth(width)) {
    return "phone";
  }

  if (isSmallTabletShellWidth(width)) {
    return "small_tablet";
  }

  return "desktop";
}

export function getShellViewportProfile(
  viewportClassOrWidth: ShellViewportClass | number = getViewportWidth()
): ShellViewportProfile {
  const viewportClass =
    typeof viewportClassOrWidth === "number"
      ? getShellViewportClass(viewportClassOrWidth)
      : viewportClassOrWidth;
  return SHELL_VIEWPORT_PROFILES[viewportClass];
}

export function useShellViewportClass(): ShellViewportClass {
  const [viewportClass, setViewportClass] = useState<ShellViewportClass>(() =>
    getShellViewportClass()
  );

  useEffect(() => {
    if (typeof window === "undefined") return;

    const syncViewportClass = () => {
      setViewportClass(getShellViewportClass());
    };

    syncViewportClass();
    window.addEventListener("resize", syncViewportClass);
    return () => window.removeEventListener("resize", syncViewportClass);
  }, []);

  return viewportClass;
}

export function useShellViewportProfile(): ShellViewportProfile {
  const viewportClass = useShellViewportClass();
  return useMemo(() => SHELL_VIEWPORT_PROFILES[viewportClass], [viewportClass]);
}
