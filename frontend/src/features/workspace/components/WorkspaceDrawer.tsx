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
import type { WorkspaceLayoutMode } from "../state/useWorkspaceLayoutMode";

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
  activeThreadId?: string | number | null;
  onMoveScratchpadToComposer?: (text: string) => void;
};

const WORKSPACE_PANEL_COPY: Record<WorkspaceDrawerTab, string> = {
  shelf: "Shelf items will appear here in a later phase.",
  scratchpad: "Scratchpad editing lands in Phase 2 with text input and autosave.",
  inspector: "Inspector renderers will plug into this panel in a later phase.",
};

function formatLayoutModeLabel(layoutMode: WorkspaceLayoutMode): string {
  switch (layoutMode) {
    case "workspace_focus":
      return "Workspace focus";
    case "balanced_split":
      return "Balanced split";
    case "chat_focus":
    default:
      return "Chat focus";
  }
}

function resolveRouteThreadIdentity(): string | null {
  if (typeof window === "undefined") return null;
  const match = window.location.pathname.match(/^\/chat\/([^/]+)/);
  return match?.[1] ? decodeURIComponent(match[1]) : null;
}

export default function WorkspaceDrawer({
  routeContext,
  isOpen,
  activeTab,
  layoutMode = "balanced_split",
  paneRatio,
  minPaneRatio,
  maxPaneRatio,
  onActiveTabChange,
  activeThreadId,
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
  const layoutModeLabel = formatLayoutModeLabel(layoutMode);
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
          <p
            data-testid="workspace-drawer-posture"
            className="mt-1 text-[11px] font-medium tracking-[0.04em]"
            style={{ color: "var(--text-subtle)" }}
          >
            {layoutModeLabel}
          </p>
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
