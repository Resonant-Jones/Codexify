export type ComposerInferenceMode = "default" | "no_think" | "think";

export type InferenceLatencyMetric = {
  label: string;
  value: string;
};

export type InferencePhase =
  | "idle"
  | "sending"
  | "thinking"
  | "streaming"
  | "completed"
  | "failed"
  | "cancelled";

export interface InferenceRequestState {
  phase: InferencePhase;
  threadId: number | null;
  taskId: string | null;
  providerId: string | null;
  modelId: string | null;
  mode: ComposerInferenceMode;
  startedAt: number | null;
  updatedAt: number | null;
  statusText: string | null;
  detailText: string | null;
  errorText: string | null;
  queuedAt?: string | null;
  awaitingModelAt?: string | null;
  awaitingFirstTokenAt?: string | null;
  firstTokenAt?: string | null;
  firstOutputAt?: string | null;
  completedAt?: string | null;
  latencyMetrics?: InferenceLatencyMetric[];
  canCancel: boolean;
  canSwitchToFast: boolean;
  isPendingCancel: boolean;
}

export const DEFAULT_COMPOSER_INFERENCE_MODE: ComposerInferenceMode =
  "default";

export function createIdleInferenceRequestState(): InferenceRequestState {
  return {
    phase: "idle",
    threadId: null,
    taskId: null,
    providerId: null,
    modelId: null,
    mode: DEFAULT_COMPOSER_INFERENCE_MODE,
    startedAt: null,
    updatedAt: null,
    statusText: null,
    detailText: null,
    errorText: null,
    queuedAt: null,
    awaitingModelAt: null,
    awaitingFirstTokenAt: null,
    firstTokenAt: null,
    firstOutputAt: null,
    completedAt: null,
    latencyMetrics: [],
    canCancel: false,
    canSwitchToFast: false,
    isPendingCancel: false,
  };
}

export function isActiveInferencePhase(phase: InferencePhase): boolean {
  return phase === "sending" || phase === "thinking" || phase === "streaming";
}

export function isReasoningMode(
  value: unknown
): value is ComposerInferenceMode {
  return value === "default" || value === "no_think" || value === "think";
}
