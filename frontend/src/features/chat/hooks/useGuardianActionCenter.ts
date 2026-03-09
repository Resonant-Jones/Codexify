import { useCallback, useEffect, useState } from "react";

import {
  fetchGuardianActionCenterSnapshot,
  type GuardianActionCenterContext,
  type GuardianActionCenterSnapshot,
} from "@/features/chat/api/actionCenter";

export type UseGuardianActionCenterResult = {
  error: string | null;
  hasLoaded: boolean;
  loading: boolean;
  reload: () => Promise<void>;
  snapshot: GuardianActionCenterSnapshot | null;
};

function getErrorMessage(error: unknown): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as { data?: { detail?: unknown; error?: unknown } };
    if (typeof response.data?.detail === "string" && response.data.detail.trim()) {
      return response.data.detail;
    }
    if (typeof response.data?.error === "string" && response.data.error.trim()) {
      return response.data.error;
    }
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }

  return "Failed to load Guardian Action Center.";
}

export function useGuardianActionCenter(
  context: GuardianActionCenterContext = {}
): UseGuardianActionCenterResult {
  const { threadId } = context;
  const [snapshot, setSnapshot] = useState<GuardianActionCenterSnapshot | null>(
    null
  );
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextSnapshot = await fetchGuardianActionCenterSnapshot({ threadId });
      setSnapshot(nextSnapshot);
      setHasLoaded(true);
      setError(
        nextSnapshot.warnings.length > 0
          ? nextSnapshot.warnings.join(" ")
          : null
      );
    } catch (nextError) {
      setSnapshot(null);
      setHasLoaded(true);
      setError(getErrorMessage(nextError));
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return {
    error,
    hasLoaded,
    loading,
    reload,
    snapshot,
  };
}

export default useGuardianActionCenter;
