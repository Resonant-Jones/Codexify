import * as React from "react";

import api from "@/lib/api";

import type {
  CommandCenterCodingWorkOrder,
  CommandCenterWorkOrderDetailResponse,
  CommandCenterWorkOrderCreateInput,
  CommandCenterWorkOrderListResponse,
  CommandCenterWorkOrderMutationResponse,
  CommandCenterWorkOrderStatus,
} from "@/features/commandCenter/types";

type UseCodingWorkOrdersOptions = {
  campaignId?: string | null;
  enabled?: boolean;
  limit?: number;
  offset?: number;
  status?: CommandCenterWorkOrderStatus | null;
};

type UseCodingWorkOrdersResult = {
  cancelWorkOrder: (
    workOrderId: string,
    reason?: string
  ) => Promise<CommandCenterCodingWorkOrder | null>;
  createWorkOrder: (
    input: CommandCenterWorkOrderCreateInput
  ) => Promise<CommandCenterCodingWorkOrder | null>;
  error: string | null;
  fetchWorkOrderDetail: (
    workOrderId: string
  ) => Promise<CommandCenterCodingWorkOrder | null>;
  items: CommandCenterCodingWorkOrder[];
  loading: boolean;
  refresh: () => Promise<void>;
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

function normalizeWorkOrderItems(
  payload: unknown
): CommandCenterCodingWorkOrder[] {
  const items = (payload as { items?: unknown } | null)?.items;
  if (!Array.isArray(items)) return [];
  return items as CommandCenterCodingWorkOrder[];
}

export default function useCodingWorkOrders(
  options: UseCodingWorkOrdersOptions = {}
): UseCodingWorkOrdersResult {
  const {
    campaignId = null,
    enabled = true,
    limit = 50,
    offset = 0,
    status = null,
  } = options;
  const mountedRef = React.useRef(true);
  const [items, setItems] = React.useState<CommandCenterCodingWorkOrder[]>([]);
  const [loading, setLoading] = React.useState<boolean>(enabled);
  const [error, setError] = React.useState<string | null>(null);

  React.useEffect(() => {
    return () => {
      mountedRef.current = false;
    };
  }, []);

  const refresh = React.useCallback(async () => {
    if (!enabled) {
      setItems([]);
      setError(null);
      setLoading(false);
      return;
    }

    try {
      setLoading(true);
      const response = await api.get<CommandCenterWorkOrderListResponse>(
        "/api/coding/work-orders",
        {
          params: {
            campaign_id: campaignId || undefined,
            limit,
            offset,
            status: status || undefined,
          },
        }
      );
      if (!mountedRef.current) return;
      setItems(normalizeWorkOrderItems(response.data));
      setError(null);
    } catch (requestError) {
      if (!mountedRef.current) return;
      setItems([]);
      setError(
        toUserSafeError(
          requestError,
          "Unable to load coding work orders right now."
        )
      );
    } finally {
      if (mountedRef.current) {
        setLoading(false);
      }
    }
  }, [campaignId, enabled, limit, offset, status]);

  const createWorkOrder = React.useCallback(
    async (
      input: CommandCenterWorkOrderCreateInput
    ): Promise<CommandCenterCodingWorkOrder | null> => {
      try {
        const response = await api.post<CommandCenterWorkOrderMutationResponse>(
          "/api/coding/work-orders",
          input
        );
        await refresh();
        return response.data?.work_order ?? null;
      } catch (requestError) {
        const normalized = toUserSafeError(
          requestError,
          "Unable to create a coding work order."
        );
        setError(normalized);
        throw new Error(normalized);
      }
    },
    [refresh]
  );

  const cancelWorkOrder = React.useCallback(
    async (
      workOrderId: string,
      reason?: string
    ): Promise<CommandCenterCodingWorkOrder | null> => {
      try {
        const response = await api.post<CommandCenterWorkOrderMutationResponse>(
          `/api/coding/work-orders/${encodeURIComponent(workOrderId)}/cancel`,
          reason ? { reason } : {}
        );
        await refresh();
        return response.data?.work_order ?? null;
      } catch (requestError) {
        const normalized = toUserSafeError(
          requestError,
          "Unable to cancel this coding work order."
        );
        setError(normalized);
        throw new Error(normalized);
      }
    },
    [refresh]
  );

  const fetchWorkOrderDetail = React.useCallback(
    async (workOrderId: string): Promise<CommandCenterCodingWorkOrder | null> => {
      try {
        const response = await api.get<CommandCenterWorkOrderDetailResponse>(
          `/api/coding/work-orders/${encodeURIComponent(workOrderId)}`
        );
        return response.data?.work_order ?? null;
      } catch (requestError) {
        const normalized = toUserSafeError(
          requestError,
          "Unable to load this work-order detail."
        );
        setError(normalized);
        throw new Error(normalized);
      }
    },
    []
  );

  React.useEffect(() => {
    void refresh();
  }, [refresh]);

  return {
    cancelWorkOrder,
    createWorkOrder,
    error,
    fetchWorkOrderDetail,
    items,
    loading,
    refresh,
  };
}
