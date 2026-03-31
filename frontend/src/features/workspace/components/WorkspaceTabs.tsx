import React from "react";

import type { WorkspaceDrawerTab } from "../state/useWorkspaceUiState";

type WorkspaceTabsProps = {
  activeTab: WorkspaceDrawerTab;
  onTabChange: (tab: WorkspaceDrawerTab) => void;
  idBase?: string;
};

const WORKSPACE_TABS: Array<{
  id: WorkspaceDrawerTab;
  label: string;
}> = [
  { id: "shelf", label: "Shelf" },
  { id: "scratchpad", label: "Scratchpad" },
  { id: "inspector", label: "Inspector" },
];

export default function WorkspaceTabs({
  activeTab,
  onTabChange,
  idBase = "workspace",
}: WorkspaceTabsProps) {
  const buttonRefs = React.useRef<
    Partial<Record<WorkspaceDrawerTab, HTMLButtonElement | null>>
  >({});

  const focusTab = React.useCallback(
    (tab: WorkspaceDrawerTab) => {
      onTabChange(tab);
      buttonRefs.current[tab]?.focus();
    },
    [onTabChange]
  );

  const handleKeyDown = React.useCallback(
    (event: React.KeyboardEvent<HTMLButtonElement>, index: number) => {
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
        focusTab(WORKSPACE_TABS[0].id);
        return;
      }

      if (event.key === "End") {
        focusTab(WORKSPACE_TABS[WORKSPACE_TABS.length - 1].id);
        return;
      }

      const delta = event.key === "ArrowRight" ? 1 : -1;
      const nextIndex =
        (index + delta + WORKSPACE_TABS.length) % WORKSPACE_TABS.length;
      focusTab(WORKSPACE_TABS[nextIndex].id);
    },
    [focusTab]
  );

  return (
    <div
      role="tablist"
      aria-label="Workspace panels"
      data-testid={`${idBase}-tabs`}
      className="flex items-center gap-2 rounded-[var(--radius-micro)] border p-2"
      style={{
        borderColor: "var(--panel-border)",
        background:
          "color-mix(in oklab, var(--chip-bg) 78%, transparent)",
      }}
    >
      {WORKSPACE_TABS.map((tab, index) => {
        const isActive = tab.id === activeTab;

        return (
          <button
            key={tab.id}
            ref={(node) => {
              buttonRefs.current[tab.id] = node;
            }}
            id={`${idBase}-tab-${tab.id}`}
            type="button"
            role="tab"
            aria-selected={isActive}
            aria-controls={`${idBase}-panel-${tab.id}`}
            tabIndex={isActive ? 0 : -1}
            data-state={isActive ? "active" : "inactive"}
            data-testid={`${idBase}-tab-${tab.id}`}
            className="min-w-0 flex-1 rounded-[var(--radius-micro)] px-4 py-3 text-[0.95rem] transition-colors"
            style={{
              border: isActive
                ? "1px solid var(--chip-border)"
                : "1px solid color-mix(in oklab, var(--chip-border) 32%, transparent)",
              background: isActive
                ? "var(--accent)"
                : "color-mix(in oklab, var(--panel-bg) 70%, transparent)",
              color: isActive ? "var(--text-on-accent)" : "var(--text)",
              fontWeight: isActive ? 600 : 500,
              boxShadow: isActive
                ? "inset 0 1px 0 rgba(255,255,255,0.14), 0 2px 6px rgba(0,0,0,0.14)"
                : undefined,
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
