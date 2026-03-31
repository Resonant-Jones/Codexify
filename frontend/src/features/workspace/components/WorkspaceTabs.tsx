import React from "react";

import type { WorkspaceDrawerTab } from "../state/useWorkspaceUiState";

type WorkspaceTabsProps = {
  activeTab: WorkspaceDrawerTab;
  onTabChange: (tab: WorkspaceDrawerTab) => void;
  onTabClose?: (tab: WorkspaceDrawerTab) => void;
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

const BASE_TAB_CLASSES =
  "relative inline-flex items-center gap-[0.35rem] px-3 py-2 border-none bg-transparent cursor-pointer select-none transition-colors duration-150 min-w-0";

const ACTIVE_TAB_STYLE = {
  color: "var(--text-on-accent)",
  background: "color-mix(in oklab, var(--accent-strong) 12%, transparent)",
};

const INACTIVE_TAB_STYLE = {
  color: "var(--text)",
};

const ACTIVE_TAB_DARK_STYLE = {
  background: "color-mix(in oklab, var(--accent-strong) 18%, transparent)",
};

export default function WorkspaceTabs({
  activeTab,
  onTabChange,
  onTabClose,
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

  const handleCloseClick = React.useCallback(
    (event: React.MouseEvent, tab: WorkspaceDrawerTab) => {
      event.stopPropagation();
      event.preventDefault();
      onTabClose?.(tab);
    },
    [onTabClose]
  );

  return (
    <div
      role="tablist"
      aria-label="Workspace panels"
      data-testid={`${idBase}-tabs`}
      className="flex w-full items-center"
      style={{
        background: "var(--panel-bg)",
        borderBottom: "1px solid var(--panel-border)",
      }}
    >
      {WORKSPACE_TABS.map((tab, index) => {
        const isActive = tab.id === activeTab;

        return (
          <React.Fragment key={tab.id}>
            {index > 0 && (
              <div
                className="h-4 w-px"
                style={{ background: "var(--panel-border)" }}
                data-testid={`${idBase}-tab-divider`}
              />
            )}
            <button
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
              className={BASE_TAB_CLASSES}
              style={isActive ? ACTIVE_TAB_STYLE : INACTIVE_TAB_STYLE}
              onClick={() => onTabChange(tab.id)}
              onKeyDown={(event) => handleKeyDown(event, index)}
            >
              <span className="min-w-0 flex-1 truncate text-[0.875rem] font-medium">
                {tab.label}
              </span>
              {isActive && onTabClose && (
                <span
                  role="button"
                  aria-label={`Close ${tab.label} tab`}
                  data-testid={`${idBase}-tab-${tab.id}-close`}
                  className="inline-flex items-center justify-center w-3.5 h-3.5 p-0 border-none rounded-full bg-transparent cursor-pointer opacity-60 hover:opacity-100 hover:bg-[color-mix(in_oklab,var(--panel-bg),85%,transparent)] transition-opacity duration-150 flex-shrink-0 focus:outline-1 focus:outline-[var(--accent-weak)] focus:outline-offset-1 active:scale-95"
                  style={{ color: "inherit" }}
                  onClick={(event) => handleCloseClick(event, tab.id)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter" || event.key === " ") {
                      event.preventDefault();
                      onTabClose(tab.id);
                    }
                  }}
                  tabIndex={0}
                >
                  <svg
                    width="6"
                    height="6"
                    viewBox="0 0 6 6"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    <path
                      d="M1 1L5 5M5 1L1 5"
                      stroke="currentColor"
                      strokeWidth="1.2"
                      strokeLinecap="round"
                    />
                  </svg>
                </span>
              )}
            </button>
          </React.Fragment>
        );
      })}
    </div>
  );
}
