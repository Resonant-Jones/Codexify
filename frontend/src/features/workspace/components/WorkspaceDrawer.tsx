import React from "react";

import FrameCard from "@/components/surface/FrameCard";

import WorkspaceScratchpadPanel from "./WorkspaceScratchpadPanel";
import WorkspaceTabs from "./WorkspaceTabs";
import type {
  WorkspaceDrawerTab,
  WorkspaceRouteContext,
} from "../state/useWorkspaceUiState";
import type { WorkspaceLayoutMode } from "../state/useWorkspaceLayoutMode";

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

const WORKSPACE_PANEL_COPY: Record<
  WorkspaceDrawerTab,
  { title: string; body: string }
> = {
  shelf: {
    title: "Shelf",
    body: "Shelf items will appear here in a later phase.",
  },
  scratchpad: {
    title: "Scratchpad",
    body: "Scratchpad editing lands in Phase 2 with text input and autosave.",
  },
  inspector: {
    title: "Inspector",
    body: "Inspector renderers will plug into this panel in a later phase.",
  },
};

function formatRouteContextLabel(routeContext: WorkspaceRouteContext): string {
  const normalized = String(routeContext ?? "").trim().toLowerCase();
  if (!normalized) return "Workspace";
  return normalized.charAt(0).toUpperCase() + normalized.slice(1);
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
  onOpenChange,
  onActiveTabChange,
  activeThreadId,
  onMoveScratchpadToComposer,
}: WorkspaceDrawerProps) {
  if (!isOpen) return null;

  const panel = WORKSPACE_PANEL_COPY[activeTab];
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
        data-pane-ratio={paneRatio?.toFixed(2)}
        data-pane-ratio-min={minPaneRatio?.toFixed(2)}
        data-pane-ratio-max={maxPaneRatio?.toFixed(2)}
      >
        <div className="mb-3 flex items-start justify-between gap-3">
          <div className="min-w-0">
            <div
              className="text-sm font-semibold"
              style={{ color: "var(--text)" }}
            >
              Workspace
            </div>
            <div
              className="text-xs"
              style={{ color: "var(--muted)" }}
            >
              {formatRouteContextLabel(routeContext)} surface
            </div>
          </div>
          <button
            type="button"
            aria-label="Close workspace"
            data-testid="workspace-drawer-close"
            className="flex h-8 w-8 items-center justify-center rounded-[var(--radius-micro)] border text-sm"
            style={{
              borderColor: "var(--panel-border)",
              background: "var(--chip-bg)",
              color: "var(--text)",
            }}
            onClick={() => onOpenChange(false)}
          >
            ×
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
            <div className="flex flex-1 min-h-0 flex-col justify-between gap-4">
              <div className="space-y-2">
                <h2 className="text-sm font-semibold">{panel.title}</h2>
                <p
                  className="text-sm leading-6"
                  style={{ color: "var(--muted)" }}
                >
                  {panel.body}
                </p>
              </div>

              <div
                className="rounded-[var(--radius-micro)] border px-3 py-2 text-xs"
                style={{
                  borderColor: "var(--chip-border)",
                  background: "var(--chip-bg)",
                  color: "var(--text-subtle)",
                }}
              >
                Phase 1 shell only.
              </div>
            </div>
          </section>
        )}
      </div>
    </FrameCard>
  );
}
