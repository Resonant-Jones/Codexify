import React, { useMemo, useRef } from "react";

export type SettingsTab =
  | "appearance"
  | "system"
  | "connectors"
  | "data"
  | "connection"
  | "personalFacts";

type SettingsPanelDockProps = {
  activeTab: SettingsTab;
  desktopMode?: boolean;
  onTabChange: (tab: SettingsTab) => void;
};

const SETTINGS_TABS: Array<{
  desktopOnly?: boolean;
  id: SettingsTab;
  label: string;
}> = [
  { id: "appearance", label: "Appearance" },
  { id: "system", label: "Imprint" },
  { id: "connectors", label: "Connectors" },
  { id: "data", label: "Data" },
  { desktopOnly: true, id: "connection", label: "Connection" },
  { id: "personalFacts", label: "Personal Facts" },
];

export default function SettingsPanelDock({
  activeTab,
  desktopMode = false,
  onTabChange,
}: SettingsPanelDockProps) {
  const buttonRefs = useRef<Partial<Record<SettingsTab, HTMLButtonElement | null>>>({});

  const visibleTabs = useMemo(
    () => SETTINGS_TABS.filter((tab) => !tab.desktopOnly || desktopMode),
    [desktopMode]
  );

  const desktopGridColumns = `repeat(${visibleTabs.length}, minmax(0, 1fr))`;

  const focusTab = (tab: SettingsTab) => {
    onTabChange(tab);
    buttonRefs.current[tab]?.focus();
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLButtonElement>,
    index: number
  ) => {
    if (
      event.key !== "ArrowRight" &&
      event.key !== "ArrowLeft" &&
      event.key !== "Home" &&
      event.key !== "End"
    ) {
      return;
    }

    event.preventDefault();

    if (event.key === "Home") {
      focusTab(visibleTabs[0].id);
      return;
    }

    if (event.key === "End") {
      focusTab(visibleTabs[visibleTabs.length - 1].id);
      return;
    }

    const delta = event.key === "ArrowRight" ? 1 : -1;
    const nextIndex = (index + delta + visibleTabs.length) % visibleTabs.length;
    focusTab(visibleTabs[nextIndex].id);
  };

  return (
    <div
      role="tablist"
      aria-label="Settings tabs"
      data-testid="settings-panel-dock"
      className="glass-pill sticky top-0 z-30 flex w-full max-w-full min-w-0 items-stretch overflow-x-auto lg:grid lg:overflow-visible"
      style={
        {
          "--pill-active-text": "var(--text-on-accent)",
          "--pill-gap": "var(--radius-micro)",
          "--pill-font": "0.84rem",
          gridTemplateColumns: desktopGridColumns,
        } as React.CSSProperties
      }
    >
      {visibleTabs.map((tab, index) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            ref={(node) => {
              buttonRefs.current[tab.id] = node;
            }}
            id={`settings-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`settings-panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            data-state={isActive ? "active" : "inactive"}
            data-testid={`settings-panel-dock-tab-${tab.id}`}
            className={[
              "pill-tab shrink-0 whitespace-nowrap text-xs transition-opacity lg:w-full lg:justify-center lg:text-center",
              isActive
                ? "opacity-100"
                : "opacity-25 hover:opacity-100 focus-visible:opacity-100",
            ].join(" ")}
            style={{
              color: isActive ? "var(--text-on-accent)" : "var(--text)",
            }}
            onClick={() => onTabChange(tab.id)}
            onKeyDown={(event) => handleKeyDown(event, index)}
          >
            {tab.label}
          </button>
        );
      })}
    </div>
  );
}
