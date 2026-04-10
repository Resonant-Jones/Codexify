import { useCallback, useEffect, useState } from "react";

import { useShellViewportClass } from "@/components/persona/layout/shellBreakpointContract";

export const WORKSPACE_UI_STORAGE_KEY = "cfy.workspace.ui";

export type WorkspaceDrawerTab = "shelf" | "scratchpad" | "inspector";
export type WorkspaceRouteContext =
  | "dashboard"
  | "guardian"
  | "documents"
  | string;

type PersistedWorkspaceUiState = {
  isOpen?: boolean;
  activeTab?: WorkspaceDrawerTab;
  lastNonCollapsedTab?: WorkspaceDrawerTab;
};

type UseWorkspaceUiStateOptions = {
  routeContext: WorkspaceRouteContext;
};

function isWorkspaceDrawerTab(value: unknown): value is WorkspaceDrawerTab {
  return (
    value === "shelf" || value === "scratchpad" || value === "inspector"
  );
}

export function getDefaultWorkspaceTab(
  routeContext: WorkspaceRouteContext
): WorkspaceDrawerTab {
  switch (String(routeContext ?? "").trim().toLowerCase()) {
    case "guardian":
      return "scratchpad";
    case "documents":
      return "inspector";
    case "dashboard":
    default:
      return "shelf";
  }
}

function readPersistedWorkspaceUiState(): PersistedWorkspaceUiState {
  if (typeof window === "undefined") return {};

  try {
    const raw = window.localStorage.getItem(WORKSPACE_UI_STORAGE_KEY);
    if (!raw) return {};
    const parsed = JSON.parse(raw);
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      return {};
    }
    return parsed as PersistedWorkspaceUiState;
  } catch {
    return {};
  }
}

export function useWorkspaceUiState({
  routeContext,
}: UseWorkspaceUiStateOptions) {
  const shellViewportClass = useShellViewportClass();
  const isPhoneShell = shellViewportClass === "phone";
  const [initialPersistedState] = useState<PersistedWorkspaceUiState>(() =>
    readPersistedWorkspaceUiState()
  );
  const [hasExplicitTab, setHasExplicitTab] = useState<boolean>(() =>
    isWorkspaceDrawerTab(initialPersistedState.activeTab)
  );
  const [isOpen, setIsOpen] = useState<boolean>(
    () => initialPersistedState.isOpen === true && !isPhoneShell
  );
  const [activeTab, setActiveTabState] = useState<WorkspaceDrawerTab>(() =>
    isWorkspaceDrawerTab(initialPersistedState.activeTab)
      ? initialPersistedState.activeTab
      : getDefaultWorkspaceTab(routeContext)
  );
  const [lastNonCollapsedTab, setLastNonCollapsedTab] =
    useState<WorkspaceDrawerTab>(() =>
      isWorkspaceDrawerTab(initialPersistedState.lastNonCollapsedTab)
        ? initialPersistedState.lastNonCollapsedTab
        : isWorkspaceDrawerTab(initialPersistedState.activeTab)
          ? initialPersistedState.activeTab
          : getDefaultWorkspaceTab(routeContext)
    );

  useEffect(() => {
    if (hasExplicitTab) return;
    const nextDefaultTab = getDefaultWorkspaceTab(routeContext);
    setActiveTabState(nextDefaultTab);
    setLastNonCollapsedTab(nextDefaultTab);
  }, [hasExplicitTab, routeContext]);

  useEffect(() => {
    if (!isPhoneShell) return;
    setIsOpen(false);
  }, [isPhoneShell]);

  useEffect(() => {
    if (typeof window === "undefined") return;

    const nextState: PersistedWorkspaceUiState = {
      isOpen,
    };

    if (hasExplicitTab) {
      nextState.activeTab = activeTab;
      nextState.lastNonCollapsedTab = lastNonCollapsedTab;
    }

    try {
      window.localStorage.setItem(
        WORKSPACE_UI_STORAGE_KEY,
        JSON.stringify(nextState)
      );
    } catch {
      // Ignore quota and storage access failures for UI-only state.
    }
  }, [activeTab, hasExplicitTab, isOpen, lastNonCollapsedTab]);

  const setActiveTab = useCallback((tab: WorkspaceDrawerTab) => {
    setHasExplicitTab(true);
    setActiveTabState(tab);
    setLastNonCollapsedTab(tab);
  }, []);

  const open = useCallback(
    (tab?: WorkspaceDrawerTab) => {
      if (tab) {
        setHasExplicitTab(true);
        setActiveTabState(tab);
        setLastNonCollapsedTab(tab);
      } else if (!hasExplicitTab) {
        const nextDefaultTab = getDefaultWorkspaceTab(routeContext);
        setActiveTabState(nextDefaultTab);
        setLastNonCollapsedTab(nextDefaultTab);
      }
      setIsOpen(true);
    },
    [hasExplicitTab, routeContext]
  );

  const close = useCallback(() => {
    setIsOpen(false);
  }, []);

  const toggle = useCallback(() => {
    setIsOpen((previous) => !previous);
  }, []);

  return {
    isOpen,
    activeTab,
    lastNonCollapsedTab,
    setActiveTab,
    open,
    close,
    toggle,
  };
}
