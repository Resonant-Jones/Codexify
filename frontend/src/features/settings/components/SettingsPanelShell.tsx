import type { ReactNode } from "react";

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
  testId?: string;
};

export default function SettingsPanelShell({
  activeTab,
  children,
  className,
  contentClassName,
  desktopMode = false,
  onTabChange,
  testId = "settings-panel-shell",
}: SettingsPanelShellProps) {
  return (
    <div
      data-testid={testId}
      className={[
        "w-full min-w-0 overflow-x-clip text-[var(--text)]",
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
