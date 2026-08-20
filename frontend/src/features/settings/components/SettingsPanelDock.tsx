import type { CSSProperties, PropsWithChildren } from "react";

import { cn } from "@/lib/utils";
import { SETTINGS_DENSITY } from "../settingsDensityContract";

type SettingsPanelDockProps = PropsWithChildren<{
  className?: string;
  "data-testid"?: string;
}>;

export default function SettingsPanelDock({
  children,
  className,
  "data-testid": dataTestId = "settings-panel-dock",
}: SettingsPanelDockProps) {
  // The active tab inherits the canonical .pill-tab[data-state="active"]
  // styling through the shared pill primitives — same as the Theme selector.
  // No dock-local --pill-active-* overrides are set here, so the selected
  // tab reads as the same filled glowing accent pill family as the rest of
  // Codexify. The bounded Settings material hook (settings-panel-dock__glass)
  // lives in index.css and handles the dark/light glass shell + perimeter
  // fringe without redefining the active selector.
  return (
    <nav
      data-testid={dataTestId}
      role="tablist"
      aria-label="Settings tabs"
      aria-orientation="horizontal"
      className={cn(
        "sticky z-30 flex w-full shrink-0 items-center justify-center",
        className
      )}
      style={
        {
          position: "sticky",
          top: SETTINGS_DENSITY.edgeChrome,
          paddingInline: SETTINGS_DENSITY.edgeChrome,
        } as CSSProperties
      }
      style={{
        position: "sticky",
        top: SETTINGS_DENSITY.edgeChrome,
        paddingInline: SETTINGS_DENSITY.edgeChrome,
      }}
    >
      <div
        className="settings-panel-dock__glass glass-pill isolate relative flex w-full min-w-0 items-stretch overflow-x-auto p-[var(--settings-dock-padding)]"
        style={
          {
            "--pill-gap": SETTINGS_DENSITY.dockGap,
            "--pill-font": SETTINGS_DENSITY.dockFontSize,
            "--settings-dock-gap": SETTINGS_DENSITY.dockGap,
            "--settings-dock-padding": SETTINGS_DENSITY.dockPadding,
          } as CSSProperties
        }
      >
        <div className="flex w-max min-w-full items-stretch justify-evenly gap-[var(--settings-dock-gap)] whitespace-nowrap">
          {children}
        </div>
      </div>
    </nav>
  );
}
