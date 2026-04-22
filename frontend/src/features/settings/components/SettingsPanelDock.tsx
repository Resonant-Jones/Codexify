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
        className="glass-pill isolate relative inline-flex w-fit max-w-full min-w-0 flex-wrap items-center justify-center overflow-x-auto"
        style={
          {
            "--pill-active-text": "var(--text-on-accent)",
            "--pill-gap": "calc(var(--radius-micro) / 2)",
            "--pill-font": "0.8rem",
          } as CSSProperties
        }
      >
        {children}
      </div>
    </nav>
  );
}
