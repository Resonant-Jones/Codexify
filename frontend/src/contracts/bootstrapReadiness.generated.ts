// Generated from contracts/bootstrap/readiness.v1.json. Do not edit.
export const BOOTSTRAP_CONTRACT_VERSION = 1 as const;

export const BootstrapWorkflow = {
  INSPECTING: "inspecting",
  CONFIGURING: "configuring",
  DOWNLOADING: "downloading",
  STARTING: "starting",
  MIGRATING: "migrating",
  VERIFYING: "verifying",
  PAUSED: "paused",
  ACTION_REQUIRED: "action_required",
  FAILED: "failed",
  COMPLETE: "complete",
} as const;
export type BootstrapWorkflow = (typeof BootstrapWorkflow)[keyof typeof BootstrapWorkflow];

export const BootstrapHumanAction = {
  NONE: "none",
  CONSENT_REQUIRED: "consent_required",
  CREDENTIALS_REQUIRED: "credentials_required",
  PROVIDER_MODEL_CHOICE_REQUIRED: "provider_model_choice_required",
  NETWORK_UNAVAILABLE: "network_unavailable",
  PREREQUISITE_UNAVAILABLE: "prerequisite_unavailable",
} as const;
export type BootstrapHumanAction = (typeof BootstrapHumanAction)[keyof typeof BootstrapHumanAction];

export const SetupReadinessState = {
  MISSING_CONFIG: "missing_config",
  CONFIG_INCOMPLETE: "config_incomplete",
  CONFIG_CONFLICT: "config_conflict",
  DOCKER_MISSING: "docker_missing",
  DOCKER_NOT_RUNNING: "docker_not_running",
  DOCKER_COMPOSE_MISSING: "docker_compose_missing",
  OLLAMA_MISSING: "ollama_missing",
  OLLAMA_NOT_RUNNING: "ollama_not_running",
  LOCAL_INFERENCE_NOT_RUNNING: "local_inference_not_running",
  MODEL_MISSING: "model_missing",
  COMPOSE_CONFIG_INVALID: "compose_config_invalid",
  EXISTING_VOLUMES_DETECTED: "existing_volumes_detected",
  BACKEND_NOT_RUNNING: "backend_not_running",
  BACKEND_UNHEALTHY: "backend_unhealthy",
  FRONTEND_NOT_RUNNING: "frontend_not_running",
  CORE_READY: "core_ready",
  INFERENCE_READY: "inference_ready",
} as const;
export type SetupReadinessState = (typeof SetupReadinessState)[keyof typeof SetupReadinessState];

export interface BootstrapReadiness {
  version: typeof BOOTSTRAP_CONTRACT_VERSION;
  workflow: BootstrapWorkflow;
  coreReady: boolean;
  inferenceReady: boolean;
  humanAction: BootstrapHumanAction;
}
