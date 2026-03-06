import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import { GuardianEventSource } from "@/lib/guardianEventSource";
import api, { getAuthToken, getDevApiKey, readRuntimeApiKey } from "@/lib/api";
import {
  createIdleInferenceRequestState,
  type ComposerInferenceMode,
  type InferenceRequestState,
} from "@/types/inference";

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
  const isActivePhase =
    next.phase === "sending" ||
    next.phase === "thinking" ||
    next.phase === "streaming";
  const canInterrupt = isActivePhase && Boolean(next.taskId);
  return {
    ...next,
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
        phase: "sending",
        threadId,
        taskId: null,
        providerId,
        modelId,
        mode,
        startedAt: Date.now(),
        updatedAt: Date.now(),
      statusText: "Sending…",
      detailText: "Submitting your turn to Guardian.",
      errorText: null,
      canCancel: false,
      canSwitchToFast: false,
      isPendingCancel: false,
    });
  },
    [closeTaskStream]
  );

  const markFailed = useCallback(
    (errorText: string, options: { detailText?: string | null } = {}) => {
      closeTaskStream();
      applyPatch({
        phase: "failed",
        statusText: "Response failed",
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
    (detailText = "The current response was stopped.") => {
      closeTaskStream();
      applyPatch({
        phase: "cancelled",
        statusText: "Stopped",
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
    (detailText = "Guardian finished responding.") => {
      closeTaskStream();
      applyPatch({
        phase: "completed",
        statusText: "Response complete",
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
        statusText:
          stateRef.current.mode === "think"
            ? "Reasoning through response…"
            : "Waiting for model…",
        detailText:
          stateRef.current.mode === "think"
            ? "This may take a few minutes."
            : "Guardian is preparing a response.",
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
        const threadId = Number(payload?.thread_id ?? payload?.threadId);
        if (
          Number.isFinite(threadId) &&
          stateRef.current.threadId != null &&
          threadId !== stateRef.current.threadId
        ) {
          return;
        }
        applyPatch({
          taskId,
          phase: "streaming",
          statusText: "Streaming response…",
          detailText: "Output is arriving now.",
          errorText: null,
          isPendingCancel: false,
        });
      };

      const handleTaskCompleted = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const detail =
          typeof payload?.message_id === "number"
            ? "Guardian finished and saved the response."
            : "Guardian finished responding.";
        markCompleted(detail);
      };

      const handleTaskCancelled = () => {
        markCancelled("The current response was cancelled.");
      };

      const handleTaskFailed = (event: Event) => {
        const payload = parseTaskEventPayload(event);
        const errorText =
          typeof payload?.error === "string" && payload.error.trim().length > 0
            ? payload.error.trim()
            : "Guardian could not finish the response.";
        markFailed(errorText, {
          detailText: "Try again or switch to a faster mode.",
        });
      };

      stream.addEventListener("task.progress", handleTaskProgress as EventListener);
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
