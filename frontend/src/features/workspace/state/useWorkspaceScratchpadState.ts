import { useCallback, useEffect, useMemo, useRef, useState } from "react";

export const WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS = 400;
export const WORKSPACE_SCRATCHPAD_FALLBACK_THREAD_KEY = "fallback";
export const WORKSPACE_SCRATCHPAD_STORAGE_PREFIX =
  "cfy.workspace.scratchpad";

type UseWorkspaceScratchpadStateOptions = {
  threadIdentity?: string | number | null;
};

export function getWorkspaceScratchpadThreadKey(
  threadIdentity?: string | number | null
): string {
  const normalized = String(threadIdentity ?? "").trim();
  return normalized || WORKSPACE_SCRATCHPAD_FALLBACK_THREAD_KEY;
}

export function getWorkspaceScratchpadStorageKey(
  threadIdentity?: string | number | null
): string {
  return `${WORKSPACE_SCRATCHPAD_STORAGE_PREFIX}.${getWorkspaceScratchpadThreadKey(
    threadIdentity
  )}`;
}

function readWorkspaceScratchpadValue(storageKey: string): string {
  if (typeof window === "undefined") return "";

  try {
    const raw = window.localStorage.getItem(storageKey);
    return typeof raw === "string" ? raw : "";
  } catch {
    return "";
  }
}

function persistWorkspaceScratchpadValue(
  storageKey: string,
  value: string
): void {
  if (typeof window === "undefined") return;

  try {
    if (value.length === 0) {
      window.localStorage.removeItem(storageKey);
      return;
    }
    window.localStorage.setItem(storageKey, value);
  } catch {
    // Ignore storage failures for ephemeral UI state.
  }
}

export function useWorkspaceScratchpadState({
  threadIdentity,
}: UseWorkspaceScratchpadStateOptions) {
  const threadKey = useMemo(
    () => getWorkspaceScratchpadThreadKey(threadIdentity),
    [threadIdentity]
  );
  const storageKey = useMemo(
    () => getWorkspaceScratchpadStorageKey(threadIdentity),
    [threadIdentity]
  );
  const [text, setTextState] = useState<string>(() =>
    readWorkspaceScratchpadValue(storageKey)
  );
  const textRef = useRef(text);
  const activeStorageKeyRef = useRef(storageKey);
  const autosaveTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const cancelAutosave = useCallback(() => {
    if (!autosaveTimerRef.current) return;
    clearTimeout(autosaveTimerRef.current);
    autosaveTimerRef.current = null;
  }, []);

  const commitValue = useCallback((nextStorageKey: string, value: string) => {
    persistWorkspaceScratchpadValue(nextStorageKey, value);
  }, []);

  const setText = useCallback((nextValue: string) => {
    textRef.current = nextValue;
    setTextState(nextValue);
  }, []);

  const clear = useCallback(() => {
    cancelAutosave();
    textRef.current = "";
    setTextState("");
    persistWorkspaceScratchpadValue(storageKey, "");
  }, [cancelAutosave, storageKey]);

  useEffect(() => {
    textRef.current = text;
  }, [text]);

  useEffect(() => {
    if (activeStorageKeyRef.current === storageKey) return;

    cancelAutosave();
    commitValue(activeStorageKeyRef.current, textRef.current);

    activeStorageKeyRef.current = storageKey;
    const nextValue = readWorkspaceScratchpadValue(storageKey);
    textRef.current = nextValue;
    setTextState(nextValue);
  }, [cancelAutosave, commitValue, storageKey]);

  useEffect(() => {
    if (activeStorageKeyRef.current !== storageKey) return;

    cancelAutosave();
    autosaveTimerRef.current = setTimeout(() => {
      commitValue(storageKey, text);
      autosaveTimerRef.current = null;
    }, WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS);

    return cancelAutosave;
  }, [cancelAutosave, commitValue, storageKey, text]);

  useEffect(() => {
    return () => {
      cancelAutosave();
      commitValue(activeStorageKeyRef.current, textRef.current);
    };
  }, [cancelAutosave, commitValue]);

  return {
    text,
    setText,
    clear,
    threadKey,
    storageKey,
    autosaveDebounceMs: WORKSPACE_SCRATCHPAD_AUTOSAVE_DEBOUNCE_MS,
  };
}
