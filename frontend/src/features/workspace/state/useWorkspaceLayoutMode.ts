import { useCallback, useEffect, useMemo, useState } from "react";

export const WORKSPACE_LAYOUT_STORAGE_KEY = "cfy.workspace.layout";
export const MIN_WORKSPACE_PANE_RATIO = 0.28;
export const MAX_WORKSPACE_PANE_RATIO = 0.62;
export const CHAT_FOCUS_WORKSPACE_PANE_RATIO = MIN_WORKSPACE_PANE_RATIO;
export const DEFAULT_WORKSPACE_PANE_RATIO = CHAT_FOCUS_WORKSPACE_PANE_RATIO;
export const BALANCED_SPLIT_WORKSPACE_PANE_RATIO = 0.42;
export const WORKSPACE_FOCUS_WORKSPACE_PANE_RATIO = MAX_WORKSPACE_PANE_RATIO;
export const BALANCED_SPLIT_MIN_RATIO = 0.36;
export const WORKSPACE_FOCUS_MIN_RATIO = 0.52;
export const MIN_WORKSPACE_PRIMARY_PANE_WIDTH = "24rem";
export const MIN_WORKSPACE_DRAWER_PANE_WIDTH = "20rem";
export const DEFAULT_WORKSPACE_LAYOUT_THREAD_KEY = "__workspace_default__";

export type WorkspaceLayoutMode =
  | "chat_focus"
  | "balanced_split"
  | "workspace_focus";
export type WorkspaceLayoutRatioBucket = "chat_first" | "shared" | "workspace_first";

type PersistedWorkspaceLayoutState = {
  layoutMode?: WorkspaceLayoutMode;
};

type UseWorkspaceLayoutModeOptions = {
  isOpen: boolean;
  activeThreadId?: string | number | null;
  storageKey?: string;
};

function isWorkspaceLayoutMode(value: unknown): value is WorkspaceLayoutMode {
  return (
    value === "chat_focus" ||
    value === "balanced_split" ||
    value === "workspace_focus"
  );
}

function getWorkspaceLayoutThreadKey(
  threadId: string | number | null | undefined
): string {
  if (threadId == null) {
    return DEFAULT_WORKSPACE_LAYOUT_THREAD_KEY;
  }

  const normalized = String(threadId).trim();
  return normalized || DEFAULT_WORKSPACE_LAYOUT_THREAD_KEY;
}

export function getWorkspaceLayoutStorageKeyForThread(
  threadId: string | number | null | undefined,
  storageKey = WORKSPACE_LAYOUT_STORAGE_KEY
): string {
  return `${storageKey}.${encodeURIComponent(getWorkspaceLayoutThreadKey(threadId))}`;
}

export function clampWorkspacePaneRatio(value: number): number {
  if (!Number.isFinite(value)) {
    return DEFAULT_WORKSPACE_PANE_RATIO;
  }

  return Math.min(MAX_WORKSPACE_PANE_RATIO, Math.max(MIN_WORKSPACE_PANE_RATIO, value));
}

export function deriveWorkspaceLayoutMode({
  isOpen,
  paneRatio,
}: {
  isOpen: boolean;
  paneRatio: number;
}): WorkspaceLayoutMode {
  const clampedPaneRatio = clampWorkspacePaneRatio(paneRatio);

  if (!isOpen || clampedPaneRatio < BALANCED_SPLIT_MIN_RATIO) {
    return "chat_focus";
  }

  if (clampedPaneRatio >= WORKSPACE_FOCUS_MIN_RATIO) {
    return "workspace_focus";
  }

  return "balanced_split";
}

export function getWorkspacePaneRatioForLayoutMode(
  layoutMode: WorkspaceLayoutMode
): number {
  switch (layoutMode) {
    case "workspace_focus":
      return WORKSPACE_FOCUS_WORKSPACE_PANE_RATIO;
    case "balanced_split":
      return BALANCED_SPLIT_WORKSPACE_PANE_RATIO;
    case "chat_focus":
    default:
      return CHAT_FOCUS_WORKSPACE_PANE_RATIO;
  }
}

export function getWorkspaceLayoutModeFromPaneRatio(
  paneRatio: number
): WorkspaceLayoutMode {
  const clampedPaneRatio = clampWorkspacePaneRatio(paneRatio);

  if (clampedPaneRatio < BALANCED_SPLIT_MIN_RATIO) {
    return "chat_focus";
  }

  if (clampedPaneRatio >= WORKSPACE_FOCUS_MIN_RATIO) {
    return "workspace_focus";
  }

  return "balanced_split";
}

export function getNextWorkspaceLayoutMode(
  layoutMode: WorkspaceLayoutMode
): WorkspaceLayoutMode {
  switch (layoutMode) {
    case "chat_focus":
      return "balanced_split";
    case "balanced_split":
      return "workspace_focus";
    case "workspace_focus":
    default:
      return "chat_focus";
  }
}

export function getWorkspaceLayoutModeLabel(
  layoutMode: WorkspaceLayoutMode
): string {
  switch (layoutMode) {
    case "workspace_focus":
      return "Workspace Focus";
    case "balanced_split":
      return "Balanced Split";
    case "chat_focus":
    default:
      return "Chat Focus";
  }
}

export function getWorkspaceLayoutRatioBucket(
  layoutMode: WorkspaceLayoutMode
): WorkspaceLayoutRatioBucket {
  switch (layoutMode) {
    case "workspace_focus":
      return "workspace_first";
    case "balanced_split":
      return "shared";
    case "chat_focus":
    default:
      return "chat_first";
  }
}

function readPersistedWorkspaceLayoutState(
  storageKey: string
): PersistedWorkspaceLayoutState {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw || !isWorkspaceLayoutMode(raw)) return {};

    return { layoutMode: raw };
  } catch {
    return {};
  }
}

export function useWorkspaceLayoutMode({
  isOpen,
  activeThreadId,
  storageKey = WORKSPACE_LAYOUT_STORAGE_KEY,
}: UseWorkspaceLayoutModeOptions) {
  const activeThreadStorageKey = useMemo(
    () => getWorkspaceLayoutStorageKeyForThread(activeThreadId, storageKey),
    [activeThreadId, storageKey]
  );

  const [paneRatio, setPaneRatioState] = useState<number>(() => {
    const persisted = readPersistedWorkspaceLayoutState(activeThreadStorageKey);
    return getWorkspacePaneRatioForLayoutMode(
      persisted.layoutMode ?? "chat_focus"
    );
  });

  useEffect(() => {
    const persisted = readPersistedWorkspaceLayoutState(activeThreadStorageKey);
    const nextPaneRatio = getWorkspacePaneRatioForLayoutMode(
      persisted.layoutMode ?? "chat_focus"
    );

    setPaneRatioState((previousPaneRatio) =>
      previousPaneRatio === nextPaneRatio ? previousPaneRatio : nextPaneRatio
    );
  }, [activeThreadStorageKey]);

  const setPaneRatio = useCallback(
    (nextPaneRatio: number | ((previousPaneRatio: number) => number)) => {
      setPaneRatioState((previousPaneRatio) =>
        clampWorkspacePaneRatio(
          typeof nextPaneRatio === "function"
            ? nextPaneRatio(previousPaneRatio)
            : nextPaneRatio
        )
      );
    },
    []
  );

  const setLayoutMode = useCallback(
    (nextLayoutMode: WorkspaceLayoutMode) => {
      const nextPaneRatio = getWorkspacePaneRatioForLayoutMode(nextLayoutMode);
      setPaneRatioState(nextPaneRatio);

      if (typeof window === "undefined") return;

      try {
        window.localStorage.setItem(activeThreadStorageKey, nextLayoutMode);
      } catch {
        // Ignore local-only persistence failures.
      }
    },
    [activeThreadStorageKey]
  );

  const layoutMode = useMemo(
    () => deriveWorkspaceLayoutMode({ isOpen, paneRatio }),
    [isOpen, paneRatio]
  );
  const primaryPaneRatio = 1 - paneRatio;
  const isWorkspaceDominant = layoutMode === "workspace_focus";
  const ratioBucket = getWorkspaceLayoutRatioBucket(layoutMode);
  const workspacePaneBasis = `${(paneRatio * 100).toFixed(2)}%`;
  const primaryPaneBasis = `${(primaryPaneRatio * 100).toFixed(2)}%`;

  return {
    paneRatio,
    setPaneRatio,
    minPaneRatio: MIN_WORKSPACE_PANE_RATIO,
    maxPaneRatio: MAX_WORKSPACE_PANE_RATIO,
    primaryPaneRatio,
    workspacePaneBasis,
    primaryPaneBasis,
    primaryPaneMinWidth: MIN_WORKSPACE_PRIMARY_PANE_WIDTH,
    workspacePaneMinWidth: MIN_WORKSPACE_DRAWER_PANE_WIDTH,
    layoutMode,
    isWorkspaceDominant,
    ratioBucket,
    setLayoutMode,
  };
}
