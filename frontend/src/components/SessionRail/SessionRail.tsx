import { MoreHorizontal, Plus, X } from "lucide-react";
import React from "react";

import { ProviderSelect } from "@/components/ProviderSelect";
import type { SessionTab, TabId } from "@/state/session/types";

type SessionRailProps = {
  tabs: SessionTab[];
  activeTabId: TabId | null;
  activeModelId: string;
  showTabs?: boolean;
  onActivateTab: (tabId: TabId) => void;
  onCloseTab: (tabId: TabId) => void;
  onOpenTab: () => void;
  onSetModel: (modelId: string) => void;
};

const SESSION_RAIL_STYLES: Record<"container" | "tabsEdgeMask" | "modelTrigger", React.CSSProperties> = {
  container: {
    border: "1px solid color-mix(in oklab, var(--panel-border) 76%, transparent)",
    borderRadius: "calc(var(--tile-radius) - 2px)",
    background:
      "linear-gradient(180deg, rgba(255,255,255,0.14), rgba(255,255,255,0.02)), color-mix(in oklab, var(--panel-bg) 66%, transparent)",
    boxShadow: "inset 0 1px 0 rgba(255,255,255,0.2), inset 0 -1px 0 rgba(0,0,0,0.16)",
    backdropFilter: "blur(12px) saturate(122%)",
    WebkitBackdropFilter: "blur(12px) saturate(122%)",
    isolation: "isolate",
  },
  tabsEdgeMask: {
    maskImage:
      "linear-gradient(to right, transparent 0px, black 14px, black calc(100% - 14px), transparent 100%)",
    WebkitMaskImage:
      "linear-gradient(to right, transparent 0px, black 14px, black calc(100% - 14px), transparent 100%)",
  },
  modelTrigger: {
    borderColor: "color-mix(in oklab, var(--panel-border) 80%, transparent)",
    background: "color-mix(in oklab, var(--panel-bg) 88%, transparent)",
    color: "color-mix(in oklab, var(--text) 82%, transparent)",
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
  activeModelId,
  showTabs,
  onActivateTab,
  onCloseTab,
  onOpenTab,
  onSetModel,
}: SessionRailProps) {
  const shouldShowTabs = showTabs ?? tabs.length > 1;
  const canCloseTabs = tabs.length > 1;
  return (
    <div className="session-rail shrink-0 flex items-center gap-2 px-3 py-2" style={SESSION_RAIL_STYLES.container}>
      {shouldShowTabs ? (
        <div className="min-w-0 flex-1 overflow-hidden">
          <div
            className="session-rail__tabs-scroll overflow-x-auto [scrollbar-width:thin]"
            style={tabs.length > 2 ? SESSION_RAIL_STYLES.tabsEdgeMask : undefined}
          >
            <div className="inline-flex min-w-full items-center gap-2">
              {tabs.map((tab) => {
                const isActive = tab.tabId === activeTabId;
                return (
                  <div
                    key={tab.tabId}
                    className="session-rail__tab-shell inline-flex items-center gap-1 rounded-[var(--tile-radius)] pr-1"
                    data-state={isActive ? "active" : "inactive"}
                  >
                    <button
                      type="button"
                      className="pill-tab session-rail__tab max-w-[220px]"
                      data-state={isActive ? "active" : "inactive"}
                      onClick={() => onActivateTab(tab.tabId)}
                      title={tabLabel(tab)}
                    >
                      <span className="truncate">{tabLabel(tab)}</span>
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

      <div className="session-rail__tools shrink-0 flex items-center gap-1">
        <ProviderSelect
          value={activeModelId}
          onChange={onSetModel}
          triggerClassName="session-rail__model-trigger"
          triggerStyle={SESSION_RAIL_STYLES.modelTrigger}
        />
        <button
          type="button"
          className="icon-inline session-rail__tool-btn"
          aria-label="New tab"
          title="New tab"
          onClick={onOpenTab}
          style={{ borderRadius: "var(--radius-micro)" }}
        >
          <Plus className="h-5 w-5" />
        </button>
        <button
          type="button"
          className="icon-inline session-rail__tool-btn"
          aria-label="Tab overflow"
          title="More tab actions"
          style={{ borderRadius: "var(--radius-micro)" }}
        >
          <MoreHorizontal className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

export default SessionRail;
