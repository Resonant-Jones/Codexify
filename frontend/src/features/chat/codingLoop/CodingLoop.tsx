import { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, CircleDashed, Loader2 } from "lucide-react";

import type { LiveEvent } from "@/hooks/useLiveEvents";
import {
  fetchCodingLoopRun,
  fetchCodingLoopRuns,
  type CodingLoopResult,
  type CodingLoopRun,
} from "@/lib/api";
import { cn } from "@/lib/utils";

export type CodingLoopExecutionMode = "chat" | "coding";

export type CodingLoopDispatchFailure = {
  id: string;
  sourceMessageId: number | null;
  message: string;
};

type CodingLoopStatus =
  | "queued"
  | "running"
  | "succeeded"
  | "failed"
  | "canceled"
  | "escalated"
  | "unknown";

type CodingLoopEventSubscribe = (
  eventType: string,
  handler: (event: LiveEvent) => void
) => () => void;

const CODING_EVENT_TYPES = [
  "created",
  "task.created",
  "task.updated",
  "task.running",
  "task.progress",
  "task.completed",
  "task.failed",
  "task.cancelled",
] as const;

const TERMINAL_STATUSES = new Set([
  "succeeded",
  "success",
  "completed",
  "failed",
  "failed_retryable",
  "failed_fatal",
  "canceled",
  "cancelled",
  "escalated",
]);

function unwrapEventPayload(event: LiveEvent): Record<string, unknown> {
  const candidate = event.payload ?? event.data;
  if (!candidate || typeof candidate !== "object") return {};
  const outer = candidate as Record<string, unknown>;
  const nested = outer.data;
  return nested && typeof nested === "object"
    ? (nested as Record<string, unknown>)
    : outer;
}

function eventRunId(event: LiveEvent, payload: Record<string, unknown>): string | null {
  const run = payload.run;
  const runRecord = run && typeof run === "object" ? (run as Record<string, unknown>) : null;
  const value = payload.run_id ?? payload.runId ?? runRecord?.run_id ?? event.entity_id;
  const normalized = String(value ?? "").trim();
  return normalized || null;
}

function eventThreadId(
  event: LiveEvent,
  payload: Record<string, unknown>
): number | null {
  const run = payload.run;
  const runRecord = run && typeof run === "object" ? (run as Record<string, unknown>) : null;
  const raw =
    payload.source_thread_id ??
    payload.thread_id ??
    payload.threadId ??
    runRecord?.source_thread_id ??
    runRecord?.thread_id ??
    event.thread_id;
  const parsed = Number(raw);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : null;
}

function normalizeStatus(raw: unknown): CodingLoopStatus {
  const status = String(raw ?? "").trim().toLowerCase();
  if (status === "queued" || status === "dispatching") return "queued";
  if (status === "running" || status === "active" || status === "progress") {
    return "running";
  }
  if (["succeeded", "success", "completed"].includes(status)) return "succeeded";
  if (["failed", "failed_retryable", "failed_fatal"].includes(status)) {
    return "failed";
  }
  if (["canceled", "cancelled"].includes(status)) return "canceled";
  if (status === "escalated") return "escalated";
  return "unknown";
}

function statusFromEventType(eventType: string): string | null {
  if (eventType === "task.running") return "running";
  if (eventType === "task.completed") return "completed";
  if (eventType === "task.failed") return "failed";
  if (eventType === "task.cancelled") return "cancelled";
  return null;
}

function isTerminal(run: CodingLoopRun): boolean {
  const status = String(run.status ?? "").trim().toLowerCase();
  return TERMINAL_STATUSES.has(status) || Boolean(run.ended_at);
}

function mergeRun(existing: CodingLoopRun | undefined, incoming: CodingLoopRun): CodingLoopRun {
  if (!existing) return incoming;
  return {
    ...existing,
    ...incoming,
    result: incoming.result ?? existing.result,
    error: incoming.error ?? existing.error,
  };
}

function errorMessage(error: unknown): string {
  const responseData = (error as { response?: { data?: unknown } } | null)?.response?.data;
  if (responseData && typeof responseData === "object") {
    const detail = (responseData as Record<string, unknown>).detail;
    if (typeof detail === "string" && detail.trim()) return detail;
  }
  if (error instanceof Error && error.message.trim()) return error.message;
  return "Guardian could not refresh Coding Loop state.";
}

export function useCodingLoopRuns(
  threadId: number | null,
  options: {
    enabled?: boolean;
    subscribe?: CodingLoopEventSubscribe;
  } = {}
) {
  const enabled = options.enabled ?? true;
  const subscribe = options.subscribe;
  const [runs, setRuns] = useState<CodingLoopRun[]>([]);
  const [dispatchErrors, setDispatchErrors] = useState<CodingLoopDispatchFailure[]>([]);
  const runsRef = useRef<CodingLoopRun[]>([]);
  const pollTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const pollNowRef = useRef<(() => void) | null>(null);
  const pollDelayRef = useRef(2000);

  useEffect(() => {
    runsRef.current = runs;
  }, [runs]);

  const mergeRuns = useCallback((incoming: CodingLoopRun[]) => {
    setRuns((current) => {
      const byId = new Map(current.map((run) => [run.run_id, run]));
      for (const run of incoming) {
        if (run?.run_id) byId.set(run.run_id, mergeRun(byId.get(run.run_id), run));
      }
      const next = Array.from(byId.values()).sort((a, b) =>
        String(a.created_at ?? "").localeCompare(String(b.created_at ?? ""))
      );
      const changed = JSON.stringify(next) !== JSON.stringify(current);
      runsRef.current = next;
      return changed ? next : current;
    });
  }, []);

  const refresh = useCallback(async () => {
    if (!enabled || threadId == null) {
      setRuns([]);
      return;
    }
    const remoteRuns = await fetchCodingLoopRuns(threadId);
    mergeRuns(remoteRuns);
  }, [enabled, mergeRuns, threadId]);

  const mergeEvent = useCallback(
    (event: LiveEvent) => {
      const payload = unwrapEventPayload(event);
      const runId = eventRunId(event, payload);
      if (!runId) return;
      const knownRun = runsRef.current.find((run) => run.run_id === runId);
      const eventThread = eventThreadId(event, payload);
      if (eventThread !== null && eventThread !== threadId) return;
      if (eventThread === null && !knownRun) return;

      const result = payload.result;
      const runPayload = payload.run;
      const runRecord = runPayload && typeof runPayload === "object"
        ? (runPayload as Record<string, unknown>)
        : {};
      const observedStatus =
        payload.status ??
        event.status ??
        runRecord.status ??
        statusFromEventType(event.type) ??
        knownRun?.status;
      mergeRuns([
        {
          ...(knownRun ?? { run_id: runId }),
          ...runRecord,
          run_id: runId,
          thread_id: threadId,
          source_thread_id:
            Number(payload.source_thread_id ?? payload.thread_id ?? threadId) || threadId,
          source_message_id:
            Number(payload.source_message_id) > 0
              ? Number(payload.source_message_id)
              : knownRun?.source_message_id ?? null,
          status: String(observedStatus ?? "").trim() || knownRun?.status,
          result:
            result && typeof result === "object"
              ? (result as CodingLoopResult)
              : knownRun?.result ?? null,
          error:
            typeof payload.error === "string"
              ? payload.error
              : knownRun?.error ?? null,
        },
      ]);
    },
    [mergeRuns, threadId]
  );

  useEffect(() => {
    runsRef.current = [];
    setRuns([]);
    setDispatchErrors([]);
    pollDelayRef.current = 2000;
    if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
    pollTimerRef.current = null;
    if (!enabled || threadId == null) return;

    let disposed = false;
    const poll = async () => {
      if (disposed) return;
      pollTimerRef.current = null;
      try {
        await refresh();
        const activeRunIds = runsRef.current
          .filter((run) => !isTerminal(run))
          .map((run) => run.run_id);
        const snapshots = await Promise.all(
          activeRunIds.map(async (runId) => {
            try {
              return await fetchCodingLoopRun(runId);
            } catch {
              return null;
            }
          })
        );
        mergeRuns(
          snapshots.filter((snapshot): snapshot is CodingLoopRun => snapshot !== null)
        );
        pollDelayRef.current = 2000;
      } catch {
        pollDelayRef.current = Math.min(pollDelayRef.current * 2, 10000);
      }
      if (disposed) return;
      if (runsRef.current.some((run) => !isTerminal(run))) {
        pollTimerRef.current = setTimeout(poll, pollDelayRef.current);
      }
    };
    pollNowRef.current = () => {
      if (!disposed && pollTimerRef.current === null) void poll();
    };

    const unsubscribe = subscribe
      ? CODING_EVENT_TYPES.map((eventType) => subscribe(eventType, mergeEvent))
      : [];
    void poll();
    return () => {
      disposed = true;
      unsubscribe.forEach((off) => off());
      if (pollTimerRef.current) clearTimeout(pollTimerRef.current);
      pollTimerRef.current = null;
      pollNowRef.current = null;
    };
  }, [enabled, mergeEvent, refresh, subscribe, threadId]);

  const registerAcceptedRun = useCallback(
    (run: CodingLoopRun) => {
      if (threadId == null || run.source_thread_id == null || run.source_thread_id === threadId) {
        mergeRuns([run]);
        pollNowRef.current?.();
      }
    },
    [mergeRuns, threadId]
  );

  const registerDispatchFailure = useCallback(
    (failure: Omit<CodingLoopDispatchFailure, "id">) => {
      setDispatchErrors((current) => [
        ...current,
        { ...failure, id: `dispatch-failure-${Date.now()}` },
      ]);
    },
    []
  );

  return {
    dispatchErrors,
    refresh,
    registerAcceptedRun,
    registerDispatchFailure,
    runs,
  };
}

function statusLabel(run: CodingLoopRun): { label: string; status: CodingLoopStatus } {
  const status = normalizeStatus(run.status ?? run.result?.status);
  switch (status) {
    case "queued":
      return { label: "Accepted — queued", status };
    case "running":
      return { label: "Active — running", status };
    case "succeeded":
      return { label: "Completed", status };
    case "failed":
      return { label: "Failed", status };
    case "canceled":
      return { label: "Canceled", status };
    case "escalated":
      return { label: "Escalated", status };
    default:
      return { label: String(run.status || "Unknown"), status };
  }
}

function resultError(result: CodingLoopResult | null | undefined): string | null {
  if (!result) return null;
  if (typeof result.error_message === "string" && result.error_message.trim()) {
    return result.error_message;
  }
  return null;
}

function CodingLoopRunCard({ run }: { run: CodingLoopRun }) {
  const state = statusLabel(run);
  const result = run.result;
  const failure = run.error || resultError(result);
  const Icon =
    state.status === "succeeded"
      ? CheckCircle2
      : state.status === "failed" || state.status === "canceled"
        ? AlertTriangle
        : state.status === "running"
          ? Loader2
          : CircleDashed;
  const filesChanged = result?.files_changed_count ?? 0;
  const artifactNames = Array.isArray(result?.artifacts)
    ? result.artifacts
        .map((artifact) => artifact.name || artifact.kind)
        .filter(Boolean)
        .join(", ")
    : "";

  return (
    <article
      data-testid="coding-loop-run-card"
      data-run-status={state.status}
      className="rounded-md border px-3 py-2 text-xs"
      style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)" }}
    >
      <div className="flex items-start gap-2">
        <Icon
          className={cn("mt-0.5 h-3.5 w-3.5 shrink-0", state.status === "running" && "animate-spin")}
          style={{ color: "var(--accent-strong)" }}
        />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
            <span className="font-medium">Coding Loop</span>
            <span style={{ color: "var(--muted)" }}>{state.label}</span>
          </div>
          <div className="mt-1" style={{ color: "var(--muted)" }}>
            Run {run.run_id}
            {run.source_message_id ? ` · source message ${run.source_message_id}` : ""}
            {run.adapter_kind ? ` · ${run.adapter_kind}` : ""}
          </div>
          {result?.summary ? <p className="mt-2">{result.summary}</p> : null}
          {failure ? (
            <p className="mt-2" style={{ color: "var(--danger, #c2410c)" }}>
              {failure}
            </p>
          ) : null}
          {filesChanged > 0 || result?.final_validation_status || result?.commit_hash || artifactNames ? (
            <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1" style={{ color: "var(--muted)" }}>
              {filesChanged > 0 ? <span>{filesChanged} file(s) changed</span> : null}
              {result?.final_validation_status ? (
                <span>Validation: {result.final_validation_status}</span>
              ) : null}
              {result?.commit_hash ? <span>Commit: {result.commit_hash}</span> : null}
              {artifactNames ? <span>Artifacts: {artifactNames}</span> : null}
            </div>
          ) : null}
        </div>
      </div>
    </article>
  );
}

export function CodingLoopCards({
  dispatchErrors,
  runs,
}: {
  dispatchErrors: CodingLoopDispatchFailure[];
  runs: CodingLoopRun[];
}) {
  if (runs.length === 0 && dispatchErrors.length === 0) return null;
  return (
    <section
      data-testid="coding-loop-cards"
      aria-label="Coding Loop runs"
      className="mt-2 space-y-2"
    >
      {dispatchErrors.map((failure) => (
        <article
          key={failure.id}
          data-testid="coding-loop-dispatch-failure"
          className="rounded-md border px-3 py-2 text-xs"
          style={{ borderColor: "var(--panel-border)", background: "var(--panel-bg)" }}
        >
          <div className="font-medium">Coding Loop was not accepted</div>
          <p className="mt-1" style={{ color: "var(--muted)" }}>
            The authored message was saved, but Guardian did not accept execution. {failure.message}
          </p>
          {failure.sourceMessageId ? (
            <p className="mt-1" style={{ color: "var(--muted)" }}>
              Source message {failure.sourceMessageId} remains in the conversation.
            </p>
          ) : null}
        </article>
      ))}
      {runs.map((run) => <CodingLoopRunCard key={run.run_id} run={run} />)}
    </section>
  );
}
