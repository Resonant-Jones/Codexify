import type { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

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
      className={cn("sticky z-20 w-full shrink-0", className)}
      style={{
        position: "sticky",
        top: "calc(var(--card-pad) + var(--board-edge))",
      }}
      data-testid="settings-panel-dock"
      className="glass-pill sticky top-0 z-30 inline-flex w-fit max-w-full min-w-0 shrink-0 items-stretch overflow-x-auto"
      style={
        {
          "--pill-active-text": "var(--text-on-accent)",
          "--pill-gap": "var(--radius-micro)",
          "--pill-font": "0.84rem",
        } as React.CSSProperties
      }
    >
      <div
        className="flex w-full flex-wrap gap-2 rounded-[var(--tile-radius)] border p-2"
        style={{
          borderColor: "color-mix(in srgb, var(--panel-bezel) 88%, transparent)",
          background: "color-mix(in srgb, var(--panel-bg) 86%, transparent)",
          boxShadow:
            "inset 0 1px 0 rgba(255,255,255,0.05), 0 10px 24px rgba(0,0,0,0.10)",
          backdropFilter: "saturate(140%) blur(10px)",
          WebkitBackdropFilter: "saturate(140%) blur(10px)",
        }}
      >
        {children}
      </div>
    </nav>
  );
}
