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
      style={{
        position: "sticky",
        top: SETTINGS_DENSITY.edgeChrome,
        paddingInline: SETTINGS_DENSITY.edgeChrome,
      }}
    >
      <div
        className="glass-pill isolate relative flex w-full min-w-0 items-stretch gap-[var(--settings-dock-gap)] overflow-x-auto p-[var(--settings-dock-padding)]"
        style={
          {
            "--pill-active-text": "var(--text-on-accent)",
            "--pill-gap": SETTINGS_DENSITY.dockGap,
            "--pill-font": SETTINGS_DENSITY.dockFontSize,
            "--settings-dock-gap": SETTINGS_DENSITY.dockGap,
            "--settings-dock-padding": SETTINGS_DENSITY.dockPadding,
          } as CSSProperties
        }
      >
        {children}
      </div>
    </nav>
  );
}
