/**
 * Global Ephemeral RAG Trace Store
 *
 * Persists the last RAG context assembly for inspection in diagnostics.
 * Survives navigation between Chat → Settings but does NOT persist across page reloads.
 * This is intentional - ephemeral, session-bound cognitive state.
 */

export interface RAGTrace {
  semantic: Array<{ text: string; score?: number; metadata?: any }>;
  memory: Array<{ text: string; score?: number; metadata?: any }>;
  depth: "shallow" | "normal" | "deep" | "diagnostic";
  threadId: number | null;
  timestamp: number;
}

// Ephemeral in-memory store
let currentTrace: RAGTrace = {
  semantic: [],
  memory: [],
  depth: "normal",
  threadId: null,
  timestamp: Date.now(),
};

// Listeners for reactive updates
const listeners = new Set<() => void>();

/**
 * Subscribe to trace updates (for React components)
 */
export function subscribeToTrace(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

/**
 * Get the current RAG trace
 */
export function getTrace(): RAGTrace {
  return { ...currentTrace };
}

/**
 * Set a new RAG trace and notify listeners
 */
export function setTrace(trace: Partial<RAGTrace>): void {
  currentTrace = {
    ...currentTrace,
    ...trace,
    timestamp: Date.now(),
  };

  // Notify all subscribers
  listeners.forEach((listener) => listener());
}

/**
 * React hook for consuming trace state
 */
export function useContextTrace(): RAGTrace {
  const [trace, setLocalTrace] = React.useState<RAGTrace>(getTrace);

  React.useEffect(() => {
    const unsubscribe = subscribeToTrace(() => {
      setLocalTrace(getTrace());
    });
    return unsubscribe;
  }, []);

  return trace;
}

// For React import
import * as React from "react";
