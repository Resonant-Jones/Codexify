import type { PropsWithChildren, RefObject } from "react";
import type { ReactNode, RefObject } from "react";

import { cn } from "@/lib/utils";

type SettingsPanelShellProps = PropsWithChildren<{
  className?: string;
  "data-testid"?: string;
  scrollContainerRef?: RefObject<HTMLElement | null>;
}>;
  contentClassName?: string;
  desktopMode?: boolean;
  onTabChange: (tab: SettingsTab) => void;
  scrollContainerRef?: RefObject<HTMLDivElement>;
  testId?: string;
};

export default function SettingsPanelShell({
  children,
  className,
  "data-testid": dataTestId = "settings-panel-shell",
  scrollContainerRef,
}: SettingsPanelShellProps) {
  return (
    <section
      data-testid={dataTestId}
      ref={scrollContainerRef}
      className={cn(
        "flex h-full min-h-0 w-full min-w-0 flex-col gap-[var(--shell-gap)] overflow-x-clip overflow-y-auto text-[var(--text)]",
        className
      )}
      style={{
        borderRadius: "calc(var(--card-radius) + var(--board-edge) / 2)",
        border: "1px solid color-mix(in srgb, var(--panel-bezel) 86%, transparent)",
        background: "color-mix(in srgb, var(--panel-bg) 80%, transparent)",
        padding: "calc(var(--card-pad) + var(--board-edge))",
        boxShadow:
          "inset 0 1px 0 rgba(255,255,255,0.05), inset 0 -1px 0 rgba(0,0,0,0.16)",
      }}
  contentClassName,
  desktopMode = false,
  onTabChange,
  scrollContainerRef,
  testId = "settings-panel-shell",
}: SettingsPanelShellProps) {
  return (
    <div
      data-testid={testId}
      ref={scrollContainerRef}
      className={[
        "flex h-full min-h-0 w-full min-w-0 flex-col overflow-x-clip overflow-y-auto text-[var(--text)]",
        className ?? "",
      ]
        .filter(Boolean)
        .join(" ")}
    >
      {children}
    </section>
  );
}
