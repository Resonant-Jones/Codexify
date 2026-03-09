import { useCallback, useEffect, useState } from "react";

import {
  acceptImprintProposal,
  fetchImprintReviewStatus,
  rejectImprintProposal,
  requestImprintProposalForReview,
  type AcceptedImprintReview,
  type ImprintProposal,
  type ImprintReviewContext,
  type ImprintReviewStatus,
  type RejectedImprintReview,
} from "@/features/settings/api/imprint";

export type ImprintReviewOutcome =
  | {
      kind: "accepted";
      message: string;
      accepted: AcceptedImprintReview;
    }
  | {
      kind: "rejected";
      message: string;
      rejected: RejectedImprintReview;
    };

export type UseImprintReviewResult = {
  accepting: boolean;
  error: string | null;
  loading: boolean;
  outcome: ImprintReviewOutcome | null;
  proposal: ImprintProposal | null;
  refresh: () => Promise<void>;
  rejecting: boolean;
  rejectProposal: () => Promise<boolean>;
  reviewStatus: ImprintReviewStatus | null;
  acceptProposal: () => Promise<boolean>;
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

  return fallback;
}

export function useImprintReview(
  context: ImprintReviewContext = {}
): UseImprintReviewResult {
  const { projectId, threadId } = context;
  const [reviewStatus, setReviewStatus] = useState<ImprintReviewStatus | null>(
    null
  );
  const [proposal, setProposal] = useState<ImprintProposal | null>(null);
  const [loading, setLoading] = useState(true);
  const [accepting, setAccepting] = useState(false);
  const [rejecting, setRejecting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [outcome, setOutcome] = useState<ImprintReviewOutcome | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);

    const [statusResult, proposalResult] = await Promise.allSettled([
      fetchImprintReviewStatus({ projectId, threadId }),
      requestImprintProposalForReview({ projectId, threadId }),
    ]);

    if (statusResult.status === "fulfilled") {
      setReviewStatus(statusResult.value);
    } else {
      setReviewStatus(null);
      setError(
        getErrorMessage(statusResult.reason, "Failed to load imprint status.")
      );
    }

    if (proposalResult.status === "fulfilled") {
      setProposal(proposalResult.value);
    } else if (statusResult.status === "fulfilled") {
      setProposal(null);
      setError(
        getErrorMessage(
          proposalResult.reason,
          "Failed to load imprint proposal."
        )
      );
    }

    setLoading(false);
  }, [projectId, threadId]);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const acceptProposal = useCallback(async () => {
    const imprintId = proposal?.imprintDraft?.id;
    if (!imprintId) {
      setError("No pending proposal is available to accept.");
      return false;
    }

    setAccepting(true);
    setError(null);

    try {
      const accepted = await acceptImprintProposal({
        imprintId,
        projectId,
        threadId,
      });
      setOutcome({
        kind: "accepted",
        message: "Proposal accepted",
        accepted,
      });
      setProposal(null);
      const nextStatus = await fetchImprintReviewStatus({ projectId, threadId });
      setReviewStatus(nextStatus);
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to accept imprint."));
      return false;
    } finally {
      setAccepting(false);
    }
  }, [projectId, proposal?.imprintDraft?.id, threadId]);

  const rejectProposal = useCallback(async () => {
    const imprintId = proposal?.imprintDraft?.id;
    if (!imprintId) {
      setError("No pending proposal is available to reject.");
      return false;
    }

    setRejecting(true);
    setError(null);

    try {
      const rejected = await rejectImprintProposal({ imprintId });
      setOutcome({
        kind: "rejected",
        message: "Proposal rejected",
        rejected,
      });
      setProposal(null);
      const nextStatus = await fetchImprintReviewStatus({ projectId, threadId });
      setReviewStatus(nextStatus);
      return true;
    } catch (nextError) {
      setError(getErrorMessage(nextError, "Failed to reject imprint."));
      return false;
    } finally {
      setRejecting(false);
    }
  }, [projectId, proposal?.imprintDraft?.id, threadId]);

  return {
    accepting,
    error,
    loading,
    outcome,
    proposal,
    refresh,
    rejectProposal,
    rejecting,
    reviewStatus,
    acceptProposal,
  };
}

export default useImprintReview;
