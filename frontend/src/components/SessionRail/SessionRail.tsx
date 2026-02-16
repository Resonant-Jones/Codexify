import { ChevronDown, Cloud, Laptop, MoreHorizontal, Plus, X } from "lucide-react";
import React from "react";

import { ProviderSelect } from "@/components/ProviderSelect";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type { SessionTab, TabId } from "@/state/session/types";

type ProfileMode = "local" | "cloud";

type SystemProfileOption = {
  id: string;
  name: string;
  mode: ProfileMode;
  providerOverride?: string | null;
  modelOverride?: string | null;
};

type SessionRailProps = {
  tabs: SessionTab[];
  activeTabId: TabId | null;
  activeModelId: string;
  activeProfileId?: string | null;
  activeProfileName?: string | null;
  activeProfileMode?: ProfileMode | null;
  profiles?: SystemProfileOption[];
  profileSwitching?: boolean;
  showTabs?: boolean;
  onActivateTab: (tabId: TabId) => void;
  onCloseTab: (tabId: TabId) => void;
  onOpenTab: () => void;
  onSetModel: (modelId: string) => void;
  onSetProfile?: (profileId: string) => void;
};

const SESSION_RAIL_STYLES: Record<"container" | "tabsEdgeMask" | "modelTrigger" | "profileTrigger", React.CSSProperties> = {
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
  profileTrigger: {
    borderColor: "color-mix(in oklab, var(--panel-border) 80%, transparent)",
    background: "color-mix(in oklab, var(--panel-bg) 88%, transparent)",
    color: "color-mix(in oklab, var(--text) 88%, transparent)",
  },
};

const FALLBACK_PROFILES: SystemProfileOption[] = [
  { id: "default", name: "Default", mode: "cloud" },
  { id: "cloud_mode", name: "Cloud Profile", mode: "cloud" },
  { id: "local_mode", name: "Local Mode", mode: "local" },
];

function tabLabel(tab: SessionTab): string {
  if (tab.title && tab.title.trim()) return tab.title.trim();
  if (tab.threadId && tab.threadId.trim()) return `Thread ${tab.threadId.trim()}`;
  return "New Tab";
}

export function SessionRail({
  tabs,
  activeTabId,
  activeModelId,
  activeProfileId = null,
  activeProfileName = null,
  activeProfileMode = null,
  profiles = FALLBACK_PROFILES,
  profileSwitching = false,
  showTabs,
  onActivateTab,
  onCloseTab,
  onOpenTab,
  onSetModel,
  onSetProfile,
}: SessionRailProps) {
  const shouldShowTabs = showTabs ?? tabs.length > 1;
  const canCloseTabs = tabs.length > 1;
  const availableProfiles = profiles.length > 0 ? profiles : FALLBACK_PROFILES;
  const selectedProfile =
    availableProfiles.find((profile) => profile.id === activeProfileId) ??
    (activeProfileId
      ? {
          id: activeProfileId,
          name: activeProfileName || activeProfileId,
          mode: activeProfileMode || "cloud",
        }
      : availableProfiles[0]);
  const ProfileIcon = selectedProfile.mode === "local" ? Laptop : Cloud;
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
        <DropdownMenu>
          <DropdownMenuTrigger
            className="session-rail__profile-trigger inline-flex items-center gap-1.5 h-8 px-3 text-xs rounded-full border transition-colors hover:bg-[color-mix(in_oklab,var(--panel-bg),var(--panel-border)_15%)]"
            style={SESSION_RAIL_STYLES.profileTrigger}
            aria-label="Switch system profile"
            disabled={profileSwitching}
          >
            <ProfileIcon className="h-3.5 w-3.5 opacity-80" />
            <span className="font-medium truncate max-w-[140px]">
              {selectedProfile.name}
            </span>
            <ChevronDown className="h-3 w-3 opacity-60" />
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="min-w-[220px]">
            <div
              className="px-3 py-2 text-xs font-semibold opacity-70 border-b"
              style={{ borderColor: "var(--panel-border)" }}
            >
              System Profile
            </div>
            {availableProfiles.map((profile) => {
              const isSelected = profile.id === selectedProfile.id;
              const ItemIcon = profile.mode === "local" ? Laptop : Cloud;
              return (
                <DropdownMenuItem
                  key={profile.id}
                  disabled={profileSwitching}
                  onClick={() => onSetProfile?.(profile.id)}
                  style={{
                    color: "var(--text)",
                    background: isSelected
                      ? "color-mix(in_oklab,var(--panel-bg),var(--accent)_15%)"
                      : "transparent",
                  }}
                >
                  <span className="flex items-center justify-between w-full gap-2">
                    <span className="inline-flex items-center gap-2 min-w-0">
                      <ItemIcon className="h-3.5 w-3.5 opacity-70 shrink-0" />
                      <span className="truncate">{profile.name}</span>
                    </span>
                    {isSelected && (
                      <span className="text-[var(--accent)]">✓</span>
                    )}
                  </span>
                </DropdownMenuItem>
              );
            })}
          </DropdownMenuContent>
        </DropdownMenu>
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
