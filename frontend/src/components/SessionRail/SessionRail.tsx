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
  onActivateTab,
  onCloseTab,
  onOpenTab,
}: SessionRailProps) {
  const shouldShowTabs = showTabs ?? tabs.length > 1;
  const canCloseTabs = tabs.length > 1;
  return (
    <div className="session-rail shrink-0 flex flex-nowrap items-center gap-2 px-3 py-2">
      {shouldShowTabs ? (
        <div
          className="session-rail__track min-w-0 flex-1 overflow-hidden rounded-[999px] border"
          data-testid="session-rail-track"
          style={{
            borderColor: "var(--panel-border)",
            background:
              "color-mix(in oklab, var(--chip-bg) 80%, transparent)",
          }}
        >
          <div className="flex min-w-0 items-center">
            <div className="min-w-0 flex-1 overflow-hidden">
              <div
                className="session-rail__tabs-scroll min-w-0 overflow-x-auto whitespace-nowrap [scrollbar-width:thin]"
                style={tabs.length > 2 ? SESSION_RAIL_STYLES.tabsEdgeMask : undefined}
              >
                <div className="inline-flex min-w-full items-center gap-1 px-1.5 py-1">
                  {tabs.map((tab, index) => {
                    const isActive = tab.tabId === activeTabId;
                    return (
                      <div
                        key={tab.tabId}
                        className="session-rail__tab-shell inline-flex min-w-0 items-center"
                        data-state={isActive ? "active" : "inactive"}
                        data-variant={isActive ? "pill" : "segment"}
                        style={{
                          flex: "0 0 auto",
                          maxWidth: isActive
                            ? "var(--cfy-session-tab-active-basis)"
                            : "var(--cfy-session-tab-inactive-basis)",
                        }}
                      >
                        {index > 0 && !isActive ? (
                          <span
                            aria-hidden="true"
                            className="session-rail__divider mx-1.5 h-4 w-px shrink-0"
                            style={{
                              background:
                                "color-mix(in oklab, var(--panel-border) 76%, transparent)",
                            }}
                          />
                        ) : null}
                        <div
                          className="inline-flex min-w-0 items-center"
                          style={
                            isActive
                              ? {
                                  borderRadius: 999,
                                  border: "1px solid var(--chip-border)",
                                  background:
                                    "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
                                  boxShadow:
                                    "inset 0 1px 0 rgba(255,255,255,0.16), 0 3px 10px rgba(0,0,0,0.14)",
                                  padding: "0.25rem 0.375rem 0.25rem 0.625rem",
                                }
                              : {
                                  padding: "0.25rem 0.125rem 0.25rem 0.125rem",
                                }
                          }
                        >
                          <button
                            type="button"
                            className="session-rail__tab block max-w-[220px] truncate px-0 py-1 text-sm font-medium"
                            data-state={isActive ? "active" : "inactive"}
                            data-variant={isActive ? "pill" : "segment"}
                            onClick={() => onActivateTab(tab.tabId)}
                            title={tabLabel(tab)}
                            style={{
                              background: "transparent",
                              color: isActive ? "var(--text)" : "var(--text-subtle)",
                            }}
                          >
                            {tabLabel(tab)}
                          </button>
                          {canCloseTabs && (
                            <button
                              type="button"
                              className="session-rail__close ml-1 inline-flex h-6 w-6 items-center justify-center rounded-full transition-opacity"
                              onClick={() => onCloseTab(tab.tabId)}
                              aria-label={`Close ${tabLabel(tab)}`}
                              title="Close tab"
                              style={{
                                color: isActive
                                  ? "var(--text-subtle)"
                                  : "var(--muted)",
                                opacity: isActive ? 0.78 : 0.56,
                              }}
                            >
                              <X className="h-3.5 w-3.5" />
                            </button>
                          )}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>
            <div
              aria-hidden="true"
              className="session-rail__endcap mr-1.5 h-8 w-4 shrink-0 rounded-[999px]"
              data-testid="session-rail-endcap"
              style={{
                background:
                  "color-mix(in oklab, var(--panel-bg) 46%, transparent)",
              }}
            />
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
