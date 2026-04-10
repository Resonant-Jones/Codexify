import * as React from "react";

import { fetchLatestRagTrace } from "@/lib/api";

import type {
  CommandCenterRagTraceItem,
  CommandCenterRagTracePayload,
  CommandCenterRagTraceUnavailableReason,
  CommandCenterRun,
} from "@/features/commandCenter/types";

type UseRagTraceResult = {
  error: string | null;
  loading: boolean;
  resolvedThreadId: number | null;
  rawTrace: Record<string, unknown> | null;
  trace: CommandCenterRagTracePayload | null;
  unavailable: boolean;
  unavailableReason: CommandCenterRagTraceUnavailableReason | null;
};

function asRecord(value: unknown): Record<string, unknown> | null {
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return null;
  }
  return value as Record<string, unknown>;
}

function asArray(...values: unknown[]): unknown[] | null {
  for (const value of values) {
    if (Array.isArray(value)) return value;
  }
  return null;
}

function firstString(...values: unknown[]): string | null {
  for (const value of values) {
    if (typeof value !== "string") continue;
    const trimmed = value.trim();
    if (trimmed) return trimmed;
  }
  return null;
}

function toFiniteNumber(value: unknown): number | null {
  if (typeof value === "number" && Number.isFinite(value)) {
    return value;
  }
  if (typeof value === "string") {
    const trimmed = value.trim();
    if (!trimmed) return null;
    const parsed = Number(trimmed);
    if (Number.isFinite(parsed)) return parsed;
  }
  return null;
}

function firstNumber(...values: unknown[]): number | null {
  for (const value of values) {
    const parsed = toFiniteNumber(value);
    if (parsed != null) return parsed;
  }
  return null;
}

function parseThreadIdFromTraceUrl(traceUrl: string | null | undefined): number | null {
  if (typeof traceUrl !== "string") return null;
  const match = traceUrl.match(/rag-trace\/(\d+)\/latest/i);
  if (!match?.[1]) return null;
  const parsed = Number(match[1]);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatError(error: unknown): string {
  const candidate = error as any;
  const detail =
    candidate?.response?.data?.detail ??
    candidate?.response?.data?.error ??
    candidate?.message ??
    "Failed to load RAG trace";
  return String(detail);
}

function normalizeText(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed || null;
  }
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return null;
}

function normalizeTraceItem(
  entry: unknown,
  index: number,
  prefix: "semantic" | "memory"
): CommandCenterRagTraceItem | null {
  const primitiveText = normalizeText(entry);
  if (primitiveText) {
    return {
      depthUsed: null,
      id: `${prefix}-${index + 1}`,
      origin: null,
      raw: null,
      score: null,
      silo: null,
      source: null,
      text: primitiveText,
      threadId: null,
      timestamp: null,
    };
  }

  const record = asRecord(entry);
  if (!record) return null;

  const metadata = asRecord(record.metadata) ?? asRecord(record.meta);
  const text = firstString(
    record.text,
    record.snippet,
    record.content,
    record.body,
    record.value,
    record.title
  );
  if (!text) return null;

  return {
    depthUsed: firstString(
      record.depth_used,
      record.depthUsed,
      metadata?.depth_used,
      metadata?.depthUsed
    ),
    id:
      firstString(
        record.id,
        record.node_id,
        record.nodeId,
        record.message_id,
        record.messageId
      ) ?? `${prefix}-${index + 1}`,
    origin: firstString(
      record.origin,
      metadata?.origin,
      record.kind,
      record.type
    ),
    raw: record,
    score: firstNumber(record.score, record.similarity, metadata?.score),
    silo: firstString(record.silo, metadata?.silo),
    source: firstString(
      record.source,
      metadata?.source,
      record.title,
      record.filename,
      metadata?.filename
    ),
    text,
    threadId: firstString(
      record.thread_id,
      record.threadId,
      metadata?.thread_id,
      metadata?.threadId
    ),
    timestamp: firstString(
      record.timestamp,
      record.created_at,
      record.createdAt,
      record.updated_at,
      record.updatedAt,
      metadata?.timestamp
    ),
  };
}

function sortByScore(items: CommandCenterRagTraceItem[]): CommandCenterRagTraceItem[] {
  return [...items].sort((left, right) => {
    if (left.score == null && right.score == null) return 0;
    if (left.score == null) return 1;
    if (right.score == null) return -1;
    return right.score - left.score;
  });
}

function normalizeTracePayload(
  payload: unknown,
  resolvedThreadId: number
): CommandCenterRagTracePayload | null {
  const trace = asRecord(payload);
  if (!trace) return null;

  const semantic = sortByScore(
    (asArray(
      trace.semantic,
      trace.semantic_results,
      trace.semanticResults,
      trace.documents
    ) ?? [])
      .map((entry, index) => normalizeTraceItem(entry, index, "semantic"))
      .filter((entry): entry is CommandCenterRagTraceItem => entry != null)
  );
  const memory = sortByScore(
    (asArray(
      trace.memory,
      trace.memory_results,
      trace.memoryResults,
      trace.graph
    ) ?? [])
      .map((entry, index) => normalizeTraceItem(entry, index, "memory"))
      .filter((entry): entry is CommandCenterRagTraceItem => entry != null)
  );

  if (semantic.length === 0 && memory.length === 0) {
    return null;
  }

  return {
    memory,
    resolvedThreadId,
    semantic,
  };
}

function resolveThreadId(run: CommandCenterRun | null): number | null {
  if (!run) return null;
  return firstNumber(run.threadId, parseThreadIdFromTraceUrl(run.traceUrl));
}

export default function useRagTrace(
  run: CommandCenterRun | null
): UseRagTraceResult {
  const [state, setState] = React.useState<UseRagTraceResult>({
    error: null,
    loading: false,
    resolvedThreadId: null,
    rawTrace: null,
    trace: null,
    unavailable: true,
    unavailableReason: "no_run",
  });

  React.useEffect(() => {
    let cancelled = false;

    if (!run) {
      setState({
        error: null,
        loading: false,
        resolvedThreadId: null,
        rawTrace: null,
        trace: null,
        unavailable: true,
        unavailableReason: "no_run",
      });
      return;
    }

    const resolvedThreadId = resolveThreadId(run);
    if (resolvedThreadId == null) {
      setState({
        error: null,
        loading: false,
        resolvedThreadId: null,
        rawTrace: null,
        trace: null,
        unavailable: true,
        unavailableReason: "no_thread",
      });
      return;
    }

    setState({
      error: null,
      loading: true,
      resolvedThreadId,
      rawTrace: null,
      trace: null,
      unavailable: false,
      unavailableReason: null,
    });

    void fetchLatestRagTrace(resolvedThreadId)
      .then((payload) => {
        if (cancelled) return;
        const rawTrace = asRecord(payload);
        if (!rawTrace) {
          setState({
            error: null,
            loading: false,
            resolvedThreadId,
            rawTrace: null,
            trace: null,
            unavailable: true,
            unavailableReason: "no_trace",
          });
          return;
        }
        const normalized = normalizeTracePayload(rawTrace, resolvedThreadId);
        setState({
          error: null,
          loading: false,
          resolvedThreadId,
          rawTrace,
          trace: normalized,
          unavailable: false,
          unavailableReason: null,
        });
      })
      .catch((error: any) => {
        if (cancelled) return;
        if (Number(error?.response?.status ?? 0) === 404) {
          setState({
            error: null,
            loading: false,
            resolvedThreadId,
            rawTrace: null,
            trace: null,
            unavailable: true,
            unavailableReason: "no_trace",
          });
          return;
        }
        setState({
          error: formatError(error),
          loading: false,
          resolvedThreadId,
          rawTrace: null,
          trace: null,
          unavailable: false,
          unavailableReason: null,
        });
      });

    return () => {
      cancelled = true;
    };
  }, [run]);

  return state;
}
