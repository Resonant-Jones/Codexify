import React from "react";
import { MoreHorizontal, Plus, X } from "lucide-react";

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
    <div className="shrink-0 flex items-center gap-2 px-3 pb-2">
      {shouldShowTabs ? (
        <div className="min-w-0 flex-1 overflow-x-auto [scrollbar-width:thin]">
          <div className="inline-flex min-w-full items-center gap-2">
            {tabs.map((tab) => (
              <div
                key={tab.tabId}
                className="inline-flex items-center gap-1 rounded-[var(--tile-radius)] border border-transparent pr-1"
                data-state={tab.tabId === activeTabId ? "active" : "inactive"}
                style={{
                  background:
                    tab.tabId === activeTabId
                      ? "color-mix(in oklab, var(--accent-strong) 84%, transparent)"
                      : "transparent",
                }}
              >
                <button
                  type="button"
                  className="pill-tab max-w-[220px]"
                  data-state={tab.tabId === activeTabId ? "active" : "inactive"}
                  onClick={() => onActivateTab(tab.tabId)}
                  title={tabLabel(tab)}
                >
                  <span className="truncate">{tabLabel(tab)}</span>
                </button>
                {canCloseTabs && (
                  <button
                    type="button"
                    className="inline-flex h-7 w-7 items-center justify-center rounded-full opacity-70 hover:opacity-100"
                    onClick={() => onCloseTab(tab.tabId)}
                    aria-label={`Close ${tabLabel(tab)}`}
                    title="Close tab"
                  >
                    <X className="h-3.5 w-3.5" />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      ) : (
        <div className="flex-1" />
      )}

      <div className="shrink-0 flex items-center gap-1">
        <ProviderSelect value={activeModelId} onChange={onSetModel} />
        <button
          type="button"
          className="icon-inline"
          aria-label="New tab"
          title="New tab"
          onClick={onOpenTab}
          style={{ borderRadius: "var(--radius-micro)" }}
        >
          <Plus className="h-5 w-5" />
        </button>
        <button
          type="button"
          className="icon-inline"
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
