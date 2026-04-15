import * as React from "react";

import { fetchRetrievalPostureHistory } from "@/lib/api";

import type {
  CommandCenterRetrievalPosture,
  CommandCenterRetrievalPostureHistoryItem,
  CommandCenterRetrievalPostureHistoryResponse,
} from "@/features/commandCenter/types";

type UseRetrievalPostureHistoryResult = {
  error: string | null;
  items: CommandCenterRetrievalPostureHistoryItem[];
  loading: boolean;
  status: "ok" | "empty" | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const trimmed = value.trim();
  return trimmed || null;
}

function asBool(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  return null;
}

function parseStatus(
  value: unknown
): CommandCenterRetrievalPostureHistoryResponse["status"] | null {
  if (value === "ok" || value === "empty") return value;
  return null;
}

function normalizeRetrievalPosture(
  raw: Record<string, unknown> | null
): CommandCenterRetrievalPosture | null {
  if (!raw) return null;

  const source_mode = asString(raw.source_mode);
  const boundary_label = asString(raw.boundary_label);
  const widen_reason = asString(raw.widen_reason);
  if (!source_mode || !boundary_label || !widen_reason) return null;

  return {
    source_mode,
    boundary_label,
    retrieval_override_mode: asString(raw.retrieval_override_mode),
    widen_reason,
    conversation_only:
      asBool(raw.conversation_only) ?? source_mode === "conversation",
  };
}

function normalizeHistoryItems(
  rawItems: unknown
): CommandCenterRetrievalPostureHistoryItem[] {
  if (!Array.isArray(rawItems)) return [];

  const items: CommandCenterRetrievalPostureHistoryItem[] = [];
  for (const rawItem of rawItems) {
    const item = asRecord(rawItem);
    if (!item) continue;

    const task_id = asString(item.task_id);
    const created_at = asString(item.created_at);
    const retrievalPosture = normalizeRetrievalPosture(
      asRecord(item.retrieval_posture)
    );
    if (!task_id || !created_at || !retrievalPosture) continue;

    items.push({
      task_id,
      created_at,
      retrieval_posture: retrievalPosture,
    });
  }

  return items;
}

function formatError(error: unknown): string {
  const candidate = error as any;
  const detail =
    candidate?.response?.data?.detail ??
    candidate?.response?.data?.error ??
    candidate?.message ??
    "Failed to load retrieval posture history";
  return String(detail);
}

export default function useRetrievalPostureHistory(
  threadId: number | null
): UseRetrievalPostureHistoryResult {
  const [state, setState] = React.useState<UseRetrievalPostureHistoryResult>({
    error: null,
    items: [],
    loading: false,
    status: null,
  });

  React.useEffect(() => {
    let cancelled = false;

    if (threadId === null) {
      setState({
        error: null,
        items: [],
        loading: false,
        status: null,
      });
      return;
    }

    setState({
      error: null,
      items: [],
      loading: true,
      status: null,
    });

    void fetchRetrievalPostureHistory(threadId)
      .then((raw) => {
        if (cancelled) return;
        const record = asRecord(raw);
        const status = parseStatus(record?.status);
        setState({
          error: null,
          items: normalizeHistoryItems(record?.items),
          loading: false,
          status: status ?? null,
        });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          error: formatError(error),
          items: [],
          loading: false,
          status: null,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [threadId]);

  return state;
}
