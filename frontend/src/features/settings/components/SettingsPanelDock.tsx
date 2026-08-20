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
          // Active selector uses the canonical accent-backed translucent fill
          // (matches SegmentedThemeControl). The color follows the resolved
          // --accent / --accent-strong tokens — no hardcoded brand color.
          "--pill-active-bg":
            "color-mix(in oklab, var(--accent-strong) 86%, transparent)",
          "--pill-active-text": "var(--text)",
          "--pill-active-border":
            "color-mix(in oklab, var(--accent-strong) 40%, transparent)",
          // Restrained layered accent glow — luminous but subordinate to
          // the tab label. All values are derived from --accent-strong /
          // --accent-weak; no raw color literals.
          "--pill-active-shadow":
            "0 0 0 1px color-mix(in oklab, var(--accent-strong) 38%, transparent), 0 8px 22px color-mix(in oklab, var(--accent-strong) 28%, transparent), 0 0 calc(var(--radius-micro) * 1.25) color-mix(in oklab, var(--accent-weak) 60%, transparent)",
          position: "sticky",
          top: SETTINGS_DENSITY.edgeChrome,
          paddingInline: SETTINGS_DENSITY.edgeChrome,
        } as CSSProperties
      }
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
