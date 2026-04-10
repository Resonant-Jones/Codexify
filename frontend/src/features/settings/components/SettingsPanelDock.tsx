import type { CSSProperties, PropsWithChildren } from "react";

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
      className={cn(
        "sticky top-[calc(var(--card-pad) + var(--board-edge))] z-30 flex w-full shrink-0 items-center justify-center",
        className
      )}
      style={{
        position: "sticky",
        top: "calc(var(--card-pad) + var(--board-edge))",
      }}
    >
      <div
        className="glass-pill flex w-full max-w-full min-w-0 flex-wrap items-center justify-center"
        style={
          {
            "--pill-active-text": "var(--text-on-accent)",
            "--pill-gap": "var(--radius-micro)",
            "--pill-font": "0.84rem",
          } as CSSProperties
        }
      >
        {children}
      </div>
    </nav>
  );
}
