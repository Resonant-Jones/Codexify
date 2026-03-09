import { useCallback, useEffect, useState } from "react";

import {
  fetchGuardianApprovalInboxSnapshot,
  type GuardianApprovalInboxContext,
  type GuardianApprovalInboxSnapshot,
} from "@/features/chat/api/approvalInbox";

export type UseGuardianApprovalInboxResult = {
  error: string | null;
  hasLoaded: boolean;
  loading: boolean;
  reload: () => Promise<void>;
  snapshot: GuardianApprovalInboxSnapshot | null;
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

  return "Failed to load Guardian Approval Inbox.";
}

export function useGuardianApprovalInbox(
  context: GuardianApprovalInboxContext = {}
): UseGuardianApprovalInboxResult {
  const { threadId } = context;
  const [snapshot, setSnapshot] =
    useState<GuardianApprovalInboxSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextSnapshot = await fetchGuardianApprovalInboxSnapshot({ threadId });
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

export default useGuardianApprovalInbox;
