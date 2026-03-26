import { Bolt, Plus, X } from "lucide-react";
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

const SESSION_RAIL_STYLES: Record<"tabsEdgeMask", React.CSSProperties> = {
  tabsEdgeMask: {
    maskImage:
      "linear-gradient(to right, transparent 0px, black 14px, black calc(100% - 14px), transparent 100%)",
    WebkitMaskImage:
      "linear-gradient(to right, transparent 0px, black 14px, black calc(100% - 14px), transparent 100%)",
  },
};

function tabLabel(tab: SessionTab): string {
  if (tab.title && tab.title.trim()) return tab.title.trim();
  if (tab.threadId && tab.threadId.trim()) return `Thread ${tab.threadId.trim()}`;
  return "New Tab";
}

export function SessionRail({
  tabs,
  activeTabId,
  showTabs,
  isCloud = false,
  onActivateTab,
  onCloseTab,
  onOpenTab,
}: SessionRailProps) {
  const shouldShowTabs = showTabs ?? tabs.length > 1;
  const canCloseTabs = tabs.length > 1;
  return (
    <div className="session-rail shrink-0 flex flex-nowrap items-center gap-1.5 px-3 py-2">
      {shouldShowTabs ? (
        <div className="min-w-0 flex-1 overflow-hidden">
          <div
            className="session-rail__tabs-scroll min-w-0 overflow-x-auto whitespace-nowrap [scrollbar-width:thin]"
            style={tabs.length > 2 ? SESSION_RAIL_STYLES.tabsEdgeMask : undefined}
          >
            <div className="inline-flex min-w-full items-center gap-1.5">
              {tabs.map((tab) => {
                const isActive = tab.tabId === activeTabId;
                const basis = isActive
                  ? "var(--cfy-session-tab-active-basis)"
                  : "var(--cfy-session-tab-inactive-basis)";
                return (
                  <div
                    key={tab.tabId}
                    className="session-rail__tab-shell inline-flex items-center gap-1 pr-0.5"
                    data-state={isActive ? "active" : "inactive"}
                    style={{
                      flex: "0 0 auto",
                      flexBasis: basis,
                      maxWidth: "var(--cfy-session-tab-active-basis)",
                    }}
                  >
                    <button
                      type="button"
                      className="pill-tab session-rail__tab max-w-[220px]"
                      data-state={isActive ? "active" : "inactive"}
                      onClick={() => onActivateTab(tab.tabId)}
                      title={tabLabel(tab)}
                    >
                      <span className="truncate inline-flex items-center gap-1">
                        <span className="truncate">{tabLabel(tab)}</span>
                        {isActive && isCloud ? (
                          <span
                            className="inline-flex items-center justify-center rounded-full text-[10px] px-1.5 py-0.5"
                            aria-label="Cloud mode"
                            style={{
                              background: "color-mix(in oklab, var(--accent), transparent 40%)",
                              color: "var(--accent-strong)",
                            }}
                          >
                            <Bolt className="h-3 w-3" />
                          </span>
                        ) : null}
                      </span>
                    </button>
                    {canCloseTabs && (
                      <button
                        type="button"
                        className="session-rail__close inline-flex h-7 w-7 items-center justify-center rounded-full"
                        onClick={() => onCloseTab(tab.tabId)}
                        aria-label={`Close ${tabLabel(tab)}`}
                        title="Close tab"
                      >
                        <X className="h-3.5 w-3.5" />
                      </button>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}
      <div className="session-rail__tools shrink-0 flex items-center gap-2">
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
