import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GuardianEventSource } from "@/lib/guardianEventSource";
import api, { getAuthToken, getDevApiKey, readRuntimeApiKey } from "@/lib/api";
import {
  createIdleInferenceRequestState,
  isActiveInferencePhase,
  type InferenceLatencyMetric,
  type ComposerInferenceMode,
  type InferenceRequestState,
} from "@/types/inference";

type TaskLifecycleState =
  | "QUEUED"
  | "AWAITING_MODEL"
  | "AWAITING_FIRST_TOKEN"
  | "STREAMING"
  | "COMPLETED"
  | "FAILED"
  | "CANCELLED";

type StartInferenceRequestInput = {
  threadId: number;
  providerId: string | null;
  modelId: string | null;
  mode: ComposerInferenceMode;
};

function parseTaskEventPayload(event: Event): Record<string, unknown> | null {
  const message = event as MessageEvent<string>;
  const raw = typeof message.data === "string" ? message.data.trim() : "";
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return parsed && typeof parsed === "object"
      ? (parsed as Record<string, unknown>)
      : null;
  } catch {
    return null;
  }
}

function normalizeTaskLifecycleState(
  value: unknown
): TaskLifecycleState | null {
  const normalized = String(value ?? "")
    .trim()
    .toUpperCase()
    .replace(/[\s-]+/g, "_");
  switch (normalized) {
    case "QUEUED":
    case "AWAITING_MODEL":
    case "AWAITING_FIRST_TOKEN":
    case "STREAMING":
    case "COMPLETED":
    case "FAILED":
    case "CANCELLED":
      return normalized;
    default:
      return null;
  }
}

function getTaskEventThreadId(payload: Record<string, unknown> | null): number | null {
  const threadId = Number(payload?.thread_id ?? payload?.threadId ?? payload?.threadID);
  return Number.isFinite(threadId) ? threadId : null;
}

function getTaskEventTaskId(payload: Record<string, unknown> | null): string | null {
  const value = String(payload?.task_id ?? payload?.taskId ?? "").trim();
  return value.length > 0 ? value : null;
}

const TIMING_FIELD_MAPPINGS = [
  ["queuedAt", "queued_at"],
  ["awaitingModelAt", "awaiting_model_at"],
  ["awaitingFirstTokenAt", "awaiting_first_token_at"],
  ["firstTokenAt", "first_token_at"],
  ["firstOutputAt", "first_output_at"],
  ["completedAt", "completed_at"],
] as const satisfies ReadonlyArray<
  readonly [keyof Pick<
    InferenceRequestState,
    | "queuedAt"
    | "awaitingModelAt"
    | "awaitingFirstTokenAt"
    | "firstTokenAt"
    | "firstOutputAt"
    | "completedAt"
  >, string]
>;

type TimingFieldKey = (typeof TIMING_FIELD_MAPPINGS)[number][0];

function normalizeTimingStamp(value: unknown): string | null {
  if (typeof value === "string") {
    const trimmed = value.trim();
    return trimmed.length > 0 ? trimmed : null;
  }
  if (typeof value === "number" && Number.isFinite(value)) {
    const date = new Date(value);
    return Number.isFinite(date.getTime()) ? date.toISOString() : null;
  }
  return null;
}

function mergeTimingPatch(
  target: Partial<Record<TimingFieldKey, string | null>>,
  source: Record<string, unknown> | null | undefined,
  options: { overwrite?: boolean } = {}
): void {
  if (!source) return;
  const overwrite = Boolean(options.overwrite);
  for (const [stateKey, payloadKey] of TIMING_FIELD_MAPPINGS) {
    const normalized = normalizeTimingStamp(source[payloadKey] ?? source[stateKey]);
    if (normalized === null) {
      continue;
    }
    if (overwrite || target[stateKey] == null) {
      target[stateKey] = normalized;
    }
  }
}

function extractTimingPatch(
  payload: Record<string, unknown> | null
): Partial<InferenceRequestState> {
  const patch: Partial<Record<TimingFieldKey, string | null>> = {};
  const trace =
    payload?.trace && typeof payload.trace === "object" && !Array.isArray(payload.trace)
      ? (payload.trace as Record<string, unknown>)
      : null;
  mergeTimingPatch(patch, trace);
  mergeTimingPatch(patch, payload, { overwrite: true });
  return patch;
}

function parseTimestampMs(value: string | null | undefined): number | null {
  if (typeof value !== "string") return null;
  const parsed = Date.parse(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function formatLatencyDuration(milliseconds: number): string {
  if (!Number.isFinite(milliseconds) || milliseconds < 0) {
    return "0ms";
  }
  if (milliseconds < 1000) {
    return `${Math.round(milliseconds)}ms`;
  }
  const seconds = milliseconds / 1000;
  const precision = seconds < 10 ? 1 : 0;
  return `${seconds.toFixed(precision)}s`;
}

function deriveLatencyMetrics(
  state: Pick<
    InferenceRequestState,
    | "queuedAt"
    | "awaitingModelAt"
    | "awaitingFirstTokenAt"
    | "firstTokenAt"
    | "firstOutputAt"
    | "completedAt"
  >
): InferenceLatencyMetric[] {
  const queuedAtMs = parseTimestampMs(state.queuedAt);
  const awaitingModelAtMs = parseTimestampMs(state.awaitingModelAt);
  const awaitingFirstTokenAtMs = parseTimestampMs(state.awaitingFirstTokenAt);
  const firstTokenAtMs = parseTimestampMs(state.firstTokenAt);
  const firstOutputAtMs = parseTimestampMs(state.firstOutputAt);
  const completedAtMs = parseTimestampMs(state.completedAt);

  const metrics: InferenceLatencyMetric[] = [];

  if (
    queuedAtMs != null &&
    awaitingModelAtMs != null &&
    awaitingModelAtMs >= queuedAtMs
  ) {
    metrics.push({
      label: "Queued",
      value: formatLatencyDuration(awaitingModelAtMs - queuedAtMs),
    });
  }

  if (
    awaitingModelAtMs != null &&
    awaitingFirstTokenAtMs != null &&
    awaitingFirstTokenAtMs >= awaitingModelAtMs
  ) {
    metrics.push({
      label: "Warmup",
      value: formatLatencyDuration(awaitingFirstTokenAtMs - awaitingModelAtMs),
    });
  }

  const firstVisibleOutputAtMs = firstTokenAtMs ?? firstOutputAtMs;
  if (
    awaitingFirstTokenAtMs != null &&
    firstVisibleOutputAtMs != null &&
    firstVisibleOutputAtMs >= awaitingFirstTokenAtMs
  ) {
    metrics.push({
      label: firstTokenAtMs != null ? "First token" : "First output",
      value: formatLatencyDuration(firstVisibleOutputAtMs - awaitingFirstTokenAtMs),
    });
  }

  if (
    queuedAtMs != null &&
    completedAtMs != null &&
    completedAtMs >= queuedAtMs
  ) {
    metrics.push({
      label: "Total",
      value: formatLatencyDuration(completedAtMs - queuedAtMs),
    });
  }

  return metrics;
}

function buildLifecyclePatch(
  lifecycleState: Exclude<TaskLifecycleState, "COMPLETED" | "FAILED" | "CANCELLED">
): Partial<InferenceRequestState> {
  switch (lifecycleState) {
    case "QUEUED":
      return {
        phase: "sending",
        statusText: "Queued…",
        detailText: "Guardian is preparing a response.",
        errorText: null,
        isPendingCancel: false,
      };
    case "AWAITING_MODEL":
      return {
        phase: "sending",
        statusText: "Warming model…",
        detailText: "Guardian is warming the selected model.",
        errorText: null,
        isPendingCancel: false,
      };
    case "AWAITING_FIRST_TOKEN":
      return {
        phase: "sending",
        statusText: "Waiting for first token…",
        detailText: "Guardian is waiting for the first response chunk.",
        errorText: null,
        isPendingCancel: false,
      };
    case "STREAMING":
      return {
        phase: "streaming",
        statusText: "Generating…",
        detailText: "Output is arriving now.",
        errorText: null,
        isPendingCancel: false,
      };
  }
}

function buildEventHeaders(): Record<string, string> {
  const headers: Record<string, string> = {};
  const authToken = getAuthToken();
  const apiKey = readRuntimeApiKey() || getDevApiKey();
  if (authToken) {
    headers.Authorization = `Bearer ${authToken}`;
  } else if (apiKey) {
    headers["X-API-Key"] = apiKey;
  }
  return headers;
}

function buildStatePatch(
  previous: InferenceRequestState,
  patch: Partial<InferenceRequestState>
): InferenceRequestState {
  const next = {
    ...previous,
    ...patch,
    updatedAt: Date.now(),
  };
  const latencyMetrics = deriveLatencyMetrics(next);
  const isActivePhase = isActiveInferencePhase(next.phase);
  const canInterrupt = isActivePhase && Boolean(next.taskId);
  return {
    ...next,
    latencyMetrics,
    canCancel: canInterrupt,
    canSwitchToFast: canInterrupt && next.mode === "think",
  };
}

export function useInferenceRequestState() {
  const [state, setState] = useState<InferenceRequestState>(
    createIdleInferenceRequestState()
  );
  const stateRef = useRef(state);
  const taskStreamRef = useRef<GuardianEventSource | null>(null);
  const attachedTaskIdRef = useRef<string | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const closeTaskStream = useCallback(() => {
    taskStreamRef.current?.close();
    taskStreamRef.current = null;
    attachedTaskIdRef.current = null;
  }, []);

  const applyPatch = useCallback((patch: Partial<InferenceRequestState>) => {
    setState((previous) => buildStatePatch(previous, patch));
  }, []);

  const reset = useCallback(() => {
    closeTaskStream();
    setState(createIdleInferenceRequestState());
  }, [closeTaskStream]);

  const startRequest = useCallback(
    ({ threadId, providerId, modelId, mode }: StartInferenceRequestInput) => {
      closeTaskStream();
      setState({
        ...createIdleInferenceRequestState(),
        phase: "sending",
        threadId,
        taskId: null,
        providerId,
        modelId,
        mode,
        startedAt: Date.now(),
        updatedAt: Date.now(),
        statusText: "Queued…",
        detailText: "Submitting your turn to Guardian.",
        errorText: null,
      });
    },
    [closeTaskStream]
  );

  const markFailed = useCallback(
    (
      errorText: string,
      options: {
        detailText?: string | null;
        timingPatch?: Partial<InferenceRequestState>;
      } = {}
    ) => {
      closeTaskStream();
      applyPatch({
        ...options.timingPatch,
        phase: "failed",
        taskId: null,
        statusText: null,
        detailText: options.detailText ?? "Guardian could not finish this turn.",
        errorText,
        canCancel: false,
        canSwitchToFast: false,
        isPendingCancel: false,
      });
    },
    [applyPatch, closeTaskStream]
  );

  const markCancelled = useCallback(
    (
      detailText = "The current response was stopped.",
      options: { timingPatch?: Partial<InferenceRequestState> } = {}
    ) => {
      closeTaskStream();
      applyPatch({
        ...options.timingPatch,
        phase: "cancelled",
        taskId: null,
        statusText: null,
        detailText,
        errorText: null,
        canCancel: false,
        canSwitchToFast: false,
        isPendingCancel: false,
      });
    },
    [applyPatch, closeTaskStream]
  );

  const markCompleted = useCallback(
    (
      detailText = "Guardian finished responding.",
      options: { timingPatch?: Partial<InferenceRequestState> } = {}
    ) => {
      closeTaskStream();
      applyPatch({
        ...options.timingPatch,
        phase: "completed",
        taskId: null,
        statusText: null,
        detailText,
        errorText: null,
        canCancel: false,
        canSwitchToFast: false,
        isPendingCancel: false,
      });
    },
    [applyPatch, closeTaskStream]
  );

  const attachTask = useCallback(
    (taskId: string) => {
      if (!taskId) return;
      if (attachedTaskIdRef.current === taskId) return;

      closeTaskStream();
      attachedTaskIdRef.current = taskId;
      applyPatch({
        taskId,
        phase: stateRef.current.mode === "think" ? "thinking" : "sending",
        errorText: null,
        isPendingCancel: false,
      });

      const stream = new GuardianEventSource(
        `/api/tasks/${encodeURIComponent(taskId)}/events`,
        {
          headers: buildEventHeaders(),
          withCredentials: true,
          autoReconnect: true,
          retryInterval: 3000,
        }
      );
      taskStreamRef.current = stream;

      const handleTaskProgress = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const threadId = getTaskEventThreadId(payload);
        const eventTaskId = getTaskEventTaskId(payload);
        if (
          Number.isFinite(threadId) &&
          stateRef.current.threadId != null &&
          threadId !== stateRef.current.threadId
        ) {
          return;
        }
        if (
          eventTaskId &&
          attachedTaskIdRef.current &&
          eventTaskId !== attachedTaskIdRef.current
        ) {
          return;
        }
        applyPatch({
          taskId,
          phase: "streaming",
          statusText: "Generating…",
          detailText: "Output is arriving now.",
          errorText: null,
          isPendingCancel: false,
        });
      };

      const handleTaskState = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const threadId = getTaskEventThreadId(payload);
        const eventTaskId = getTaskEventTaskId(payload);
        if (
          Number.isFinite(threadId) &&
          stateRef.current.threadId != null &&
          threadId !== stateRef.current.threadId
        ) {
          return;
        }
        if (
          eventTaskId &&
          attachedTaskIdRef.current &&
          eventTaskId !== attachedTaskIdRef.current
        ) {
          return;
        }

        const lifecycleState = normalizeTaskLifecycleState(
          payload?.state ?? payload?.status ?? payload?.lifecycle_state
        );
        if (!lifecycleState) {
          return;
        }
        const timingPatch = extractTimingPatch(payload);

        if (lifecycleState === "COMPLETED") {
          const detail =
            typeof payload?.message_id === "number"
              ? "Guardian finished and saved the response."
              : "Guardian finished responding.";
          markCompleted(detail, { timingPatch });
          return;
        }
        if (lifecycleState === "FAILED") {
          const errorText =
            typeof payload?.error === "string" && payload.error.trim().length > 0
              ? payload.error.trim()
              : "Guardian could not finish the response.";
          markFailed(errorText, {
            detailText: "Try again or switch to a faster mode.",
            timingPatch,
          });
          return;
        }
        if (lifecycleState === "CANCELLED") {
          markCancelled("The current response was cancelled.", {
            timingPatch,
          });
          return;
        }

        const patch = buildLifecyclePatch(lifecycleState);
        applyPatch({
          taskId,
          ...timingPatch,
          ...patch,
        });
      };

      const handleTaskCompleted = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const detail =
          typeof payload?.message_id === "number"
            ? "Guardian finished and saved the response."
            : "Guardian finished responding.";
        markCompleted(detail, { timingPatch: extractTimingPatch(payload) });
      };

      const handleTaskCancelled = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        markCancelled("The current response was cancelled.", {
          timingPatch: extractTimingPatch(payload),
        });
      };

      const handleTaskFailed = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const errorText =
          typeof payload?.error === "string" && payload.error.trim().length > 0
            ? payload.error.trim()
            : "Guardian could not finish the response.";
        markFailed(errorText, {
          detailText: "Try again or switch to a faster mode.",
          timingPatch: extractTimingPatch(payload),
        });
      };

      stream.addEventListener("task.progress", handleTaskProgress as EventListener);
      stream.addEventListener("task.state", handleTaskState as EventListener);
      stream.addEventListener("task.completed", handleTaskCompleted as EventListener);
      stream.addEventListener("task.cancelled", handleTaskCancelled as EventListener);
      stream.addEventListener("task.failed", handleTaskFailed as EventListener);
      stream.addEventListener("completion.error", handleTaskFailed as EventListener);
      stream.onerror = () => {
        if (stateRef.current.phase === "completed" || stateRef.current.phase === "cancelled") {
          return;
        }
        applyPatch({
          detailText:
            stateRef.current.phase === "thinking"
              ? "Still waiting for the worker to report progress."
              : stateRef.current.detailText,
        });
      };
    },
    [applyPatch, closeTaskStream, markCancelled, markCompleted, markFailed]
  );

  const requestCancel = useCallback(async () => {
    const taskId = stateRef.current.taskId;
    if (!taskId) return false;
    applyPatch({
      isPendingCancel: true,
      detailText:
        stateRef.current.mode === "think"
          ? "Cancelling the current reasoning pass…"
          : "Cancelling the current response…",
    });
    try {
      await api.post(`/api/tasks/${encodeURIComponent(taskId)}/cancel`);
      return true;
    } catch (error: any) {
      markFailed(
        error?.response?.data?.detail ||
          error?.message ||
          "Unable to stop the current request.",
        {
          detailText: "Guardian could not cancel the active task.",
        }
      );
      return false;
    }
  }, [applyPatch, markFailed]);

  useEffect(() => () => closeTaskStream(), [closeTaskStream]);

  return useMemo(
    () => ({
      state,
      startRequest,
      attachTask,
      markCompleted,
      markFailed,
      markCancelled,
      requestCancel,
      reset,
    }),
    [
      attachTask,
      markCancelled,
      markCompleted,
      markFailed,
      requestCancel,
      reset,
      startRequest,
      state,
    ]
  );
}
