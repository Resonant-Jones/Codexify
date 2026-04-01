import { Plus, X } from "lucide-react";
import React from "react";

import type { SessionTab, TabId } from "@/state/session/types";

type SessionRailProps = {
  tabs: SessionTab[];
  activeTabId: TabId | null;
  showTabs?: boolean;
  isCloud?: boolean;
  onActivateTab: (tabId: TabId) => void;
  onCloseTab: (tabId: TabId) => void;
  onOpenTab: () => void;
};

function tabLabel(tab: SessionTab): string {
  if (tab.title && tab.title.trim()) return tab.title.trim();
  if (tab.threadId && tab.threadId.trim()) return `Thread ${tab.threadId.trim()}`;
  return "New Tab";
}

const RAIL_WRAPPER_CLASSES =
  "shrink-0 flex flex-nowrap items-center gap-2 px-3 py-2";

const SEGMENT_BASE_CLASSES =
  "relative inline-flex items-center gap-[0.35rem] px-3 py-2 border-none bg-transparent cursor-pointer select-none transition-colors duration-150 min-w-0";

export function SessionRail({
  tabs,
  activeTabId,
  showTabs,
  onActivateTab,
  onCloseTab,
  onOpenTab,
}: SessionRailProps) {
  const shouldShowTabs = showTabs ?? tabs.length > 1;

  return (
    <div className={RAIL_WRAPPER_CLASSES}>
      {shouldShowTabs ? (
        <div
          className="flex-1 min-w-0 flex items-center"
          data-testid="session-rail-track"
        >
          <div className="flex min-w-0 items-center overflow-x-auto [scrollbar-width:thin]">
            <div className="inline-flex min-w-full items-center gap-1 px-1.5 py-1">
              {tabs.map((tab, index) => {
                const isActive = tab.tabId === activeTabId;

                return (
                  <React.Fragment key={tab.tabId}>
                    {index > 0 && (
                      <div
                        className="h-4 w-px shrink-0"
                        style={{
                          background:
                            "color-mix(in oklab, var(--panel-border) 76%, transparent)",
                        }}
                        data-testid="session-rail-divider"
                      />
                    )}
                    <div
                      className={SEGMENT_BASE_CLASSES}
                      data-state={isActive ? "active" : "inactive"}
                      data-testid={`session-rail-tab-${tab.tabId}`}
                      style={
                        isActive
                          ? {
                              color: "var(--text-on-accent)",
                              background:
                                "color-mix(in oklab, var(--accent-strong) 12%, transparent)",
                            }
                          : {
                              color: "var(--text)",
                            }
                      }
                    >
                      <button
                        type="button"
                        className="min-w-0 flex-1 truncate px-0 py-1 text-sm font-medium"
                        data-state={isActive ? "active" : "inactive"}
                        onClick={() => onActivateTab(tab.tabId)}
                        title={tabLabel(tab)}
                        style={{
                          background: "transparent",
                          color: "inherit",
                        }}
                      >
                        {tabLabel(tab)}
                      </button>
                      {isActive && (
                        <button
                          type="button"
                          className="inline-flex items-center justify-center w-3.5 h-3.5 p-0 border-none rounded-full bg-transparent cursor-pointer opacity-60 hover:opacity-100 hover:bg-[color-mix(in_oklab,var(--panel-bg),85%,transparent)] transition-opacity duration-150 flex-shrink-0 focus:outline-1 focus:outline-[var(--accent-weak)] focus:outline-offset-1 active:scale-95"
                          onClick={(e) => {
                            e.stopPropagation();
                            e.preventDefault();
                            onCloseTab(tab.tabId);
                          }}
                          aria-label={`Close ${tabLabel(tab)}`}
                          title="Close tab"
                          style={{
                            color: "inherit",
                          }}
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
                        </button>
                      )}
                    </div>
                  </React.Fragment>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}
      <div className="shrink-0 flex items-center gap-2">
        <button
          type="button"
          className="icon-inline session-rail__tool-btn p-2 rounded-md hover:bg-white/10 transition"
          aria-label="New tab"
          title="New tab"
          onClick={onOpenTab}
        >
          <Plus className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

export default SessionRail;
