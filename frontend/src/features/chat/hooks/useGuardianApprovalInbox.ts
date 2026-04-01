import { useCallback, useEffect, useMemo, useState } from "react";

import {
  buildGuardianApprovalRunSections,
  fetchGuardianApprovalInboxSnapshot,
  type GuardianApprovalInboxContext,
  type GuardianApprovalInboxSnapshot,
} from "@/features/chat/api/approvalInbox";
import { useAgentRuns } from "@/features/chat/hooks/useAgentRuns";

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
  const {
    data: agentRuns,
    loading: agentRunsLoading,
    capabilityState: agentRunsCapabilityState,
  } = useAgentRuns(threadId ?? null);
  const [baseSnapshot, setBaseSnapshot] =
    useState<GuardianApprovalInboxSnapshot | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const snapshot = useMemo(() => {
    if (!baseSnapshot) return null;
    const runSections = buildGuardianApprovalRunSections(
      threadId != null && agentRunsCapabilityState !== "unavailable"
        ? agentRuns
        : null,
      baseSnapshot.awaitingApprovals
    );
    return {
      ...baseSnapshot,
      awaitingApprovals: runSections.awaitingApprovals,
      blockedActions: runSections.blockedActions,
      escalatedItems: runSections.escalatedItems,
      clarificationNeeded: runSections.clarificationNeeded,
    };
  }, [agentRuns, agentRunsCapabilityState, baseSnapshot, threadId]);

  const reload = useCallback(async () => {
    setLoading(true);
    setError(null);

    try {
      const nextSnapshot = await fetchGuardianApprovalInboxSnapshot({ threadId });
      setBaseSnapshot(nextSnapshot);
      setHasLoaded(true);
      setError(
        nextSnapshot.warnings.length > 0
          ? nextSnapshot.warnings.join(" ")
          : null
      );
    } catch (nextError) {
      setBaseSnapshot(null);
      setHasLoaded(true);
      setError(getErrorMessage(nextError));
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    void reload();
  }, [reload]);

  const combinedLoading =
    loading || (threadId != null && agentRunsLoading && !hasLoaded);

  return {
    error,
    hasLoaded,
    loading: combinedLoading,
    reload,
    snapshot,
  };
}

export default useGuardianApprovalInbox;
