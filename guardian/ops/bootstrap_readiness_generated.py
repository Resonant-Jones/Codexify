# Generated from contracts/bootstrap/readiness.v1.json. Do not edit.
from __future__ import annotations
from dataclasses import dataclass
from enum import Enum

BOOTSTRAP_CONTRACT_VERSION = 1

class BootstrapWorkflow(str, Enum):
    INSPECTING = "inspecting"
    CONFIGURING = "configuring"
    DOWNLOADING = "downloading"
    STARTING = "starting"
    MIGRATING = "migrating"
    VERIFYING = "verifying"
    PAUSED = "paused"
    ACTION_REQUIRED = "action_required"
    FAILED = "failed"
    COMPLETE = "complete"


class BootstrapHumanAction(str, Enum):
    NONE = "none"
    CONSENT_REQUIRED = "consent_required"
    CREDENTIALS_REQUIRED = "credentials_required"
    PROVIDER_MODEL_CHOICE_REQUIRED = "provider_model_choice_required"
    NETWORK_UNAVAILABLE = "network_unavailable"
    PREREQUISITE_UNAVAILABLE = "prerequisite_unavailable"


class SetupReadinessState(str, Enum):
    MISSING_CONFIG = "missing_config"
    CONFIG_INCOMPLETE = "config_incomplete"
    CONFIG_CONFLICT = "config_conflict"
    DOCKER_MISSING = "docker_missing"
    DOCKER_NOT_RUNNING = "docker_not_running"
    DOCKER_COMPOSE_MISSING = "docker_compose_missing"
    OLLAMA_MISSING = "ollama_missing"
    OLLAMA_NOT_RUNNING = "ollama_not_running"
    LOCAL_INFERENCE_NOT_RUNNING = "local_inference_not_running"
    MODEL_MISSING = "model_missing"
    COMPOSE_CONFIG_INVALID = "compose_config_invalid"
    EXISTING_VOLUMES_DETECTED = "existing_volumes_detected"
    BACKEND_NOT_RUNNING = "backend_not_running"
    BACKEND_UNHEALTHY = "backend_unhealthy"
    FRONTEND_NOT_RUNNING = "frontend_not_running"
    CORE_READY = "core_ready"
    INFERENCE_READY = "inference_ready"


@dataclass(frozen=True)
class BootstrapReadiness:
    workflow: BootstrapWorkflow
    core_ready: bool = False
    inference_ready: bool = False
    human_action: BootstrapHumanAction = BootstrapHumanAction.NONE

    def as_dict(self) -> dict:
        return {"version": BOOTSTRAP_CONTRACT_VERSION,
                "workflow": self.workflow.value, "coreReady": self.core_ready,
                "inferenceReady": self.inference_ready,
                "humanAction": self.human_action.value}
