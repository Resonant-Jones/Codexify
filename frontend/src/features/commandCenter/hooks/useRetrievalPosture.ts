import * as React from "react";

import { fetchLatestRetrievalPosture } from "@/lib/api";

import type {
  CommandCenterRetrievalPosture,
  CommandCenterRetrievalPostureResponse,
} from "@/features/commandCenter/types";

type UseRetrievalPostureResult = {
  error: string | null;
  loading: boolean;
  retrievalPosture: CommandCenterRetrievalPosture | null;
  status: "ok" | "empty" | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asString(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || null;
  }
  return null;
}

function asBool(value: unknown): boolean | null {
  if (typeof value === "boolean") return value;
  return null;
}

function asStringOrNull(value: unknown): string | null {
  if (value === null || value === undefined) return null;
  return asString(value);
}

function normalizeRetrievalPosture(
  raw: Record<string, unknown> | null
): CommandCenterRetrievalPosture | null {
  if (!raw) return null;

  const posture = raw.retrieval_posture;
  if (!posture || typeof posture !== "object") return null;
  const record = posture as Record<string, unknown>;

  const source_mode = asString(record.source_mode);
  if (!source_mode) return null;

  const boundary_label = asStringOrNull(record.boundary_label);
  const retrieval_override_mode = asStringOrNull(record.retrieval_override_mode);
  const widen_reason = asStringOrNull(record.widen_reason) ?? "none";
  const conversation_only = asBool(record.conversation_only) ?? source_mode === "conversation";

  return {
    source_mode,
    boundary_label: boundary_label ?? "unknown",
    retrieval_override_mode,
    widen_reason,
    conversation_only,
  };
}

function parseStatus(value: unknown): "ok" | "empty" | null {
  if (value === "ok" || value === "empty") return value;
  return null;
}

function formatError(error: unknown): string {
  const candidate = error as any;
  const detail =
    candidate?.response?.data?.detail ??
    candidate?.response?.data?.error ??
    candidate?.message ??
    "Failed to load retrieval posture";
  return String(detail);
}

export default function useRetrievalPosture(
  threadId: number | null
): UseRetrievalPostureResult {
  const [state, setState] = React.useState<UseRetrievalPostureResult>({
    error: null,
    loading: false,
    retrievalPosture: null,
    status: null,
  });

  React.useEffect(() => {
    let cancelled = false;

    if (threadId === null) {
      setState({
        error: null,
        loading: false,
        retrievalPosture: null,
        status: null,
      });
      return;
    }

    setState({
      error: null,
      loading: true,
      retrievalPosture: null,
      status: null,
    });

    void fetchLatestRetrievalPosture(threadId)
      .then((raw) => {
        if (cancelled) return;
        const record = asRecord(raw);
        const posture = normalizeRetrievalPosture(record);
        const status = parseStatus(record?.status);
        setState({
          error: null,
          loading: false,
          retrievalPosture: posture,
          status: status ?? null,
        });
      })
      .catch((error: any) => {
        if (cancelled) return;
        setState({
          error: formatError(error),
          loading: false,
          retrievalPosture: null,
          status: null,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [threadId]);

  return state;
}
