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
  (typeof TASK_LIFECYCLE_STATE)[keyof typeof TASK_LIFECYCLE_STATE];

type StartInferenceRequestInput = {
  threadId: number;
  providerId: string | null;
  modelId: string | null;
  mode: ComposerInferenceMode;
};

const TASK_LIFECYCLE_STATE = {
  QUEUED: "QUEUED",
  AWAITING_MODEL: "AWAITING_MODEL",
  AWAITING_FIRST_TOKEN: "AWAITING_FIRST_TOKEN",
  STREAMING: "STREAMING",
  COMPLETED: "COMPLETED",
  FAILED: "FAILED",
  CANCELLED: "CANCELLED",
} as const;

const INFERENCE_LIFECYCLE_STATE = {
  IDLE: "idle",
  QUEUED: "queued",
  AWAITING_MODEL: "awaiting_model",
  AWAITING_FIRST_TOKEN: "awaiting_first_token",
  STREAMING: "streaming",
  COMPLETED: "completed",
  PROVIDER_ERROR: "provider_error",
  DEGRADED: "degraded",
  CANCELLED: "cancelled",
} as const;

const INFERENCE_STATUS_TEXT = {
  QUEUED: "Queued…",
  WARMING_MODEL: "Warming model…",
  WAITING_FOR_FIRST_TOKEN: "Waiting for first token…",
  GENERATING: "Generating…",
  PROVIDER_ERROR: "Provider error…",
  PROVIDER_DEGRADED: "Provider degraded…",
} as const;

const INFERENCE_DETAIL_TEXT = {
  QUEUED: "Guardian is preparing a response.",
  SUBMITTING_TURN: "Submitting your turn to Guardian.",
  WARMING_MODEL: "Guardian is warming the selected model.",
  WAITING_FOR_FIRST_TOKEN: "Guardian is waiting for the first response chunk.",
  STREAMING: "Output is arriving now.",
  COMPLETED: "Guardian finished responding.",
  COMPLETED_AND_SAVED: "Guardian finished and saved the response.",
  PROVIDER_ERROR: "Provider error: Guardian could not finish this turn.",
  PROVIDER_ERROR_RETRY: "Provider error: try again or switch to a faster mode.",
  CANCELLED: "The current response was stopped.",
  CANCELLED_ACTIVE: "The current response was cancelled.",
  CANCEL_THINKING: "Cancelling the current reasoning pass…",
  CANCEL_RESPONSE: "Cancelling the current response…",
  CANCEL_FAILED: "Guardian could not cancel the active task.",
  DEGRADED_STREAMING:
    "Provider visibility is degraded; still waiting for the next stream event.",
  DEGRADED_TERMINAL:
    "Provider visibility is degraded; still waiting for a terminal task event.",
} as const;

function isExplicitDegradedState(state: Pick<InferenceRequestState, "statusText" | "detailText">): boolean {
  return (
    state.statusText === INFERENCE_STATUS_TEXT.PROVIDER_DEGRADED ||
    state.detailText === INFERENCE_DETAIL_TEXT.DEGRADED_STREAMING ||
    state.detailText === INFERENCE_DETAIL_TEXT.DEGRADED_TERMINAL
  );
}

function buildDelayedLifecycleKey(
  state: Pick<InferenceRequestState, "threadId" | "taskId">,
  snapshot: Pick<InferenceLifecycleSnapshot, "canonicalState" | "delayDetailText" | "timings">
): string {
  return [
    state.threadId ?? "null",
    state.taskId ?? "null",
    snapshot.canonicalState,
    snapshot.delayDetailText,
    snapshot.timings.sendElapsedMs ?? "na",
    snapshot.timings.firstLifecycleEvidenceMs ?? "na",
    snapshot.timings.firstTokenMs ?? "na",
  ].join("|");
}

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
    case TASK_LIFECYCLE_STATE.QUEUED:
    case TASK_LIFECYCLE_STATE.AWAITING_MODEL:
    case TASK_LIFECYCLE_STATE.AWAITING_FIRST_TOKEN:
    case TASK_LIFECYCLE_STATE.STREAMING:
    case TASK_LIFECYCLE_STATE.COMPLETED:
    case TASK_LIFECYCLE_STATE.FAILED:
    case TASK_LIFECYCLE_STATE.CANCELLED:
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

export const INFERENCE_SLOW_PATH_MS = 15_000;

type InferenceLifecycleState =
  (typeof INFERENCE_LIFECYCLE_STATE)[keyof typeof INFERENCE_LIFECYCLE_STATE];

type InferenceLifecycleSnapshot = {
  canonicalState: InferenceLifecycleState;
  isDelayed: boolean;
  delayDetailText: string | null;
  timings: {
    sendElapsedMs: number | null;
    firstLifecycleEvidenceMs: number | null;
    firstTokenMs: number | null;
    terminalMs: number | null;
  };
  evidence: {
    hasTaskId: boolean;
    hasQueuedAt: boolean;
    hasAwaitingModelAt: boolean;
    hasAwaitingFirstTokenAt: boolean;
    hasFirstTokenAt: boolean;
    hasFirstOutputAt: boolean;
    hasCompletedAt: boolean;
    hasErrorText: boolean;
  };
};

type LifecycleTimingState = Pick<
  InferenceRequestState,
  | "phase"
  | "threadId"
  | "taskId"
  | "startedAt"
  | "updatedAt"
  | "providerId"
  | "modelId"
  | "mode"
  | "statusText"
  | "detailText"
  | "errorText"
  | "queuedAt"
  | "awaitingModelAt"
  | "awaitingFirstTokenAt"
  | "firstTokenAt"
  | "firstOutputAt"
  | "completedAt"
>;

function buildDelayedDetailText(
  state: Pick<LifecycleTimingState, "taskId">,
  canonicalState: Exclude<
    InferenceLifecycleState,
    "idle" | "completed" | "provider_error" | "degraded" | "cancelled"
  >,
  sendElapsedMs: number
): string {
  const elapsed = formatLatencyDuration(sendElapsedMs);
  switch (canonicalState) {
    case INFERENCE_LIFECYCLE_STATE.QUEUED:
      return state.taskId
        ? `Task accepted; still waiting for lifecycle evidence after ${elapsed}.`
        : `No lifecycle evidence yet after ${elapsed}; still waiting for task acknowledgement.`;
    case INFERENCE_LIFECYCLE_STATE.AWAITING_MODEL:
      return `Task acknowledged; the model is still warming up after ${elapsed}.`;
    case INFERENCE_LIFECYCLE_STATE.AWAITING_FIRST_TOKEN:
      return `Model accepted the request; still waiting for the first token after ${elapsed}.`;
    case INFERENCE_LIFECYCLE_STATE.STREAMING:
      return `Assistant output is still streaming after ${elapsed}.`;
  }
}

export function describeInferenceRequestState(
  state: LifecycleTimingState,
  now = Date.now()
): InferenceLifecycleSnapshot {
  const queuedAtMs = parseTimestampMs(state.queuedAt);
  const awaitingModelAtMs = parseTimestampMs(state.awaitingModelAt);
  const awaitingFirstTokenAtMs = parseTimestampMs(state.awaitingFirstTokenAt);
  const firstTokenAtMs = parseTimestampMs(state.firstTokenAt);
  const firstOutputAtMs = parseTimestampMs(state.firstOutputAt);
  const completedAtMs = parseTimestampMs(state.completedAt);
  const startedAtMs =
    typeof state.startedAt === "number" && Number.isFinite(state.startedAt)
      ? state.startedAt
      : null;

  const firstLifecycleEvidenceAtMs =
    queuedAtMs ??
    awaitingModelAtMs ??
    awaitingFirstTokenAtMs ??
    firstTokenAtMs ??
    firstOutputAtMs ??
    (state.taskId != null &&
    typeof state.updatedAt === "number" &&
    Number.isFinite(state.updatedAt)
      ? state.updatedAt
      : null) ??
    completedAtMs;
  const firstVisibleProgressAtMs =
    firstTokenAtMs ??
    firstOutputAtMs ??
    (state.phase === "streaming" &&
    typeof state.updatedAt === "number" &&
    Number.isFinite(state.updatedAt)
      ? state.updatedAt
      : null);
  const sendElapsedMs =
    startedAtMs != null ? Math.max(0, now - startedAtMs) : null;
  const firstLifecycleEvidenceMs =
    startedAtMs != null && firstLifecycleEvidenceAtMs != null
      ? Math.max(0, firstLifecycleEvidenceAtMs - startedAtMs)
      : null;
  const firstTokenMs =
    startedAtMs != null && firstVisibleProgressAtMs != null
      ? Math.max(0, firstVisibleProgressAtMs - startedAtMs)
      : null;
  const terminalMs =
    startedAtMs != null && completedAtMs != null
      ? Math.max(0, completedAtMs - startedAtMs)
      : startedAtMs != null &&
          state.phase === "completed" &&
          typeof state.updatedAt === "number" &&
          Number.isFinite(state.updatedAt)
        ? Math.max(0, state.updatedAt - startedAtMs)
      : null;

  const evidence = {
    hasTaskId: Boolean(state.taskId),
    hasQueuedAt: queuedAtMs != null,
    hasAwaitingModelAt: awaitingModelAtMs != null,
    hasAwaitingFirstTokenAt: awaitingFirstTokenAtMs != null,
    hasFirstTokenAt: firstTokenAtMs != null,
    hasFirstOutputAt: firstOutputAtMs != null,
    hasCompletedAt: completedAtMs != null,
    hasErrorText: Boolean(state.errorText),
  };

  let canonicalState: InferenceLifecycleState = INFERENCE_LIFECYCLE_STATE.IDLE;
  if (state.phase === "completed" || completedAtMs != null) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.COMPLETED;
  } else if (state.phase === "failed" || state.errorText) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.PROVIDER_ERROR;
  } else if (state.phase === "cancelled") {
    canonicalState = INFERENCE_LIFECYCLE_STATE.CANCELLED;
  } else if (isExplicitDegradedState(state)) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.DEGRADED;
  } else if (state.phase === "streaming" || firstVisibleProgressAtMs != null) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.STREAMING;
  } else if (awaitingFirstTokenAtMs != null) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.AWAITING_FIRST_TOKEN;
  } else if (awaitingModelAtMs != null) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.AWAITING_MODEL;
  } else if (queuedAtMs != null || state.taskId != null || startedAtMs != null) {
    canonicalState = INFERENCE_LIFECYCLE_STATE.QUEUED;
  }

  const isDelayed =
    sendElapsedMs != null &&
    sendElapsedMs >= INFERENCE_SLOW_PATH_MS &&
    canonicalState !== INFERENCE_LIFECYCLE_STATE.COMPLETED &&
    canonicalState !== INFERENCE_LIFECYCLE_STATE.PROVIDER_ERROR &&
    canonicalState !== INFERENCE_LIFECYCLE_STATE.CANCELLED;

  const delayedState =
    canonicalState === INFERENCE_LIFECYCLE_STATE.QUEUED ||
    canonicalState === INFERENCE_LIFECYCLE_STATE.AWAITING_MODEL ||
    canonicalState === INFERENCE_LIFECYCLE_STATE.AWAITING_FIRST_TOKEN ||
    canonicalState === INFERENCE_LIFECYCLE_STATE.STREAMING
      ? canonicalState
      : null;

  return {
    canonicalState,
    isDelayed,
    delayDetailText:
      isDelayed && delayedState != null
        ? buildDelayedDetailText(state, delayedState, sendElapsedMs ?? 0)
        : null,
    timings: {
      sendElapsedMs,
      firstLifecycleEvidenceMs,
      firstTokenMs,
      terminalMs,
    },
    evidence,
  };
}

function logInferenceLifecycleAttribution(
  reason: string,
  state: LifecycleTimingState,
  snapshot: InferenceLifecycleSnapshot
): void {
  console.debug("[useInferenceRequestState] lifecycle attribution", {
    reason,
    canonicalState: snapshot.canonicalState,
    isDelayed: snapshot.isDelayed,
    delayDetailText: snapshot.delayDetailText,
    evidence: snapshot.evidence,
    timings: snapshot.timings,
    thresholdMs: INFERENCE_SLOW_PATH_MS,
    threadId: state.threadId,
    taskId: state.taskId,
    providerId: state.providerId,
    modelId: state.modelId,
    mode: state.mode,
    statusText: state.statusText,
    detailText: state.detailText,
    errorText: state.errorText,
    phase: state.phase,
  });
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
    case TASK_LIFECYCLE_STATE.QUEUED:
      return {
        phase: "sending",
        statusText: INFERENCE_STATUS_TEXT.QUEUED,
        detailText: INFERENCE_DETAIL_TEXT.QUEUED,
        errorText: null,
        isPendingCancel: false,
      };
    case TASK_LIFECYCLE_STATE.AWAITING_MODEL:
      return {
        phase: "sending",
        statusText: INFERENCE_STATUS_TEXT.WARMING_MODEL,
        detailText: INFERENCE_DETAIL_TEXT.WARMING_MODEL,
        errorText: null,
        isPendingCancel: false,
      };
    case TASK_LIFECYCLE_STATE.AWAITING_FIRST_TOKEN:
      return {
        phase: "sending",
        statusText: INFERENCE_STATUS_TEXT.WAITING_FOR_FIRST_TOKEN,
        detailText: INFERENCE_DETAIL_TEXT.WAITING_FOR_FIRST_TOKEN,
        errorText: null,
        isPendingCancel: false,
      };
    case TASK_LIFECYCLE_STATE.STREAMING:
      return {
        phase: "streaming",
        statusText: INFERENCE_STATUS_TEXT.GENERATING,
        detailText: INFERENCE_DETAIL_TEXT.STREAMING,
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
  const delayedLifecycleKeyRef = useRef<string | null>(null);

  useEffect(() => {
    stateRef.current = state;
  }, [state]);

  const closeTaskStream = useCallback(() => {
    taskStreamRef.current?.close();
    taskStreamRef.current = null;
    attachedTaskIdRef.current = null;
    delayedLifecycleKeyRef.current = null;
  }, []);

  const applyPatch = useCallback((patch: Partial<InferenceRequestState>) => {
    setState((previous) => buildStatePatch(previous, patch));
  }, []);

  const reset = useCallback(() => {
    closeTaskStream();
    delayedLifecycleKeyRef.current = null;
    setState(createIdleInferenceRequestState());
  }, [closeTaskStream]);

  const startRequest = useCallback(
    ({ threadId, providerId, modelId, mode }: StartInferenceRequestInput) => {
      closeTaskStream();
      const nextState = {
        ...createIdleInferenceRequestState(),
        phase: "sending",
        threadId,
        taskId: null,
        providerId,
        modelId,
        mode,
        startedAt: Date.now(),
        updatedAt: Date.now(),
        statusText: INFERENCE_STATUS_TEXT.QUEUED,
        detailText: INFERENCE_DETAIL_TEXT.SUBMITTING_TURN,
        errorText: null,
      };
      stateRef.current = nextState;
      setState(nextState);
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
        statusText: INFERENCE_STATUS_TEXT.PROVIDER_ERROR,
        detailText:
          options.detailText ??
          INFERENCE_DETAIL_TEXT.PROVIDER_ERROR,
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
      detailText = INFERENCE_DETAIL_TEXT.CANCELLED,
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
      detailText = INFERENCE_DETAIL_TEXT.COMPLETED,
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
          statusText: INFERENCE_STATUS_TEXT.GENERATING,
          detailText: INFERENCE_DETAIL_TEXT.STREAMING,
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

        if (lifecycleState === TASK_LIFECYCLE_STATE.COMPLETED) {
          const detail =
            typeof payload?.message_id === "number"
              ? INFERENCE_DETAIL_TEXT.COMPLETED_AND_SAVED
              : INFERENCE_DETAIL_TEXT.COMPLETED;
          markCompleted(detail, { timingPatch });
          return;
        }
        if (lifecycleState === TASK_LIFECYCLE_STATE.FAILED) {
          const errorText =
            typeof payload?.error === "string" && payload.error.trim().length > 0
              ? payload.error.trim()
              : "Guardian could not finish the response.";
          markFailed(errorText, {
            detailText: INFERENCE_DETAIL_TEXT.PROVIDER_ERROR_RETRY,
            timingPatch,
          });
          return;
        }
        if (lifecycleState === TASK_LIFECYCLE_STATE.CANCELLED) {
          markCancelled(INFERENCE_DETAIL_TEXT.CANCELLED_ACTIVE, {
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
            ? INFERENCE_DETAIL_TEXT.COMPLETED_AND_SAVED
            : INFERENCE_DETAIL_TEXT.COMPLETED;
        markCompleted(detail, { timingPatch: extractTimingPatch(payload) });
      };

      const handleTaskCancelled = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        markCancelled(INFERENCE_DETAIL_TEXT.CANCELLED_ACTIVE, {
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
          detailText: INFERENCE_DETAIL_TEXT.PROVIDER_ERROR_RETRY,
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
        const snapshot = describeInferenceRequestState(stateRef.current);
        if (snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.PROVIDER_ERROR) {
          return;
        }
        const delayedDetail =
          snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.STREAMING
            ? INFERENCE_DETAIL_TEXT.DEGRADED_STREAMING
            : INFERENCE_DETAIL_TEXT.DEGRADED_TERMINAL;
        logInferenceLifecycleAttribution("stream.onerror", stateRef.current, snapshot);
        applyPatch({
          statusText: INFERENCE_STATUS_TEXT.PROVIDER_DEGRADED,
          detailText: delayedDetail,
        });
      };
    },
    [applyPatch, closeTaskStream, markCancelled, markCompleted, markFailed]
  );

  useEffect(() => {
    const snapshot = describeInferenceRequestState(state);
    if (
      snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.IDLE ||
      snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.COMPLETED ||
      snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.DEGRADED ||
      snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.PROVIDER_ERROR ||
      snapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.CANCELLED
    ) {
      delayedLifecycleKeyRef.current = null;
      return;
    }

    const key = buildDelayedLifecycleKey(state, snapshot);

    if (state.detailText === snapshot.delayDetailText) {
      delayedLifecycleKeyRef.current = key;
      return;
    }

    const applyDelayedDetail = (
      currentState: InferenceRequestState = stateRef.current
    ) => {
      const currentSnapshot = describeInferenceRequestState(currentState);
      if (
        currentSnapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.IDLE ||
        currentSnapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.COMPLETED ||
        currentSnapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.DEGRADED ||
        currentSnapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.PROVIDER_ERROR ||
        currentSnapshot.canonicalState === INFERENCE_LIFECYCLE_STATE.CANCELLED ||
        currentSnapshot.delayDetailText == null ||
        !currentSnapshot.isDelayed
      ) {
        return;
      }

      const currentKey = buildDelayedLifecycleKey(currentState, currentSnapshot);

      if (currentState.detailText === currentSnapshot.delayDetailText) {
        delayedLifecycleKeyRef.current = currentKey;
        return;
      }

      delayedLifecycleKeyRef.current = currentKey;
      logInferenceLifecycleAttribution("slow-threshold", currentState, currentSnapshot);
      applyPatch({
        detailText: currentSnapshot.delayDetailText,
      });
    };

    const elapsedMs = snapshot.timings.sendElapsedMs ?? 0;
    const remainingMs = Math.max(INFERENCE_SLOW_PATH_MS - elapsedMs, 0);
    if (!snapshot.isDelayed || snapshot.delayDetailText == null) {
      const timeout = window.setTimeout(() => {
        applyDelayedDetail();
      }, remainingMs);
      return () => window.clearTimeout(timeout);
    }

    applyDelayedDetail();
  }, [applyPatch, state]);

  const requestCancel = useCallback(async () => {
    const taskId = stateRef.current.taskId;
    if (!taskId) return false;
    applyPatch({
      isPendingCancel: true,
      detailText:
        stateRef.current.mode === "think"
          ? INFERENCE_DETAIL_TEXT.CANCEL_THINKING
          : INFERENCE_DETAIL_TEXT.CANCEL_RESPONSE,
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
          detailText: INFERENCE_DETAIL_TEXT.CANCEL_FAILED,
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
