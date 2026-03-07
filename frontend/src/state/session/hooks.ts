import React from "react";

import type { ComposerInferenceMode } from "@/types/inference";
import type { SessionSpine } from "@/state/session/SessionSpine";
import { DEFAULT_MODEL_ID } from "@/state/session/types";
import type { SessionState, SessionTab, TabId } from "@/state/session/types";

type Selector<T> = (state: SessionState | null) => T;
type Equality<T> = (a: T, b: T) => boolean;

const EMPTY_TABS: SessionTab[] = [];
const EMPTY_RAIL_SLICE: SessionRailSlice = {
  tabs: EMPTY_TABS,
  activeTabId: null,
};

function isSessionTabEqual(a: SessionTab | null, b: SessionTab | null): boolean {
  if (a === b) return true;
  if (!a || !b) return false;
  return (
    a.tabId === b.tabId &&
    a.threadId === b.threadId &&
    a.pendingThread === b.pendingThread &&
    a.title === b.title &&
    (a.providerId ?? null) === (b.providerId ?? null) &&
    a.modelId === b.modelId &&
    a.inferenceMode === b.inferenceMode &&
    a.createdAt === b.createdAt &&
    a.updatedAt === b.updatedAt
  );
}

function areTabsEqual(a: SessionTab[], b: SessionTab[]): boolean {
  if (a === b) return true;
  if (a.length !== b.length) return false;
  for (let i = 0; i < a.length; i += 1) {
    if (!isSessionTabEqual(a[i], b[i])) return false;
  }
  return true;
}

export type SessionRailSlice = {
  tabs: SessionTab[];
  activeTabId: TabId | null;
};

export function getWrappedSessionTabId(
  tabs: SessionTab[],
  activeTabId: TabId | null,
  direction: 1 | -1
): TabId | null {
  if (tabs.length <= 1) return activeTabId;
  const activeIndex = tabs.findIndex((tab) => tab.tabId === activeTabId);
  if (activeIndex < 0) return tabs[0]?.tabId ?? null;
  const nextIndex = (activeIndex + direction + tabs.length) % tabs.length;
  return tabs[nextIndex]?.tabId ?? null;
}

function isRailSliceEqual(a: SessionRailSlice, b: SessionRailSlice): boolean {
  return a.activeTabId === b.activeTabId && areTabsEqual(a.tabs, b.tabs);
}

function selectRailSlice(state: SessionState | null): SessionRailSlice {
  if (!state) return EMPTY_RAIL_SLICE;
  return {
    tabs: state.tabs,
    activeTabId: state.activeTabId ?? null,
  };
}

function selectActiveTab(state: SessionState | null): SessionTab | null {
  if (!state) return null;
  return state.tabs.find((tab) => tab.tabId === state.activeTabId) ?? null;
}

function selectActiveModelId(
  state: SessionState | null,
  fallback = DEFAULT_MODEL_ID
): string {
  return selectActiveTab(state)?.modelId || fallback;
}

function selectActiveProviderId(state: SessionState | null): string | null {
  return selectActiveTab(state)?.providerId ?? null;
}

function selectActiveInferenceMode(
  state: SessionState | null,
  fallback: ComposerInferenceMode
): ComposerInferenceMode {
  return selectActiveTab(state)?.inferenceMode ?? fallback;
}

function selectActiveThreadId(state: SessionState | null): string | null {
  return selectActiveTab(state)?.threadId ?? null;
}

function selectActiveDraft(state: SessionState | null): string {
  const activeTabId = state?.activeTabId;
  if (!activeTabId) return "";
  return state?.drafts?.[activeTabId] ?? "";
}

export function useSessionSpineSelector<T>(
  spine: SessionSpine | null,
  selector: Selector<T>,
  options: {
    fallback: T;
    isEqual?: Equality<T>;
  }
): T {
  const isEqual = options.isEqual ?? Object.is;
  const fallback = options.fallback;
  const selectorRef = React.useRef(selector);
  const equalRef = React.useRef(isEqual);

  selectorRef.current = selector;
  equalRef.current = isEqual;

  const [selected, setSelected] = React.useState<T>(() => {
    if (!spine) return fallback;
    return selector(spine.getSnapshot());
  });

  React.useEffect(() => {
    if (!spine) {
      setSelected((prev) => (equalRef.current(prev, fallback) ? prev : fallback));
      return;
    }

    const updateFromSnapshot = (snapshot: SessionState | null) => {
      const next = selectorRef.current(snapshot);
      setSelected((prev) => (equalRef.current(prev, next) ? prev : next));
    };

    updateFromSnapshot(spine.getSnapshot());
    return spine.subscribe((snapshot) => {
      updateFromSnapshot(snapshot);
    });
  }, [fallback, spine]);

  return selected;
}

export function useSessionRailSlice(
  spine: SessionSpine | null
): SessionRailSlice {
  return useSessionSpineSelector(spine, selectRailSlice, {
    fallback: EMPTY_RAIL_SLICE,
    isEqual: isRailSliceEqual,
  });
}

export function useSessionActiveTab(
  spine: SessionSpine | null
): SessionTab | null {
  return useSessionSpineSelector(spine, selectActiveTab, {
    fallback: null,
    isEqual: isSessionTabEqual,
  });
}

export function useSessionActiveModelId(
  spine: SessionSpine | null,
  fallback = DEFAULT_MODEL_ID
): string {
  const selector = React.useCallback(
    (state: SessionState | null) => selectActiveModelId(state, fallback),
    [fallback]
  );
  return useSessionSpineSelector(spine, selector, {
    fallback,
  });
}

export function useSessionActiveThreadId(
  spine: SessionSpine | null
): string | null {
  return useSessionSpineSelector(spine, selectActiveThreadId, {
    fallback: null,
  });
}

export function useSessionActiveDraft(
  spine: SessionSpine | null
): string {
  return useSessionSpineSelector(spine, selectActiveDraft, {
    fallback: "",
  });
}

export function useSessionActiveProviderId(
  spine: SessionSpine | null
): string | null {
  return useSessionSpineSelector(spine, selectActiveProviderId, {
    fallback: null,
  });
}

export function useSessionActiveInferenceMode(
  spine: SessionSpine | null,
  fallback: ComposerInferenceMode
): ComposerInferenceMode {
  const selector = React.useCallback(
    (state: SessionState | null) => selectActiveInferenceMode(state, fallback),
    [fallback]
  );
  return useSessionSpineSelector(spine, selector, {
    fallback,
  });
}
