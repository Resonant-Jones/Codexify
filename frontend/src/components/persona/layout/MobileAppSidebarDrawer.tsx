import * as React from "react";
import { createPortal } from "react-dom";
import { X } from "lucide-react";

import FrameCard from "@/components/surface/FrameCard";
import RefractiveGlassCard from "@/components/ui/RefractiveGlassCard";
import codexifyMarkSrc from "@/assets/brands/codexify/codexify-mark.png";
import { getMobileShellProfile } from "./mobileShellProfile";
import {
  getMobileNavigationControlStyle,
  type MobileApplicationDestination,
  type MobileApplicationView,
} from "./mobileNavigationContract";
import { useShellViewportProfile } from "./shellBreakpointContract";

type MobileAppSidebarDrawerProps = React.PropsWithChildren<{
  isOpen: boolean;
  onClose: () => void;
  isApplicationNavigationExpanded: boolean;
  onApplicationNavigationExpandedChange: (expanded: boolean) => void;
  activeApplicationView: MobileApplicationView;
  applicationDestinations: readonly MobileApplicationDestination[];
  onNavigateApplicationView: (view: MobileApplicationView) => void;
  returnFocusRef?: React.RefObject<HTMLElement | null>;
  wallpaperUrl?: string | null;
}>;

const FOCUSABLE_CONTROLS =
  'button:not([disabled]), [href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])';

export default function MobileAppSidebarDrawer({
  isOpen,
  onClose,
  isApplicationNavigationExpanded,
  onApplicationNavigationExpandedChange,
  activeApplicationView,
  applicationDestinations,
  onNavigateApplicationView,
  returnFocusRef,
  wallpaperUrl = null,
  children,
}: MobileAppSidebarDrawerProps) {
  const shellViewportProfile = useShellViewportProfile();
  const mobileShellProfile = React.useMemo(
    () => getMobileShellProfile(shellViewportProfile),
    [shellViewportProfile]
  );
  const drawerRef = React.useRef<HTMLElement | null>(null);
  const closeRef = React.useRef<HTMLButtonElement | null>(null);
  const applicationNavigationTriggerRef = React.useRef<HTMLButtonElement | null>(
    null
  );
  const portalTarget =
    typeof document === "undefined"
      ? null
      : document.getElementById("cfy-portal-root") ??
        document.getElementById("app") ??
        document.getElementById("root") ??
        document.body ??
        document.documentElement;

  React.useEffect(() => {
    if (!isOpen || typeof document === "undefined") return undefined;
    const previousOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    closeRef.current?.focus();
    return () => {
      document.body.style.overflow = previousOverflow;
      returnFocusRef?.current?.focus();
    };
  }, [isOpen, returnFocusRef]);

  React.useEffect(() => {
    if (!isOpen || typeof window === "undefined") return undefined;
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      if (isApplicationNavigationExpanded) {
        onApplicationNavigationExpandedChange(false);
        applicationNavigationTriggerRef.current?.focus();
        return;
      }
      onClose();
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [
    isApplicationNavigationExpanded,
    isOpen,
    onApplicationNavigationExpandedChange,
    onClose,
  ]);

  const containFocus = React.useCallback(
    (event: React.KeyboardEvent<HTMLElement>) => {
      if (event.key !== "Tab") return;
      const drawer = drawerRef.current;
      if (!drawer) return;
      const focusableControls = Array.from(
        drawer.querySelectorAll<HTMLElement>(FOCUSABLE_CONTROLS)
      ).filter(
        (control) =>
          !control.hasAttribute("hidden") &&
          control.getAttribute("aria-hidden") !== "true"
      ) as HTMLElement[];
      if (focusableControls.length === 0) {
        event.preventDefault();
        return;
      }
      const firstControl = focusableControls[0];
      const lastControl = focusableControls[focusableControls.length - 1];
      const activeControl = document.activeElement;
      if (
        event.shiftKey &&
        (activeControl === firstControl ||
          !(activeControl instanceof Node) ||
          !drawer.contains(activeControl))
      ) {
        event.preventDefault();
        lastControl.focus();
      } else if (!event.shiftKey && activeControl === lastControl) {
        event.preventDefault();
        firstControl.focus();
      }
    },
    []
  );

  const primaryDestinations = React.useMemo(
    () =>
      applicationDestinations.filter(
        (destination) => destination.priority === "primary"
      ),
    [applicationDestinations]
  );
  const secondaryDestinations = React.useMemo(
    () =>
      applicationDestinations.filter(
        (destination) => destination.priority === "secondary"
      ),
    [applicationDestinations]
  );
  const renderDestinations = React.useCallback(
    (destinations: readonly MobileApplicationDestination[]) =>
      destinations.map((destination) => {
        const isActive = activeApplicationView === destination.view;
        return (
          <button
            key={destination.view}
            type="button"
            className="pill-tab flex w-full items-center justify-start text-left"
            data-testid={`mobile-app-sidebar-destination-${destination.view}`}
            data-state={isActive ? "active" : "inactive"}
            aria-current={isActive ? "page" : undefined}
            onClick={() => {
              onNavigateApplicationView(destination.view);
              onClose();
            }}
            style={getMobileNavigationControlStyle(true)}
          >
            {destination.label}
          </button>
        );
      }),
    [activeApplicationView, onClose, onNavigateApplicationView]
  );

  if (!isOpen || !portalTarget) return null;

  return createPortal(
    <div
      data-testid="mobile-sidebar-overlay"
      style={{
        position: "fixed",
        inset: 0,
        zIndex: "var(--shell-overlay-z, 2000)",
      }}
    >
      <button
        type="button"
        data-testid="mobile-sidebar-scrim"
        className="absolute inset-0 border-0 p-0"
        style={{
          background:
            "color-mix(in oklab, var(--panel-bg) 68%, transparent)",
        }}
        aria-label="Dismiss application navigation and workspace sidebar"
        onClick={onClose}
      />
      <aside
        ref={drawerRef}
        data-testid="mobile-sidebar-drawer"
        className="absolute left-0 top-0 h-full overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-label="Application navigation and workspace"
        onKeyDown={containFocus}
        style={{
          width: mobileShellProfile.guardian.drawerWidth,
          zIndex: "calc(var(--shell-overlay-z, 2000) + 1)",
        }}
        onPointerDown={(event) => event.stopPropagation()}
        onClick={(event) => event.stopPropagation()}
      >
        <div className="relative h-full w-full min-h-0 min-w-0 box-border">
          <div className="absolute inset-0 -z-10 overflow-hidden rounded-[var(--card-radius)] pointer-events-none">
            <RefractiveGlassCard
              wallpaperUrl={wallpaperUrl}
              className="h-full w-full rounded-[var(--card-radius)]"
              style={{ background: "transparent", border: "none" }}
              intensity={0.006}
              aberration={0}
            />
          </div>
          <FrameCard
            fill
            refractiveFallback
            shimmerMode="subtle"
            liquidBezelWidth={3}
            className="flex h-full w-full min-h-0 min-w-0 flex-col box-border"
            style={{
              borderRadius: "var(--card-radius)",
              borderWidth: 1,
              borderStyle: "solid",
              borderColor: "var(--panel-border)",
              background: "var(--panel-bg)",
            }}
          >
            <div className="flex h-full min-h-0 flex-col">
              <header
                className="flex shrink-0 items-center justify-between gap-[var(--card-pad)] p-[var(--card-pad)]"
                style={{
                  borderBlockEnd: "var(--frame) solid var(--panel-border)",
                }}
              >
                <button
                  ref={applicationNavigationTriggerRef}
                  type="button"
                  className="icon-inline flex shrink-0 items-center justify-center rounded-[var(--radius-micro)] bg-[var(--accent)] p-[calc(var(--radius-micro)/2)]"
                  aria-label={
                    isApplicationNavigationExpanded
                      ? "Collapse application navigation"
                      : "Expand application navigation"
                  }
                  aria-expanded={isApplicationNavigationExpanded}
                  aria-controls="mobile-app-sidebar-application-navigation"
                  onClick={() =>
                    onApplicationNavigationExpandedChange(
                      !isApplicationNavigationExpanded
                    )
                  }
                >
                  <img
                    src={codexifyMarkSrc}
                    alt=""
                    aria-hidden="true"
                    data-testid="mobile-app-sidebar-codexify-mark"
                    className="block h-[calc(var(--radius-micro)*2)] w-[calc(var(--radius-micro)*2)] shrink-0 object-contain"
                  />
                </button>
                <button
                  ref={closeRef}
                  type="button"
                  className="icon-inline shrink-0"
                  aria-label="Close application navigation and workspace sidebar"
                  onClick={onClose}
                  style={getMobileNavigationControlStyle(true, { square: true })}
                >
                  <X
                    aria-hidden="true"
                    className="h-[calc(var(--radius-micro)*2)] w-[calc(var(--radius-micro)*2)]"
                  />
                </button>
              </header>
              {isApplicationNavigationExpanded &&
                applicationDestinations.length > 0 && (
                  <nav
                    id="mobile-app-sidebar-application-navigation"
                    aria-label="Application destinations"
                    data-testid="mobile-app-sidebar-application-navigation"
                    className="shrink-0 p-[var(--card-pad)]"
                  >
                    <div className="flex flex-col gap-[var(--pill-gap)]">
                      {renderDestinations(primaryDestinations)}
                    </div>
                    {secondaryDestinations.length > 0 && (
                      <div
                        className="mt-[var(--card-pad)] flex flex-col gap-[var(--pill-gap)] pt-[var(--card-pad)]"
                        style={{
                          borderBlockStart:
                            "var(--frame) solid var(--panel-border)",
                        }}
                      >
                        {renderDestinations(secondaryDestinations)}
                      </div>
                    )}
                  </nav>
                )}
              <div className="min-h-0 flex-1" data-testid="mobile-sidebar-workspace">
                {children}
              </div>
            </div>
          </FrameCard>
        </div>
      </aside>
    </div>,
    portalTarget
  );
}
