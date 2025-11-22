import { useCallback, useState } from "react";
import api from "@/lib/api";
import { RagTraceResponse } from "@/types/rag";

interface UseRAGTraceState {
  trace: RagTraceResponse | null;
  loading: boolean;
  error: string | null;
}

/**
 * Hook to fetch and manage RAG trace data for a given thread
 */
export function useRAGTrace(threadId: number | null) {
  const [state, setState] = useState<UseRAGTraceState>({
    trace: null,
    loading: false,
    error: null,
  });

  const fetchTrace = useCallback(async () => {
    if (!threadId) {
      setState({ trace: null, loading: false, error: null });
      return;
    }

    setState((prev) => ({ ...prev, loading: true, error: null }));

    try {
      const response = await api.get<RagTraceResponse>(
        `/chat/${threadId}/debug/rag-trace/latest`
      );
      setState({
        trace: response.data,
        loading: false,
        error: null,
      });
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to load RAG trace";

      // If it's a 404, it just means no trace exists yet (not an error)
      if (errorMessage.includes("404")) {
        setState({
          trace: null,
          loading: false,
          error: null,
        });
      } else {
        setState({
          trace: null,
          loading: false,
          error: errorMessage,
        });
      }
    }
  }, [threadId]);

  return {
    ...state,
    fetchTrace,
  };
}
