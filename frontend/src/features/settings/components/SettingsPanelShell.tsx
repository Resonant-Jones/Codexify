import type { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";

type SettingsPanelShellProps = PropsWithChildren<{
  className?: string;
  "data-testid"?: string;
}>;

export default function SettingsPanelShell({
  children,
  className,
  "data-testid": dataTestId = "settings-panel-shell",
}: SettingsPanelShellProps) {
  return (
    <section
      data-testid={dataTestId}
      className={cn("flex min-h-0 w-full flex-col gap-[var(--shell-gap)]", className)}
      style={{
        borderRadius: "calc(var(--card-radius) + var(--board-edge) / 2)",
        border: "1px solid color-mix(in srgb, var(--panel-bezel) 86%, transparent)",
        background: "color-mix(in srgb, var(--panel-bg) 80%, transparent)",
        padding: "calc(var(--card-pad) + var(--board-edge))",
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.05), inset 0 -1px 0 rgba(0,0,0,0.16)",
      }}
    >
      {children}
    </section>
  );
}
