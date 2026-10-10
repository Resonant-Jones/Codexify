// Generated from contracts/bootstrap/readiness.v1.json. Do not edit.
use serde::{Deserialize, Serialize};

pub const BOOTSTRAP_CONTRACT_VERSION: u8 = 1;

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[allow(non_camel_case_types)]
pub enum BootstrapWorkflow {
    #[serde(rename = "inspecting")]
    INSPECTING,
    #[serde(rename = "configuring")]
    CONFIGURING,
    #[serde(rename = "downloading")]
    DOWNLOADING,
    #[serde(rename = "starting")]
    STARTING,
    #[serde(rename = "migrating")]
    MIGRATING,
    #[serde(rename = "verifying")]
    VERIFYING,
    #[serde(rename = "paused")]
    PAUSED,
    #[serde(rename = "action_required")]
    ACTION_REQUIRED,
    #[serde(rename = "failed")]
    FAILED,
    #[serde(rename = "complete")]
    COMPLETE,
}
impl BootstrapWorkflow {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::INSPECTING => "inspecting",
            Self::CONFIGURING => "configuring",
            Self::DOWNLOADING => "downloading",
            Self::STARTING => "starting",
            Self::MIGRATING => "migrating",
            Self::VERIFYING => "verifying",
            Self::PAUSED => "paused",
            Self::ACTION_REQUIRED => "action_required",
            Self::FAILED => "failed",
            Self::COMPLETE => "complete",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[allow(non_camel_case_types)]
pub enum BootstrapHumanAction {
    #[serde(rename = "none")]
    NONE,
    #[serde(rename = "consent_required")]
    CONSENT_REQUIRED,
    #[serde(rename = "credentials_required")]
    CREDENTIALS_REQUIRED,
    #[serde(rename = "provider_model_choice_required")]
    PROVIDER_MODEL_CHOICE_REQUIRED,
    #[serde(rename = "network_unavailable")]
    NETWORK_UNAVAILABLE,
    #[serde(rename = "prerequisite_unavailable")]
    PREREQUISITE_UNAVAILABLE,
}
impl BootstrapHumanAction {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::NONE => "none",
            Self::CONSENT_REQUIRED => "consent_required",
            Self::CREDENTIALS_REQUIRED => "credentials_required",
            Self::PROVIDER_MODEL_CHOICE_REQUIRED => "provider_model_choice_required",
            Self::NETWORK_UNAVAILABLE => "network_unavailable",
            Self::PREREQUISITE_UNAVAILABLE => "prerequisite_unavailable",
        }
    }
}

#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
#[allow(non_camel_case_types)]
pub enum SetupReadinessState {
    #[serde(rename = "missing_config")]
    MISSING_CONFIG,
    #[serde(rename = "config_incomplete")]
    CONFIG_INCOMPLETE,
    #[serde(rename = "config_conflict")]
    CONFIG_CONFLICT,
    #[serde(rename = "docker_missing")]
    DOCKER_MISSING,
    #[serde(rename = "docker_not_running")]
    DOCKER_NOT_RUNNING,
    #[serde(rename = "docker_compose_missing")]
    DOCKER_COMPOSE_MISSING,
    #[serde(rename = "ollama_missing")]
    OLLAMA_MISSING,
    #[serde(rename = "ollama_not_running")]
    OLLAMA_NOT_RUNNING,
    #[serde(rename = "local_inference_not_running")]
    LOCAL_INFERENCE_NOT_RUNNING,
    #[serde(rename = "model_missing")]
    MODEL_MISSING,
    #[serde(rename = "compose_config_invalid")]
    COMPOSE_CONFIG_INVALID,
    #[serde(rename = "existing_volumes_detected")]
    EXISTING_VOLUMES_DETECTED,
    #[serde(rename = "backend_not_running")]
    BACKEND_NOT_RUNNING,
    #[serde(rename = "backend_unhealthy")]
    BACKEND_UNHEALTHY,
    #[serde(rename = "frontend_not_running")]
    FRONTEND_NOT_RUNNING,
    #[serde(rename = "core_ready")]
    CORE_READY,
    #[serde(rename = "inference_ready")]
    INFERENCE_READY,
}
impl SetupReadinessState {
    pub fn as_str(self) -> &'static str {
        match self {
            Self::MISSING_CONFIG => "missing_config",
            Self::CONFIG_INCOMPLETE => "config_incomplete",
            Self::CONFIG_CONFLICT => "config_conflict",
            Self::DOCKER_MISSING => "docker_missing",
            Self::DOCKER_NOT_RUNNING => "docker_not_running",
            Self::DOCKER_COMPOSE_MISSING => "docker_compose_missing",
            Self::OLLAMA_MISSING => "ollama_missing",
            Self::OLLAMA_NOT_RUNNING => "ollama_not_running",
            Self::LOCAL_INFERENCE_NOT_RUNNING => "local_inference_not_running",
            Self::MODEL_MISSING => "model_missing",
            Self::COMPOSE_CONFIG_INVALID => "compose_config_invalid",
            Self::EXISTING_VOLUMES_DETECTED => "existing_volumes_detected",
            Self::BACKEND_NOT_RUNNING => "backend_not_running",
            Self::BACKEND_UNHEALTHY => "backend_unhealthy",
            Self::FRONTEND_NOT_RUNNING => "frontend_not_running",
            Self::CORE_READY => "core_ready",
            Self::INFERENCE_READY => "inference_ready",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapReadiness {
    pub version: u8,
    pub workflow: BootstrapWorkflow,
    pub core_ready: bool,
    pub inference_ready: bool,
    pub human_action: BootstrapHumanAction,
}
