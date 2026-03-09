import { useCallback, useEffect, useMemo, useState } from "react";

import { useLiveEvents, type LiveEvent } from "@/hooks/useLiveEvents";
import {
  approveGuardianThreadApproval,
  denyGuardianThreadApproval,
  fetchGuardianThreadApprovalSnapshot,
  type GuardianThreadApprovalContext,
  type GuardianThreadIntervention,
} from "@/features/chat/api/threadApprovals";

export type UseGuardianThreadApprovalRailResult = {
  approve: () => Promise<boolean>;
  canSubmitDecision: boolean;
  deny: () => Promise<boolean>;
  error: string | null;
  hasLoaded: boolean;
  intervention: GuardianThreadIntervention | null;
  loading: boolean;
  notice: string | null;
  reload: () => Promise<void>;
  submittingAction: "approve" | "deny" | null;
  visible: boolean;
};

export type GuardianThreadApprovalRailContext = GuardianThreadApprovalContext & {
  reloadSignal?: number;
};

function getErrorMessage(error: unknown, fallback: string): string {
  if (
    error &&
    typeof error === "object" &&
    "response" in error &&
    error.response &&
    typeof error.response === "object" &&
    "data" in error.response
  ) {
    const response = error.response as {
      data?: { detail?: unknown; error?: unknown };
    };
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

  return fallback;
}

function eventMatchesThread(event: LiveEvent, threadId: number): boolean {
  const payload = (event.data as any)?.data ?? event.data;
  const eventThreadId = Number(
    payload?.thread_id ??
      payload?.threadId ??
      payload?.run?.thread_id ??
      payload?.run?.threadId
  );
  if (!Number.isFinite(eventThreadId)) return true;
  return eventThreadId === threadId;
}

export function useGuardianThreadApprovalRail(
  context: GuardianThreadApprovalRailContext = {}
): UseGuardianThreadApprovalRailResult {
  const { reloadSignal, threadId } = context;
  const [intervention, setIntervention] =
    useState<GuardianThreadIntervention | null>(null);
  const [loading, setLoading] = useState(true);
  const [hasLoaded, setHasLoaded] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const [submittingAction, setSubmittingAction] =
    useState<"approve" | "deny" | null>(null);
  const { subscribe } = useLiveEvents({ passive: true });

  const reload = useCallback(async () => {
    if (typeof threadId !== "number") {
      setIntervention(null);
      setLoading(false);
      setHasLoaded(true);
      setError(null);
      setNotice(null);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const snapshot = await fetchGuardianThreadApprovalSnapshot({ threadId });
      setIntervention(snapshot.intervention);
      setHasLoaded(true);
      setNotice(snapshot.warnings.length > 0 ? snapshot.warnings.join(" ") : null);
    } catch (nextError) {
      setIntervention(null);
      setHasLoaded(true);
      setError(
        getErrorMessage(
          nextError,
          "Failed to load thread intervention state."
        )
      );
    } finally {
      setLoading(false);
    }
  }, [threadId]);

  useEffect(() => {
    void reload();
  }, [reload, reloadSignal]);

  useEffect(() => {
    if (typeof threadId !== "number") return;

    const onRelevantEvent = (event: LiveEvent) => {
      if (!eventMatchesThread(event, threadId)) return;
      void reload();
    };

    const unsubscribes = [
      subscribe("browser.approval.requested", onRelevantEvent),
      subscribe("browser.approval.decided", onRelevantEvent),
      subscribe("run.blocked", onRelevantEvent),
      subscribe("run.failed", onRelevantEvent),
      subscribe("run.completed", onRelevantEvent),
      subscribe("task.failed", onRelevantEvent),
      subscribe("task.completed", onRelevantEvent),
      subscribe("task.cancelled", onRelevantEvent),
      subscribe("message.created", onRelevantEvent),
    ];

    return () => {
      for (const unsubscribe of unsubscribes) {
        unsubscribe();
      }
    };
  }, [reload, subscribe, threadId]);

  const canSubmitDecision = useMemo(
    () =>
      Boolean(
        intervention?.decision.supported &&
          typeof intervention.decision.approvalId === "number"
      ),
    [intervention]
  );

  const approve = useCallback(async (): Promise<boolean> => {
    if (!intervention) return false;
    if (!canSubmitDecision || intervention.decision.approvalId == null) {
      setError(
        "Direct approve/deny is unavailable for this thread intervention."
      );
      return false;
    }

    setSubmittingAction("approve");
    setError(null);
    setNotice(null);

    try {
      await approveGuardianThreadApproval({
        approvalId: intervention.decision.approvalId,
        reason: `Approved from thread ${intervention.threadId} approval rail.`,
      });
      setNotice("Approval submitted.");
      await reload();
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to submit approval."));
      return false;
    } finally {
      setSubmittingAction(null);
    }
  }, [canSubmitDecision, intervention, reload]);

  const deny = useCallback(async (): Promise<boolean> => {
    if (!intervention) return false;
    if (!canSubmitDecision || intervention.decision.approvalId == null) {
      setError(
        "Direct approve/deny is unavailable for this thread intervention."
      );
      return false;
    }

    setSubmittingAction("deny");
    setError(null);
    setNotice(null);

    try {
      await denyGuardianThreadApproval({
        approvalId: intervention.decision.approvalId,
        reason: `Denied from thread ${intervention.threadId} approval rail.`,
      });
      setNotice("Denial submitted.");
      await reload();
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to submit denial."));
      return false;
    } finally {
      setSubmittingAction(null);
    }
  }, [canSubmitDecision, intervention, reload]);

  return {
    approve,
    canSubmitDecision,
    deny,
    error,
    hasLoaded,
    intervention,
    loading,
    notice,
    reload,
    submittingAction,
    visible: intervention != null,
  };
}

export default useGuardianThreadApprovalRail;
