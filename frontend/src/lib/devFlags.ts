/**
 * Developer feature flags
 *
 * Controls visibility and behavior of development-only features.
 * Can be toggled via environment variables or localStorage.
 */

const DEV_FLAG_STORAGE_KEY = "cfy:dev-flags";

interface DevFlags {
  showRagTraceUI: boolean;
}

const defaultFlags: DevFlags = {
  showRagTraceUI: import.meta.env.VITE_SHOW_RAG_TRACE_UI === "true",
};

/**
 * Get current dev flags from localStorage and environment
 */
export function getDevFlags(): DevFlags {
  try {
    const stored = localStorage.getItem(DEV_FLAG_STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...defaultFlags, ...parsed };
    }
  } catch {
    // Ignore localStorage errors
  }
  return defaultFlags;
}

/**
 * Set a dev flag in localStorage
 */
export function setDevFlag<K extends keyof DevFlags>(key: K, value: DevFlags[K]) {
  try {
    const flags = getDevFlags();
    flags[key] = value;
    localStorage.setItem(DEV_FLAG_STORAGE_KEY, JSON.stringify(flags));
  } catch {
    // Ignore localStorage errors
  }
}

/**
 * Toggle a boolean dev flag
 */
export function toggleDevFlag(key: keyof DevFlags) {
  const flags = getDevFlags();
  if (typeof flags[key] === "boolean") {
    setDevFlag(key, !flags[key] as any);
  }
}

/**
 * Check if RAG trace UI is enabled
 */
export function isRagTraceUIEnabled(): boolean {
  return getDevFlags().showRagTraceUI;
}
