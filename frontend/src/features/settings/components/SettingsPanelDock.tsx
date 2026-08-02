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
          "--settings-nav-surface":
            "color-mix(in srgb, var(--panel-bg) 86%, var(--text) 14%)",
          "--pill-active-bg": "transparent",
          "--pill-active-text": "var(--text)",
          "--pill-active-border": "var(--accent)",
          "--pill-active-shadow":
            "0 0 calc(var(--radius-micro) * 0.75) color-mix(in srgb, var(--accent-weak) 72%, transparent)",
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
        className="glass-pill isolate relative flex w-full min-w-0 items-stretch overflow-x-auto p-[var(--settings-dock-padding)]"
        style={
          {
            background: "var(--settings-nav-surface)",
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
