import React, { useState } from "react";

import FrameCard from "@/components/surface/FrameCard";

import WorkspaceScratchpadPanel from "./WorkspaceScratchpadPanel";
import WorkspaceShelfPanel from "./WorkspaceShelfPanel";
import WorkspaceInspectorPanel from "./WorkspaceInspectorPanel";
import WorkspaceTabs from "./WorkspaceTabs";
import type {
  WorkspaceDrawerTab,
  WorkspaceRouteContext,
} from "../state/useWorkspaceUiState";
import {
  getNextWorkspaceLayoutMode,
  getWorkspaceLayoutModeLabel,
  getWorkspacePaneRatioForLayoutMode,
  type WorkspaceLayoutMode,
} from "../state/useWorkspaceLayoutMode";

type ShelfItem = { kind: "document"; item: { id: string; filename?: string; src_url: string; caption?: string; mime_type?: string; created_at?: string; project_id?: string | number; thread_id?: string | number } } | { kind: "image"; item: { id: string; src_url: string; filename?: string; caption?: string; created_at?: string; project_id?: string | number; thread_id?: string | number } };

type WorkspaceDrawerProps = {
  routeContext: WorkspaceRouteContext;
  isOpen: boolean;
  activeTab: WorkspaceDrawerTab;
  layoutMode?: WorkspaceLayoutMode;
  paneRatio?: number;
  minPaneRatio?: number;
  maxPaneRatio?: number;
  onOpenChange: (open: boolean) => void;
  onActiveTabChange: (tab: WorkspaceDrawerTab) => void;
  onLayoutModeChange?: (layoutMode: WorkspaceLayoutMode) => void;
  activeThreadId?: string | number | null;
  projectId?: string | number | null;
  onMoveScratchpadToComposer?: (text: string) => void;
};

const WORKSPACE_PANEL_COPY: Record<WorkspaceDrawerTab, string> = {
  shelf: "Shelf items will appear here in a later phase.",
  scratchpad: "Scratchpad editing lands in Phase 2 with text input and autosave.",
  inspector: "Inspector renderers will plug into this panel in a later phase.",
};

function resolveRouteThreadIdentity(): string | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/chat\/([^/]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export default function WorkspaceDrawer({
  routeContext,
  isOpen,
  activeTab,
  layoutMode = "chat_focus",
  paneRatio = getWorkspacePaneRatioForLayoutMode(layoutMode),
  minPaneRatio,
  maxPaneRatio,
  onActiveTabChange,
  onLayoutModeChange,
  activeThreadId,
  projectId,
  onMoveScratchpadToComposer,
}: WorkspaceDrawerProps) {
  const [selectedItem, setSelectedItem] = useState<ShelfItem | null>(null);

  const handleShelfItemClick = React.useCallback(
    (item: ShelfItem) => {
      if (item.kind === "document") {
        setSelectedItem(item);
        onActiveTabChange("inspector");
      }
    },
    [onActiveTabChange]
  );

  const panel = WORKSPACE_PANEL_COPY[activeTab];
  const layoutModeLabel = getWorkspaceLayoutModeLabel(layoutMode);
  const idBase = "workspace";
  const resolvedThreadIdentity =
    activeThreadId == null ? resolveRouteThreadIdentity() : activeThreadId;
  const handleMoveScratchpadToComposer = React.useCallback(
    (text: string) => {
      if (onMoveScratchpadToComposer) {
        onMoveScratchpadToComposer(text);
        return;
      }
      if (typeof window === "undefined") return;
      window.dispatchEvent(
        new CustomEvent("cfy:composer:prefill", {
          detail: { text },
        })
      );
    },
    [onMoveScratchpadToComposer]
  );
  const handlePostureClick = React.useCallback(
    (event: React.MouseEvent<HTMLButtonElement>) => {
      if (event.detail > 1) return;
      onLayoutModeChange?.(getNextWorkspaceLayoutMode(layoutMode));
    },
    [layoutMode, onLayoutModeChange]
  );
  const handlePostureDoubleClick = React.useCallback(() => {
    onLayoutModeChange?.("chat_focus");
  }, [onLayoutModeChange]);

  if (!isOpen) return null;

  return (
    <FrameCard
      fill
      refractiveFallback
      shimmerMode="subtle"
      className="flex h-full w-full min-h-0 flex-col overflow-hidden"
    >
      <div
        className="flex h-full min-h-0 flex-col p-[var(--card-pad)]"
        data-testid="workspace-drawer"
        data-route-context={String(routeContext ?? "")}
        data-layout-mode={layoutMode}
        data-layout-label={layoutModeLabel}
        data-pane-ratio={paneRatio?.toFixed(2)}
        data-pane-ratio-min={minPaneRatio?.toFixed(2)}
        data-pane-ratio-max={maxPaneRatio?.toFixed(2)}
      >
        <div
          className="mb-3 flex flex-col items-center text-center"
          data-testid="workspace-drawer-header"
          data-header-layout="centered"
        >
          <div
            className="text-[15px] font-semibold"
            data-testid="workspace-drawer-title"
            style={{ color: "var(--text)" }}
          >
            Workspace
          </div>
          <button
            data-testid="workspace-drawer-posture"
            className="group relative mt-1 inline-flex cursor-pointer items-center justify-center border-0 bg-transparent px-1 py-0 text-[11px] font-medium tracking-[0.04em] text-[var(--text-subtle)] transition-[color,filter,opacity] duration-200 hover:text-[var(--text)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[color-mix(in_oklab,var(--accent)_45%,transparent)] focus-visible:ring-offset-2"
            style={{ color: "var(--text-subtle)" }}
            onClick={handlePostureClick}
            onDoubleClick={handlePostureDoubleClick}
            title="Click to cycle posture. Double-click to reset to Chat Focus."
            type="button"
          >
            <span className="relative inline-flex items-center justify-center">
              {layoutModeLabel}
              <span
                aria-hidden="true"
                className="absolute inset-x-0 -bottom-0.5 h-px scale-x-0 bg-[color-mix(in_oklab,var(--accent)_55%,transparent)] opacity-0 shadow-[0_0_8px_color-mix(in_oklab,var(--accent)_45%,transparent)] transition-all duration-200 group-hover:scale-x-100 group-hover:opacity-100 group-focus-visible:scale-x-100 group-focus-visible:opacity-100"
              />
            </span>
          </button>
        </div>

        <WorkspaceTabs
          activeTab={activeTab}
          onTabChange={onActiveTabChange}
          idBase={idBase}
        />

        {activeTab === "scratchpad" ? (
          <section
            id={`${idBase}-panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`${idBase}-tab-${activeTab}`}
            className="mt-3 flex flex-1 min-h-0 flex-col rounded-[var(--radius)] border p-4"
            style={{
              borderColor: "var(--panel-border)",
              background:
                "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
              color: "var(--text)",
            }}
          >
            <WorkspaceScratchpadPanel
              threadIdentity={resolvedThreadIdentity}
              onMoveToComposer={handleMoveScratchpadToComposer}
            />
          </section>
        ) : activeTab === "shelf" ? (
          <section
            id={`${idBase}-panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`${idBase}-tab-${activeTab}`}
            className="mt-3 flex flex-1 min-h-0 flex-col rounded-[var(--radius)] border p-4"
            style={{
              borderColor: "var(--panel-border)",
              background:
                "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
              color: "var(--text)",
            }}
          >
            <WorkspaceShelfPanel
              threadIdentity={resolvedThreadIdentity}
              projectId={projectId}
              onItemClick={handleShelfItemClick}
            />
          </section>
        ) : (
          <section
            id={`${idBase}-panel-${activeTab}`}
            role="tabpanel"
            aria-labelledby={`${idBase}-tab-${activeTab}`}
            className="mt-3 flex flex-1 min-h-0 flex-col rounded-[var(--radius)] border p-4"
            style={{
              borderColor: "var(--panel-border)",
              background:
                "color-mix(in oklab, var(--panel-bg) 92%, transparent)",
              color: "var(--text)",
            }}
          >
            <WorkspaceInspectorPanel selectedItem={selectedItem} />
          </section>
        )}
      </div>
    </FrameCard>
  );
}
