import { useEffect, useMemo, useState } from "react";

import { useShellViewportClass } from "@/components/persona/layout/shellBreakpointContract";
import { useViewportInsets } from "@/hooks/useViewportInsets";
import type { MobileGestureState } from "@/components/persona/layout/mobileMotionContract";

function useMediaQuery(query: string): boolean {
  const [matches, setMatches] = useState(false);

  useEffect(() => {
    if (typeof window === "undefined" || typeof window.matchMedia !== "function") {
      return;
    }

    const mediaQueryList = window.matchMedia(query);
    const syncMatches = () => {
      setMatches(mediaQueryList.matches);
    };

    syncMatches();

    if (typeof mediaQueryList.addEventListener === "function") {
      mediaQueryList.addEventListener("change", syncMatches);
      return () => mediaQueryList.removeEventListener("change", syncMatches);
    }

    mediaQueryList.addListener(syncMatches);
    return () => mediaQueryList.removeListener(syncMatches);
  }, [query]);

  return matches;
}

export function useMobileGestureState(enabled = true): MobileGestureState {
  const shellViewportClass = useShellViewportClass();
  const isPhoneShell = enabled && shellViewportClass === "phone";
  const viewportInsets = useViewportInsets(isPhoneShell);
  const isCoarsePointer = useMediaQuery("(pointer: coarse)");
  const prefersReducedMotion = useMediaQuery("(prefers-reduced-motion: reduce)");

  return useMemo(
    () => ({
      isPhoneShell,
      isCoarsePointer,
      prefersReducedMotion,
      isKeyboardOpen: isPhoneShell ? viewportInsets.isKeyboardOpen : false,
      keyboardInset: isPhoneShell ? viewportInsets.keyboardInset : 0,
      allowMomentumScroll: isPhoneShell && (isCoarsePointer || enabled),
    }),
    [
      enabled,
      isCoarsePointer,
      isPhoneShell,
      prefersReducedMotion,
      viewportInsets.isKeyboardOpen,
      viewportInsets.keyboardInset,
    ]
  );
}
