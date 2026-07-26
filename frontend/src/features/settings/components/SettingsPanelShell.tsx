import type { PropsWithChildren } from "react";

import { cn } from "@/lib/utils";
import { SETTINGS_DENSITY } from "../settingsDensityContract";

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
      className={cn(
        "flex h-full min-h-0 w-full min-w-0 flex-col overflow-hidden text-[var(--text)]",
        className
      )}
      style={{
        border: "none",
        background: "transparent",
        padding: SETTINGS_DENSITY.edgeChrome,
        boxShadow: "none",
      }}
    >
      {children}
    </section>
  );
}
