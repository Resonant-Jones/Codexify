import type { ReactNode, RefObject } from "react";

import SettingsPanelDock, {
  type SettingsTab,
} from "@/features/settings/components/SettingsPanelDock";

type SettingsPanelShellProps = {
  activeTab: SettingsTab;
  children: ReactNode;
  className?: string;
  contentClassName?: string;
  desktopMode?: boolean;
  onTabChange: (tab: SettingsTab) => void;
  scrollContainerRef?: RefObject<HTMLDivElement>;
  testId?: string;
};

export default function SettingsPanelShell({
  activeTab,
  children,
  className,
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
      <div className="mx-auto flex w-full min-w-0 max-w-[84rem] flex-col gap-[var(--shell-gap)] px-[var(--shell-gap)] py-[var(--shell-gap)] sm:px-5 lg:px-6">
        <SettingsPanelDock
          activeTab={activeTab}
          desktopMode={desktopMode}
          onTabChange={onTabChange}
        />
        <div
          className={[
            "w-full min-w-0 space-y-[var(--shell-gap)]",
            contentClassName ?? "",
          ]
            .filter(Boolean)
            .join(" ")}
        >
          {children}
        </div>
      </div>
    </div>
  );
}
