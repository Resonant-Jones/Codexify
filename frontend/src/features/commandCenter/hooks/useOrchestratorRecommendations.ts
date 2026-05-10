import * as React from "react";

import api from "@/lib/api";

import type {
  CommandCenterOrchestratorNextResponse,
  CommandCenterOrchestratorRecommendation,
  CommandCenterOrchestratorSkipReason,
} from "@/features/commandCenter/types";

type UseOrchestratorRecommendationsOptions = {
  campaignId?: string | null;
  enabled?: boolean;
  limit?: number;
};

type UseOrchestratorRecommendationsResult = {
  decisionReasons: string[];
  error: string | null;
  loading: boolean;
  recommendations: CommandCenterOrchestratorRecommendation[];
  refresh: () => Promise<void>;
  skipped: CommandCenterOrchestratorSkipReason[];
};

function toUserSafeError(error: unknown, fallback: string): string {
  const detail = (error as { response?: { data?: { detail?: unknown } } } | null)?.response?.data?.detail;
  if (typeof detail === "string" && detail.trim()) {
    return detail
      .trim()
      .replace(/_/g, " ")
      .toLowerCase();
  }

  if (error instanceof Error && error.message.trim()) {
    return error.message.trim();
  }
  return fallback;
}

export default function useOrchestratorRecommendations(
  options: UseOrchestratorRecommendationsOptions = {}
): UseOrchestratorRecommendationsResult {
  const { campaignId = null, enabled = true, limit = 5 } = options;
  const mountedRef = React.useRef(true);
  const [recommendations, setRecommendations] = React.useState<
    CommandCenterOrchestratorRecommendation[]
  >([]);
  const [skipped, setSkipped] = React.useState<
    CommandCenterOrchestratorSkipReason[]
  >([]);
  const [decisionReasons, setDecisionReasons] = React.useState<string[]>([]);
  const [loading, setLoading] = React.useState<boolean>(enabled);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refresh = React.useCallback(async () => {
    if (!enabled) {
      setRecommendations([]);
      setSkipped([]);
      setDecisionReasons([]);
      setError(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await api.get<CommandCenterOrchestratorNextResponse>(
        "/api/coding/orchestrator/next",
        {
          params: {
            campaign_id: campaignId || undefined,
            limit,
          },
        }
      );
      if (!mountedRef.current) return;
      setRecommendations(
        Array.isArray(response.data?.recommendations)
          ? response.data.recommendations
          : []
      );
      setSkipped(Array.isArray(response.data?.skipped) ? response.data.skipped : []);
      setDecisionReasons(
        Array.isArray(response.data?.decision_reasons)
          ? response.data.decision_reasons
          : []
      );
      setError(null);
    } catch (requestError) {
      if (!mountedRef.current) return;
      setRecommendations([]);
      setSkipped([]);
      setDecisionReasons([]);
      setError(
        toUserSafeError(
          requestError,
          "Unable to load orchestrator recommendations right now."
        )
      );
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [campaignId, enabled, limit]);

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    decisionReasons,
    error,
    loading,
    recommendations,
    refresh,
    skipped,
  };
}
