import { useCallback, useEffect, useMemo, useState } from "react";

export const WORKSPACE_LAYOUT_STORAGE_KEY = "cfy.workspace.layout";
export const MIN_WORKSPACE_PANE_RATIO = 0.28;
export const MAX_WORKSPACE_PANE_RATIO = 0.62;
export const DEFAULT_WORKSPACE_PANE_RATIO = 0.42;
export const BALANCED_SPLIT_MIN_RATIO = 0.36;
export const WORKSPACE_FOCUS_MIN_RATIO = 0.52;

export type WorkspaceLayoutMode =
  | "chat_focus"
  | "balanced_split"
  | "workspace_focus";

type PersistedWorkspaceLayoutState = {
  paneRatio?: number;
};

type UseWorkspaceLayoutModeOptions = {
  isOpen: boolean;
  initialPaneRatio?: number;
  storageKey?: string;
};

function isFiniteNumber(value: unknown): value is number {
  return typeof value === "number" && Number.isFinite(value);
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

function readPersistedWorkspaceLayoutState(
  storageKey: string
): PersistedWorkspaceLayoutState {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(storageKey);
    if (!raw) return {};

    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }

    return parsed as PersistedWorkspaceLayoutState;
  } catch {
    return {};
  }
}

export function useWorkspaceLayoutMode({
  isOpen,
  initialPaneRatio,
  storageKey = WORKSPACE_LAYOUT_STORAGE_KEY,
}: UseWorkspaceLayoutModeOptions) {
  const [paneRatio, setPaneRatioState] = useState<number>(() => {
    const persisted = readPersistedWorkspaceLayoutState(storageKey);

    if (isFiniteNumber(persisted.paneRatio)) {
      return clampWorkspacePaneRatio(persisted.paneRatio);
    }

    return clampWorkspacePaneRatio(
      initialPaneRatio ?? DEFAULT_WORKSPACE_PANE_RATIO
    );
  });

  useEffect(() => {
    if (typeof window === "undefined") return;

    try {
      window.localStorage.setItem(
        storageKey,
        JSON.stringify({ paneRatio })
      );
    } catch {
      // Ignore local-only persistence failures.
    }
  }, [paneRatio, storageKey]);

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

  const layoutMode = useMemo(
    () => deriveWorkspaceLayoutMode({ isOpen, paneRatio }),
    [isOpen, paneRatio]
  );
  const primaryPaneRatio = 1 - paneRatio;

  return {
    paneRatio,
    setPaneRatio,
    minPaneRatio: MIN_WORKSPACE_PANE_RATIO,
    maxPaneRatio: MAX_WORKSPACE_PANE_RATIO,
    primaryPaneRatio,
    layoutMode,
  };
}
