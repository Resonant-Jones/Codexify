import type {
  ChatRequestState,
  ProviderRuntimeState,
} from "@/contracts/runtimeTokens";

export type RuntimeVisualTone = "neutral" | "info" | "warning" | "error";

export type RuntimeVisualStateKey =
  | "queued"
  | "warming"
  | "starting"
  | "generating"
  | "complete"
  | "delayed"
  | "error";

export interface RuntimeVisualState {
  key: RuntimeVisualStateKey;

  label: string;
  description?: string;

  tone: RuntimeVisualTone;

  isTerminal: boolean;
  isBlocking: boolean;
}

export function mapRuntimeToVisualState(
  requestState: ChatRequestState,
  providerState?: ProviderRuntimeState
): RuntimeVisualState {
  // Error states (highest priority)
  if (
    requestState === "failed_retryable" ||
    requestState === "failed_fatal" ||
    providerState === "error"
  ) {
    return {
      key: "error",
      label: "Error",
      description: "The request failed or the provider returned an error.",
      tone: "error",
      isTerminal: true,
      isBlocking: true,
    };
  }

  // Completed
  if (requestState === "completed") {
    return {
      key: "complete",
      label: "Complete",
      description: "The response finished successfully.",
      tone: "neutral",
      isTerminal: true,
      isBlocking: false,
    };
  }

  // Generating / streaming
  if (
    requestState === "streaming" ||
    providerState === "generating"
  ) {
    return {
      key: "generating",
      label: "Generating",
      description: "The model is producing output.",
      tone: "neutral",
      isTerminal: false,
      isBlocking: false,
    };
  }

  // Awaiting first token
  if (requestState === "awaiting_first_token") {
    return {
      key: "starting",
      label: "Starting",
      description: "The model has accepted the request and is preparing output.",
      tone: "info",
      isTerminal: false,
      isBlocking: false,
    };
  }

  // Awaiting model with provider context
  if (requestState === "awaiting_model") {
    if (providerState === "model_warming") {
      return {
        key: "warming",
        label: "Warming",
        description: "The model is loading into memory.",
        tone: "warning",
        isTerminal: false,
        isBlocking: true,
      };
    }

    if (providerState === "degraded") {
      return {
        key: "delayed",
        label: "Delayed",
        description: "The runtime is slow or under load.",
        tone: "warning",
        isTerminal: false,
        isBlocking: false,
      };
    }

    return {
      key: "starting",
      label: "Starting",
      description: "Waiting for the model to begin processing.",
      tone: "info",
      isTerminal: false,
      isBlocking: false,
    };
  }

  // Queued / dispatch path
  if (
    requestState === "queued" ||
    requestState === "dispatching" ||
    requestState === "awaiting_ack"
  ) {
    return {
      key: "queued",
      label: "Queued",
      description: "The request is waiting to be processed.",
      tone: "info",
      isTerminal: false,
      isBlocking: false,
    };
  }

  // Fallback
  return {
    key: "queued",
    label: "Pending",
    description: "The request is in progress.",
    tone: "info",
    isTerminal: false,
    isBlocking: false,
  };
}
