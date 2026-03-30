use base64::engine::general_purpose::{STANDARD as BASE64_STANDARD, URL_SAFE_NO_PAD};
use base64::Engine as _;
use hmac::{Hmac, Mac};
use reqwest::header::CONTENT_TYPE;
use serde::Serialize;
use serde_json::Value;
use sha2::Sha256;
use std::collections::{BTreeMap, HashSet};
use std::env;
use std::ffi::OsStr;
use std::fs;
use std::io::{ErrorKind, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;
use tauri::Manager;

const DESKTOP_KEYCHAIN_SERVICE: &str = "com.codexify.desktop";
const DESKTOP_KEYCHAIN_ACCOUNT: &str = "guardian_api_key";
const NORMALIZED_DOCKER_PATH: &str = "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin";
const BOOTSTRAP_LOG_TAIL_LINES: &str = "200";
const BOOTSTRAP_LOG_SERVICES: [&str; 5] = ["backend", "worker-chat", "db", "redis", "migrator"];
const BOOTSTRAP_RESTART_SERVICES: [&str; 5] = ["db", "redis", "migrator", "backend", "worker-chat"];
const DESKTOP_MEDIA_MAX_BYTES: usize = 10 * 1024 * 1024;
const FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE: &str = "runtime-root-unavailable";
const FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_MISSING: &str = "packaged-runtime-assets-missing";
const FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_CORRUPT: &str = "packaged-runtime-assets-corrupt";
const FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_INVALID: &str = "packaged-runtime-assets-invalid";
const FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED: &str =
    "packaged-runtime-materialization-failed";
const FAILURE_KIND_DOCKER_MOUNT_PATH_UNSHARED_OR_UNSUPPORTED: &str =
    "docker-mount-path-unshared-or-unsupported";
const FAILURE_KIND_DOCKER_CLI_UNAVAILABLE: &str = "docker-cli-unavailable";
const FAILURE_KIND_DOCKER_CLI_EXECUTION_FAILED: &str = "docker-cli-execution-failed";
const FAILURE_KIND_DOCKER_CLI_FOUND_BUT_UNUSABLE_FROM_PACKAGED_CONTEXT: &str =
    "docker-cli-found-but-unusable-from-packaged-context";
const FAILURE_KIND_DOCKER_DAEMON_UNAVAILABLE: &str = "docker-daemon-unavailable";
const FAILURE_KIND_RUNTIME_PATH_UNAVAILABLE: &str = "runtime-path-unavailable";
const FAILURE_KIND_REPO_RUNTIME_MISSING: &str = "repo-runtime-missing";
const FAILURE_KIND_PACKAGED_BOOTSTRAP_UNSUPPORTED: &str = "packaged-bootstrap-unsupported";
const FAILURE_KIND_SETUP_FAILED: &str = "setup-failed";
const FAILURE_KIND_PACKAGED_SETUP_FAILED: &str = "packaged-setup-failed";
const FAILURE_KIND_COMPOSE_UP_FAILED: &str = "compose-up-failed";
const FAILURE_KIND_PACKAGED_COMPOSE_UP_FAILED: &str = "packaged-compose-up-failed";
const FAILURE_KIND_READINESS_FAILED: &str = "readiness-failed";
const FAILURE_KIND_PACKAGED_READINESS_FAILED: &str = "packaged-readiness-failed";
const FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR: &str = "unexpected-execution-error";
const RUNTIME_CONTEXT_DEVELOPMENT: &str = "development";
const RUNTIME_CONTEXT_PACKAGED: &str = "packaged";
const PACKAGED_RUNTIME_METADATA_DIRNAME: &str = "Codexify";
const PACKAGED_RUNTIME_ROOT_DIRNAME: &str = "Codexify";
const PACKAGED_RUNTIME_HOME_DIRNAME: &str = PACKAGED_RUNTIME_METADATA_DIRNAME;
const PACKAGED_RUNTIME_MANIFEST_FILENAME: &str = ".codexify-runtime-manifest.json";
const PACKAGED_RUNTIME_MARKER_FILENAME: &str = ".codexify-packaged-runtime";
const PACKAGED_SETUP_DEFAULT_NEO4J_USER: &str = "neo4j";
const PACKAGED_SETUP_DEFAULT_NEO4J_PASS: &str = "codexify";
const PACKAGED_RUNTIME_REQUIRED_ASSETS: [&str; 12] = [
    ".env.example",
    ".env.template",
    "backend",
    "docker",
    "docker-compose.yml",
    "guardian",
    "plugins",
    "pytest.ini",
    "requirements",
    "requirements.txt",
    "scripts",
    "tests",
];
const PACKAGED_RUNTIME_PLACEHOLDER_DIRS: [&str; 3] =
    ["models", "models/bge-large-en-v1.5", ".chroma"];

#[cfg(target_os = "macos")]
const MACOS_DOCKER_APP_BUNDLE: &str = "/Applications/Docker.app";

#[cfg(target_os = "macos")]
const MACOS_DOCKER_CANDIDATES: [&str; 3] = [
    "/opt/homebrew/bin/docker",
    "/usr/local/bin/docker",
    "/Applications/Docker.app/Contents/Resources/bin/docker",
];

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopRuntimeConfig {
    pub mode: String,
    pub backend_base_url: String,
    pub api_base_url: String,
    pub sse_url: String,
    pub share_public_base_url: String,
    pub auth_mode: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopFetchedMedia {
    pub content_type: String,
    pub bytes_base64: String,
    pub size_bytes: usize,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct DesktopFetchMediaError {
    pub kind: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimePreflight {
    pub docker_cli_installed: bool,
    pub docker_compose_available: bool,
    pub docker_daemon_reachable: bool,
    pub ready: bool,
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_home: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub packaged: Option<bool>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapStepResult {
    pub ok: bool,
    pub step: String,
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_home: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub packaged: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stdout: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stderr: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exit_code: Option<i32>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct HealthEndpointCheck {
    pub endpoint: String,
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub status_code: Option<u16>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub response_excerpt: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct RuntimeReadiness {
    pub ok: bool,
    pub step: String,
    pub ready: bool,
    pub backend_reachable: bool,
    pub startup_ready: bool,
    pub redis_ready: bool,
    pub chat_ready: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub llm_ready: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_home: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub packaged: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    pub checks: Vec<HealthEndpointCheck>,
}

#[allow(dead_code)]
pub type RuntimeHealthCheckResult = RuntimeReadiness;

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapDockerOpenResult {
    pub ok: bool,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapLogResult {
    pub ok: bool,
    pub service: String,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_home: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub packaged: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub logs: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exit_code: Option<i32>,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapRestartResult {
    pub ok: bool,
    pub services: Vec<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub failure_kind: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_context: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub repo_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_home: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub runtime_root: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub packaged: Option<bool>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stdout: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub stderr: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub exit_code: Option<i32>,
}

#[derive(Debug, Clone, Copy)]
enum FailureKind {
    DockerBinaryNotFound,
    DockerCliExecutionFailed,
    DockerCliFoundButUnusableFromPackagedContext,
    DockerComposeUnavailable,
    DockerDaemonUnreachable,
    UnexpectedCommandExecutionError,
}

impl FailureKind {
    fn as_str(self) -> &'static str {
        match self {
            Self::DockerBinaryNotFound => FAILURE_KIND_DOCKER_CLI_UNAVAILABLE,
            Self::DockerCliExecutionFailed => FAILURE_KIND_DOCKER_CLI_EXECUTION_FAILED,
            Self::DockerCliFoundButUnusableFromPackagedContext => {
                FAILURE_KIND_DOCKER_CLI_FOUND_BUT_UNUSABLE_FROM_PACKAGED_CONTEXT
            }
            Self::DockerComposeUnavailable => "docker-compose-unavailable",
            Self::DockerDaemonUnreachable => FAILURE_KIND_DOCKER_DAEMON_UNAVAILABLE,
            Self::UnexpectedCommandExecutionError => FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR,
        }
    }

    fn summary(self) -> &'static str {
        match self {
            Self::DockerBinaryNotFound => "Docker CLI unavailable",
            Self::DockerCliExecutionFailed => "Docker CLI execution failed",
            Self::DockerCliFoundButUnusableFromPackagedContext => {
                "Docker CLI found but unusable from packaged context"
            }
            Self::DockerComposeUnavailable => "Docker Compose unavailable",
            Self::DockerDaemonUnreachable => "Docker daemon unavailable",
            Self::UnexpectedCommandExecutionError => "Unexpected command execution error",
        }
    }
}

#[derive(Debug, Clone)]
struct DockerCommandEnvironment {
    home: Option<String>,
    docker_config: Option<String>,
}

#[derive(Debug)]
struct ResolvedDockerBinary {
    command: String,
    display: String,
    resolution_detail: String,
    environment: DockerCommandEnvironment,
}

#[derive(Debug)]
struct CommandProbe {
    ok: bool,
    failure_kind: Option<FailureKind>,
    detail: String,
}

impl CommandProbe {
    fn success(detail: String) -> Self {
        Self {
            ok: true,
            failure_kind: None,
            detail,
        }
    }

    fn failure(kind: FailureKind, detail: String) -> Self {
        Self {
            ok: false,
            failure_kind: Some(kind),
            detail,
        }
    }

    fn skipped(detail: String) -> Self {
        Self {
            ok: false,
            failure_kind: None,
            detail,
        }
    }
}

#[derive(Debug)]
struct ParsedHttpUrl {
    host: String,
    port: u16,
    path: String,
}

#[derive(Debug)]
pub struct BootstrapRuntime {
    runtime_context: String,
    packaged: bool,
    runtime_root: Option<PathBuf>,
    repo_root: Option<PathBuf>,
    runtime_home: Option<PathBuf>,
    resource_root: Option<PathBuf>,
    resolution_detail: Option<String>,
    failure_kind: Option<String>,
}

impl BootstrapRuntime {
    fn success(
        runtime_context: &'static str,
        packaged: bool,
        runtime_root: PathBuf,
        repo_root: Option<PathBuf>,
        runtime_home: Option<PathBuf>,
        resource_root: Option<PathBuf>,
        resolution_detail: String,
    ) -> Self {
        Self {
            runtime_context: runtime_context.to_string(),
            packaged,
            runtime_root: Some(runtime_root),
            repo_root,
            runtime_home,
            resource_root,
            resolution_detail: Some(resolution_detail),
            failure_kind: None,
        }
    }

    fn failure(
        runtime_context: &'static str,
        packaged: bool,
        runtime_root: Option<PathBuf>,
        repo_root: Option<PathBuf>,
        runtime_home: Option<PathBuf>,
        resource_root: Option<PathBuf>,
        failure_kind: &'static str,
        detail: String,
    ) -> Self {
        Self {
            runtime_context: runtime_context.to_string(),
            packaged,
            runtime_root,
            repo_root,
            runtime_home,
            resource_root,
            resolution_detail: Some(detail),
            failure_kind: Some(failure_kind.to_string()),
        }
    }

    fn runtime_root_path(&self) -> Option<&Path> {
        self.runtime_root.as_deref()
    }

    fn runtime_home_display(&self) -> Option<String> {
        self.runtime_home
            .as_ref()
            .map(|path| path.display().to_string())
    }

    fn runtime_root_display(&self) -> Option<String> {
        self.runtime_root
            .as_ref()
            .map(|path| path.display().to_string())
    }

    fn repo_root_display(&self) -> Option<String> {
        self.repo_root
            .as_ref()
            .map(|path| path.display().to_string())
    }
}

#[derive(Debug)]
struct BootstrapRuntimeMaterializationError {
    failure_kind: &'static str,
    detail: String,
}

#[derive(Debug, Serialize)]
#[serde(rename_all = "camelCase")]
struct PackagedRuntimeManifest {
    schema_version: u8,
    app_version: String,
    runtime_context: String,
    packaged: bool,
    runtime_home: String,
    compose_file: String,
    env_file: String,
    env_template: String,
    env_example: String,
    resource_root: String,
    marker_file: String,
    attachment_state: String,
    bundled_assets: Vec<String>,
    placeholder_directories: Vec<String>,
}

fn compose_file_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join("docker-compose.yml")
}

fn runtime_env_file_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join(".env")
}

fn runtime_env_template_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join(".env.template")
}

fn runtime_env_example_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join(".env.example")
}

fn packaged_runtime_manifest_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join(PACKAGED_RUNTIME_MANIFEST_FILENAME)
}

fn packaged_runtime_marker_path(runtime_root: &Path) -> PathBuf {
    runtime_root.join(PACKAGED_RUNTIME_MARKER_FILENAME)
}

#[derive(Debug)]
struct BootstrapRuntimeValidationError {
    failure_kind: &'static str,
    detail: String,
}

fn phase_failure_kind(
    runtime: &BootstrapRuntime,
    packaged_kind: &'static str,
    development_kind: &'static str,
) -> &'static str {
    if runtime.packaged {
        packaged_kind
    } else {
        development_kind
    }
}

fn is_managed_packaged_runtime_root(runtime_root: &Path) -> bool {
    packaged_runtime_marker_path(runtime_root).is_file()
}

fn ensure_packaged_runtime_root_is_managed(
    runtime_root: &Path,
) -> Result<(), BootstrapRuntimeMaterializationError> {
    if !runtime_root.exists() {
        return Ok(());
    }

    if is_managed_packaged_runtime_root(runtime_root) {
        return Ok(());
    }

    Err(BootstrapRuntimeMaterializationError {
        failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
        detail: join_lines(vec![
            "Packaged runtime materialization refused to reuse an existing unmanaged runtime root."
                .to_string(),
            format!("runtimeRoot={}", runtime_root.display()),
            format!(
                "marker={}",
                packaged_runtime_marker_path(runtime_root).display()
            ),
            "Refusing to overwrite a pre-existing non-managed directory.".to_string(),
        ]),
    })
}

fn detect_docker_mount_path_rejection(text: &str) -> bool {
    let normalized = text.trim().to_ascii_lowercase();
    if normalized.is_empty() {
        return false;
    }

    normalized.contains("mounts denied")
        || normalized.contains("mount denied")
        || normalized.contains("path is not shared")
        || normalized.contains("paths are not shared")
        || normalized.contains("is not shared from the host")
        || normalized.contains("sharing is not enabled")
        || normalized.contains("file sharing")
}

fn path_exists(path: &Path) -> bool {
    path.exists()
}

fn copy_file_to_runtime(source: &Path, destination: &Path) -> Result<(), String> {
    if let Some(parent) = destination.parent() {
        fs::create_dir_all(parent).map_err(|err| {
            format!(
                "Failed to create runtime parent {}: {err}",
                parent.display()
            )
        })?;
    }

    fs::copy(source, destination).map_err(|err| {
        format!(
            "Failed to copy resource {} -> {}: {err}",
            source.display(),
            destination.display()
        )
    })?;

    Ok(())
}

fn copy_dir_all(source: &Path, destination: &Path) -> Result<(), String> {
    if !source.is_dir() {
        return Err(format!("Resource directory missing: {}", source.display()));
    }

    fs::create_dir_all(destination).map_err(|err| {
        format!(
            "Failed to create runtime directory {}: {err}",
            destination.display()
        )
    })?;

    for entry in fs::read_dir(source).map_err(|err| {
        format!(
            "Failed to read resource directory {}: {err}",
            source.display()
        )
    })? {
        let entry = entry.map_err(|err| {
            format!(
                "Failed to inspect resource entry under {}: {err}",
                source.display()
            )
        })?;
        let source_path = entry.path();
        let destination_path = destination.join(entry.file_name());
        let file_type = entry.file_type().map_err(|err| {
            format!(
                "Failed to inspect resource type {}: {err}",
                source_path.display()
            )
        })?;

        if file_type.is_dir() {
            copy_dir_all(&source_path, &destination_path)?;
        } else if file_type.is_file() {
            copy_file_to_runtime(&source_path, &destination_path)?;
        } else if file_type.is_symlink() {
            let metadata = fs::metadata(&source_path).map_err(|err| {
                format!(
                    "Failed to resolve symbolic resource {}: {err}",
                    source_path.display()
                )
            })?;
            if metadata.is_dir() {
                copy_dir_all(&source_path, &destination_path)?;
            } else if metadata.is_file() {
                copy_file_to_runtime(&source_path, &destination_path)?;
            } else {
                return Err(format!(
                    "Unsupported packaged resource type at {}",
                    source_path.display()
                ));
            }
        }
    }

    Ok(())
}

fn write_packaged_runtime_manifest(
    resource_root: &Path,
    runtime_root: &Path,
    attachment_state: &str,
) -> Result<PathBuf, BootstrapRuntimeMaterializationError> {
    let manifest_path = packaged_runtime_manifest_path(runtime_root);
    let marker_path = packaged_runtime_marker_path(runtime_root);
    let manifest = PackagedRuntimeManifest {
        schema_version: 1,
        app_version: env!("CARGO_PKG_VERSION").to_string(),
        runtime_context: RUNTIME_CONTEXT_PACKAGED.to_string(),
        packaged: true,
        runtime_home: runtime_root.display().to_string(),
        compose_file: compose_file_path(runtime_root).display().to_string(),
        env_file: runtime_env_file_path(runtime_root).display().to_string(),
        env_template: runtime_env_template_path(runtime_root)
            .display()
            .to_string(),
        env_example: runtime_env_example_path(runtime_root).display().to_string(),
        resource_root: resource_root.display().to_string(),
        marker_file: marker_path.display().to_string(),
        attachment_state: attachment_state.to_string(),
        bundled_assets: PACKAGED_RUNTIME_REQUIRED_ASSETS
            .iter()
            .map(|path| path.to_string())
            .collect(),
        placeholder_directories: PACKAGED_RUNTIME_PLACEHOLDER_DIRS
            .iter()
            .map(|path| path.to_string())
            .collect(),
    };
    let manifest_body = serde_json::to_string_pretty(&manifest).map_err(|err| {
        BootstrapRuntimeMaterializationError {
            failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
            detail: join_lines(vec![
                "Packaged runtime materialization failed while serializing the runtime manifest."
                    .to_string(),
                format!("runtimeHome={}", runtime_root.display()),
                format!("manifest={}", manifest_path.display()),
                format!("error={err}"),
            ]),
        }
    })?;

    fs::write(&manifest_path, manifest_body).map_err(|err| {
        BootstrapRuntimeMaterializationError {
            failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
            detail: join_lines(vec![
                "Packaged runtime materialization failed while writing the runtime manifest."
                    .to_string(),
                format!("runtimeHome={}", runtime_root.display()),
                format!("manifest={}", manifest_path.display()),
                format!("error={err}"),
            ]),
        }
    })?;

    Ok(manifest_path)
}

fn validate_packaged_runtime_attachment(
    runtime_root: &Path,
) -> Result<(), BootstrapRuntimeMaterializationError> {
    let mut missing_runtime_assets = Vec::new();

    for relative_path in PACKAGED_RUNTIME_REQUIRED_ASSETS {
        let runtime_path = runtime_root.join(relative_path);
        if !path_exists(&runtime_path) {
            missing_runtime_assets.push(relative_path.to_string());
        }
    }

    for placeholder in PACKAGED_RUNTIME_PLACEHOLDER_DIRS {
        let runtime_path = runtime_root.join(placeholder);
        if !runtime_path.is_dir() {
            missing_runtime_assets.push(placeholder.to_string());
        }
    }

    let marker_path = packaged_runtime_marker_path(runtime_root);
    if !marker_path.is_file() {
        missing_runtime_assets.push(PACKAGED_RUNTIME_MARKER_FILENAME.to_string());
    }

    let manifest_path = packaged_runtime_manifest_path(runtime_root);
    if !manifest_path.is_file() {
        missing_runtime_assets.push(PACKAGED_RUNTIME_MANIFEST_FILENAME.to_string());
    }

    if missing_runtime_assets.is_empty() {
        return Ok(());
    }

    Err(BootstrapRuntimeMaterializationError {
        failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_CORRUPT,
        detail: join_lines(vec![
            "The packaged runtime home is missing materialized runtime assets after refresh."
                .to_string(),
            format!("runtimeHome={}", runtime_root.display()),
            format!("missingRuntimeAssets={}", missing_runtime_assets.join(",")),
        ]),
    })
}

fn materialize_packaged_runtime_assets(
    resource_root: &Path,
    runtime_root: &Path,
) -> Result<Vec<String>, BootstrapRuntimeMaterializationError> {
    let mut detail_lines = vec![
        format!("resourceRoot={}", resource_root.display()),
        format!("runtimeRoot={}", runtime_root.display()),
    ];
    let runtime_manifest_path = packaged_runtime_manifest_path(runtime_root);
    let marker_path = packaged_runtime_marker_path(runtime_root);
    let attachment_state = if runtime_manifest_path.is_file() && marker_path.is_file() {
        "refresh"
    } else {
        "first-run"
    };
    detail_lines.push(format!("attachmentState={attachment_state}"));

    ensure_packaged_runtime_root_is_managed(runtime_root)?;

    fs::create_dir_all(runtime_root).map_err(|err| BootstrapRuntimeMaterializationError {
        failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
        detail: join_lines(vec![
            "Packaged runtime root is unavailable.".to_string(),
            format!("runtimeRoot={}", runtime_root.display()),
            format!("error={err}"),
        ]),
    })?;

    for placeholder in PACKAGED_RUNTIME_PLACEHOLDER_DIRS {
        let placeholder_path = runtime_root.join(placeholder);
        fs::create_dir_all(&placeholder_path).map_err(|err| {
            BootstrapRuntimeMaterializationError {
                failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
                detail: join_lines(vec![
                "Packaged runtime materialization failed while creating placeholder directories."
                    .to_string(),
                format!("runtimeRoot={}", runtime_root.display()),
                format!("placeholder={}", placeholder_path.display()),
                format!("error={err}"),
            ]),
            }
        })?;
    }

    let mut missing_assets = Vec::new();
    for relative_path in PACKAGED_RUNTIME_REQUIRED_ASSETS {
        let source_path = resource_root.join(relative_path);
        let destination_path = runtime_root.join(relative_path);
        if !path_exists(&source_path) {
            missing_assets.push(relative_path.to_string());
            continue;
        }

        let metadata =
            fs::metadata(&source_path).map_err(|err| BootstrapRuntimeMaterializationError {
                failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
                detail: join_lines(vec![
                    "Packaged runtime materialization failed while inspecting a resource."
                        .to_string(),
                    format!("resource={}", source_path.display()),
                    format!("error={err}"),
                ]),
            })?;

        if metadata.is_dir() {
            copy_dir_all(&source_path, &destination_path).map_err(|detail| {
                BootstrapRuntimeMaterializationError {
                    failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
                    detail: join_lines(vec![
                        "Packaged runtime materialization failed while copying a resource directory."
                            .to_string(),
                        detail,
                    ]),
                }
            })?;
        } else if metadata.is_file() {
            copy_file_to_runtime(&source_path, &destination_path).map_err(|detail| {
                BootstrapRuntimeMaterializationError {
                    failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
                    detail: join_lines(vec![
                        "Packaged runtime materialization failed while copying a resource file."
                            .to_string(),
                        detail,
                    ]),
                }
            })?;
        } else {
            missing_assets.push(relative_path.to_string());
        }
    }

    if !missing_assets.is_empty() {
        detail_lines.push(format!("missingAssets={}", missing_assets.join(",")));
        detail_lines.push(
            "The packaged app bundle is missing the runtime source payload needed to bootstrap safely."
                .to_string(),
        );
        return Err(BootstrapRuntimeMaterializationError {
            failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_MISSING,
            detail: join_lines(detail_lines),
        });
    }

    let manifest_path =
        write_packaged_runtime_manifest(resource_root, runtime_root, attachment_state)?;
    let marker_contents = join_lines(vec![
        format!("version={}", env!("CARGO_PKG_VERSION")),
        format!("attachmentState={attachment_state}"),
        format!("resourceRoot={}", resource_root.display()),
        format!("runtimeRoot={}", runtime_root.display()),
        format!("runtimeHome={}", runtime_root.display()),
        format!("manifest={}", manifest_path.display()),
    ]);
    fs::write(&marker_path, marker_contents).map_err(|err| {
        BootstrapRuntimeMaterializationError {
            failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED,
            detail: join_lines(vec![
                "Packaged runtime materialization failed while writing the runtime marker."
                    .to_string(),
                format!("runtimeRoot={}", runtime_root.display()),
                format!("marker={}", marker_path.display()),
                format!("error={err}"),
            ]),
        }
    })?;

    validate_packaged_runtime_attachment(runtime_root)?;

    detail_lines.push(format!("manifest={}", manifest_path.display()));
    detail_lines.push(format!(
        "composeFile={}",
        compose_file_path(runtime_root).display()
    ));
    detail_lines.push(format!(
        "runtimeEnvTemplate={}",
        runtime_env_template_path(runtime_root).display()
    ));
    detail_lines.push(format!(
        "runtimeEnvExample={}",
        runtime_env_example_path(runtime_root).display()
    ));
    detail_lines.push("materialization=complete".to_string());
    Ok(detail_lines)
}

fn env_first(keys: &[&str], fallback: &str) -> String {
    for key in keys {
        if let Ok(value) = env::var(key) {
            let trimmed = value.trim();
            if !trimmed.is_empty() {
                return trimmed.to_string();
            }
        }
    }
    fallback.to_string()
}

fn desktop_backend_base_url() -> String {
    trim_trailing_slash(&env_first(
        &[
            "CODEXIFY_DESKTOP_BACKEND_URL",
            "VITE_GUARDIAN_API_BASE",
            "GUARDIAN_API_BASE",
        ],
        "http://127.0.0.1:8888",
    ))
}

fn desktop_fetch_media_error(kind: &str, detail: impl Into<String>) -> DesktopFetchMediaError {
    DesktopFetchMediaError {
        kind: kind.to_string(),
        detail: Some(detail.into()),
    }
}

fn normalize_desktop_media_fetch_path(raw: &str) -> Result<String, DesktopFetchMediaError> {
    let trimmed = raw.trim();
    if trimmed.is_empty()
        || !trimmed.starts_with("/media/")
        || trimmed.contains("..")
        || trimmed.contains('?')
        || trimmed.contains('#')
    {
        return Err(desktop_fetch_media_error(
            "invalid_path",
            "Desktop media fetch requires a canonical /media/... path.",
        ));
    }
    Ok(trimmed.to_string())
}

fn desktop_media_signing_secret() -> Result<String, DesktopFetchMediaError> {
    let env_secret = env_first(
        &[
            "GUARDIAN_MEDIA_URL_SECRET",
            "GUARDIAN_SESSION_SECRET",
            "GUARDIAN_API_KEY",
            "VITE_GUARDIAN_API_KEY",
        ],
        "",
    );
    if !env_secret.trim().is_empty() {
        return Ok(env_secret.trim().to_string());
    }
    match read_keychain_password() {
        Ok(Some(value)) if !value.trim().is_empty() => Ok(value.trim().to_string()),
        Ok(_) => Err(desktop_fetch_media_error(
            "fetch_failed",
            "Desktop media signing secret unavailable.",
        )),
        Err(detail) => Err(desktop_fetch_media_error("fetch_failed", detail)),
    }
}

fn desktop_media_signature_for_path(
    path: &str,
    secret: &str,
) -> Result<String, DesktopFetchMediaError> {
    let mut mac = Hmac::<Sha256>::new_from_slice(secret.as_bytes()).map_err(|_| {
        desktop_fetch_media_error(
            "fetch_failed",
            "Unable to initialize desktop media signature state.",
        )
    })?;
    mac.update(path.as_bytes());
    Ok(URL_SAFE_NO_PAD.encode(mac.finalize().into_bytes()))
}

fn desktop_signed_media_url(
    backend_base_url: &str,
    path: &str,
) -> Result<String, DesktopFetchMediaError> {
    let secret = desktop_media_signing_secret()?;
    let signature = desktop_media_signature_for_path(path, &secret)?;
    Ok(combine_url(
        backend_base_url,
        &format!("{path}?sig={signature}"),
    ))
}

fn desktop_media_response_content_type(
    response: &reqwest::Response,
) -> Result<String, DesktopFetchMediaError> {
    let header_value = response
        .headers()
        .get(CONTENT_TYPE)
        .and_then(|value| value.to_str().ok())
        .map(|value| value.trim().to_string())
        .unwrap_or_default();
    desktop_media_content_type_guard(&header_value)?;
    Ok(header_value)
}

fn desktop_media_content_type_guard(header_value: &str) -> Result<(), DesktopFetchMediaError> {
    let normalized = header_value
        .split(';')
        .next()
        .map(|value| value.trim().to_ascii_lowercase())
        .unwrap_or_default();
    if normalized.starts_with("image/") {
        Ok(())
    } else {
        Err(desktop_fetch_media_error(
            "type_not_allowed",
            format!(
                "Desktop media fetch only supports image/* responses (got {}).",
                if header_value.is_empty() {
                    "<missing>"
                } else {
                    header_value.as_str()
                }
            ),
        ))
    }
}

fn desktop_media_size_guard(size_bytes: usize) -> Result<(), DesktopFetchMediaError> {
    if size_bytes > DESKTOP_MEDIA_MAX_BYTES {
        return Err(desktop_fetch_media_error(
            "too_large",
            format!(
                "Desktop media fetch exceeded {} bytes.",
                DESKTOP_MEDIA_MAX_BYTES
            ),
        ));
    }
    Ok(())
}

fn trim_trailing_slash(raw: &str) -> String {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return String::new();
    }
    trimmed.trim_end_matches('/').to_string()
}

fn combine_url(base: &str, path: &str) -> String {
    let clean_base = trim_trailing_slash(base);
    let clean_path = path.trim();
    if clean_path.is_empty() {
        return clean_base;
    }
    let normalized_path = if clean_path.starts_with('/') {
        clean_path.to_string()
    } else {
        format!("/{}", clean_path)
    };
    format!("{clean_base}{normalized_path}")
}

fn resolve_api_base_url(backend_base_url: &str) -> String {
    let configured = env_first(&["CODEXIFY_DESKTOP_API_BASE_URL", "VITE_API_BASE_URL"], "");
    if configured.is_empty() {
        return combine_url(backend_base_url, "/api");
    }
    if configured.starts_with("http://") || configured.starts_with("https://") {
        return trim_trailing_slash(&configured);
    }
    if configured.starts_with('/') {
        return combine_url(backend_base_url, &configured);
    }
    combine_url(backend_base_url, &format!("/{}", configured))
}

fn resolve_share_public_base_url(backend_base_url: &str) -> String {
    let configured = env_first(
        &[
            "CODEXIFY_DESKTOP_SHARE_BASE_URL",
            "VITE_SHARE_PUBLIC_BASE_URL",
        ],
        "",
    );
    if configured.is_empty() {
        return "http://127.0.0.1:5173".to_string();
    }
    if configured.starts_with("http://") || configured.starts_with("https://") {
        return trim_trailing_slash(&configured);
    }
    if configured.starts_with('/') {
        return combine_url(backend_base_url, &configured);
    }
    combine_url(backend_base_url, &format!("/{}", configured))
}

fn join_lines(lines: Vec<String>) -> String {
    lines
        .into_iter()
        .filter(|line| !line.trim().is_empty())
        .collect::<Vec<_>>()
        .join("\n")
}

fn normalize_output(bytes: &[u8]) -> Option<String> {
    let trimmed = String::from_utf8_lossy(bytes).trim().to_string();
    if trimmed.is_empty() {
        None
    } else {
        Some(trimmed)
    }
}

fn parse_env_entry(raw: &str) -> Option<(String, String)> {
    let line = raw.trim();
    if line.is_empty() || line.starts_with('#') || !line.contains('=') {
        return None;
    }

    let mut parts = line.splitn(2, '=');
    let key = parts.next()?.trim().to_string();
    let mut value = parts.next()?.trim().to_string();
    if value.len() >= 2
        && ((value.starts_with('"') && value.ends_with('"'))
            || (value.starts_with('\'') && value.ends_with('\'')))
    {
        value = value[1..value.len() - 1].to_string();
    }

    Some((key, value))
}

fn read_env_file_ordered(
    env_path: &Path,
) -> Result<(Vec<String>, BTreeMap<String, String>), String> {
    let mut order = Vec::new();
    let mut values = BTreeMap::new();
    if !env_path.is_file() {
        return Ok((order, values));
    }

    let contents = fs::read_to_string(env_path)
        .map_err(|err| format!("Failed to read env file {}: {err}", env_path.display()))?;
    for raw_line in contents.lines() {
        if let Some((key, value)) = parse_env_entry(raw_line) {
            if !order.iter().any(|existing| existing == &key) {
                order.push(key.clone());
            }
            values.insert(key, value);
        }
    }

    Ok((order, values))
}

fn sanitize_env_value(value: &str) -> String {
    if value.contains(' ') || value.contains('#') {
        format!("\"{}\"", value.replace('\\', "\\\\").replace('"', "\\\""))
    } else {
        value.to_string()
    }
}

fn push_ordered_key(order: &mut Vec<String>, key: &str) {
    if !order.iter().any(|existing| existing == key) {
        order.push(key.to_string());
    }
}

fn generate_bootstrap_secret_hex(byte_len: usize) -> Result<String, String> {
    let mut bytes = vec![0_u8; byte_len];
    fs::File::open("/dev/urandom")
        .and_then(|mut file| file.read_exact(&mut bytes))
        .map_err(|err| format!("Failed to generate a packaged bootstrap secret: {err}"))?;
    Ok(bytes
        .iter()
        .map(|byte| format!("{byte:02x}"))
        .collect::<String>())
}

#[derive(Debug)]
struct PackagedSetupEnvResult {
    env_path: PathBuf,
    preserved_keys: Vec<String>,
    generated_guardian_api_key: bool,
    created_new_env_file: bool,
    migrated_legacy_env_source: Option<PathBuf>,
    migrated_legacy_runtime_assets: Vec<String>,
}

fn migrate_packaged_setup_env(
    runtime_home: Option<&Path>,
    runtime_root: &Path,
) -> Result<Option<PathBuf>, BootstrapRuntimeValidationError> {
    let Some(runtime_home) = runtime_home else {
        return Ok(None);
    };

    let source_env_path = runtime_env_file_path(runtime_home);
    let destination_env_path = runtime_env_file_path(runtime_root);

    if destination_env_path.exists() || !source_env_path.is_file() {
        return Ok(None);
    }

    if let Some(parent) = destination_env_path.parent() {
        fs::create_dir_all(parent).map_err(|err| BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            detail: format!(
                "Failed to prepare packaged env directory {}: {err}",
                parent.display()
            ),
        })?;
    }

    fs::copy(&source_env_path, &destination_env_path).map_err(|err| {
        BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            detail: format!(
                "Failed to migrate packaged env {} -> {}: {err}",
                source_env_path.display(),
                destination_env_path.display()
            ),
        }
    })?;

    Ok(Some(source_env_path))
}

fn migrate_packaged_setup_runtime_dir(
    runtime_home: Option<&Path>,
    runtime_root: &Path,
    relative_path: &str,
) -> Result<Option<PathBuf>, BootstrapRuntimeValidationError> {
    let Some(runtime_home) = runtime_home else {
        return Ok(None);
    };

    let source_path = runtime_home.join(relative_path);
    let destination_path = runtime_root.join(relative_path);
    if !source_path.is_dir() {
        return Ok(None);
    }

    if destination_path.exists() {
        if !destination_path.is_dir() {
            return Err(BootstrapRuntimeValidationError {
                failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
                detail: format!(
                    "Packaged runtime migration expected {} to be a directory.",
                    destination_path.display()
                ),
            });
        }

        let mut entries =
            fs::read_dir(&destination_path).map_err(|err| BootstrapRuntimeValidationError {
                failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
                detail: format!(
                    "Failed to inspect packaged runtime destination {}: {err}",
                    destination_path.display()
                ),
            })?;
        if entries.next().is_some() {
            return Ok(None);
        }
    }

    copy_dir_all(&source_path, &destination_path).map_err(|detail| {
        BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            detail,
        }
    })?;

    Ok(Some(source_path))
}

fn materialize_packaged_setup_env(
    runtime_home: Option<&Path>,
    runtime_root: &Path,
) -> Result<PackagedSetupEnvResult, BootstrapRuntimeValidationError> {
    let env_path = runtime_env_file_path(runtime_root);
    let migrated_legacy_env_source = migrate_packaged_setup_env(runtime_home, runtime_root)?;
    let mut migrated_legacy_runtime_assets = Vec::new();
    for asset in [".chroma", "models"] {
        if migrate_packaged_setup_runtime_dir(runtime_home, runtime_root, asset)?.is_some() {
            migrated_legacy_runtime_assets.push(asset.to_string());
        }
    }
    let (mut order, mut values) =
        read_env_file_ordered(&env_path).map_err(|detail| BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            detail,
        })?;
    let created_new_env_file = !env_path.exists();
    let preserved_keys = values.keys().cloned().collect::<Vec<_>>();

    let existing_guardian_api_key = values
        .get("GUARDIAN_API_KEY")
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty());
    let generated_guardian_api_key = existing_guardian_api_key.is_none();
    let guardian_api_key = match existing_guardian_api_key {
        Some(value) => value,
        None => {
            generate_bootstrap_secret_hex(32).map_err(|detail| BootstrapRuntimeValidationError {
                failure_kind: FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR,
                detail,
            })?
        }
    };

    values.insert("GUARDIAN_API_KEY".to_string(), guardian_api_key.clone());
    values.insert("VITE_GUARDIAN_API_KEY".to_string(), guardian_api_key);

    let defaults = [
        ("GUARDIAN_AUTH_MODE", "local"),
        ("CODEXIFY_DESKTOP_BACKEND_URL", "http://127.0.0.1:8888"),
        ("CODEXIFY_DESKTOP_SHARE_BASE_URL", "http://127.0.0.1:5173"),
        ("NEO4J_USER", PACKAGED_SETUP_DEFAULT_NEO4J_USER),
        ("NEO4J_PASS", PACKAGED_SETUP_DEFAULT_NEO4J_PASS),
    ];

    for (key, default_value) in defaults {
        let replace_value = values
            .get(key)
            .map(|value| value.trim().is_empty())
            .unwrap_or(true);
        if replace_value {
            values.insert(key.to_string(), default_value.to_string());
        }
        push_ordered_key(&mut order, key);
    }
    push_ordered_key(&mut order, "GUARDIAN_API_KEY");
    push_ordered_key(&mut order, "VITE_GUARDIAN_API_KEY");

    let mut lines = vec![
        "# Generated by Codexify packaged setup".to_string(),
        "# Safe to edit. Re-running packaged setup preserves existing keys and backfills required runtime values."
            .to_string(),
    ];
    let mut written = HashSet::new();
    for key in &order {
        if let Some(value) = values.get(key) {
            lines.push(format!("{key}={}", sanitize_env_value(value)));
            written.insert(key.clone());
        }
    }
    for (key, value) in &values {
        if written.contains(key) {
            continue;
        }
        lines.push(format!("{key}={}", sanitize_env_value(value)));
    }
    lines.push(String::new());

    fs::write(&env_path, lines.join("\n")).map_err(|err| BootstrapRuntimeValidationError {
        failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
        detail: format!(
            "Failed to write packaged env file {}: {err}",
            env_path.display()
        ),
    })?;

    Ok(PackagedSetupEnvResult {
        env_path,
        preserved_keys,
        generated_guardian_api_key,
        created_new_env_file,
        migrated_legacy_env_source,
        migrated_legacy_runtime_assets,
    })
}

fn render_probe_output(stdout: &[u8], stderr: &[u8]) -> Vec<String> {
    let mut lines = Vec::new();
    if let Some(stdout) = normalize_output(stdout) {
        lines.push(format!("stdout: {stdout}"));
    }
    if let Some(stderr) = normalize_output(stderr) {
        lines.push(format!("stderr: {stderr}"));
    }
    lines
}

fn normalize_bootstrap_service(service: &str) -> Result<&'static str, String> {
    let trimmed = service.trim();
    BOOTSTRAP_LOG_SERVICES
        .iter()
        .copied()
        .find(|candidate| candidate.eq_ignore_ascii_case(trimmed))
        .ok_or_else(|| {
            format!(
                "Unsupported bootstrap log service `{trimmed}`. Supported services: {}.",
                BOOTSTRAP_LOG_SERVICES.join(", ")
            )
        })
}

fn resolve_development_bootstrap_runtime() -> BootstrapRuntime {
    let current_exe = match env::current_exe() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapRuntime::failure(
                RUNTIME_CONTEXT_DEVELOPMENT,
                false,
                None,
                None,
                None,
                None,
                FAILURE_KIND_RUNTIME_PATH_UNAVAILABLE,
                join_lines(vec![
                    "runtime repo resolution: failed".to_string(),
                    format!("currentExeError={err}"),
                ]),
            );
        }
    };

    let mut detail_lines = vec![
        "runtime repo resolution:".to_string(),
        format!("runtimeContext={RUNTIME_CONTEXT_DEVELOPMENT}"),
        "packaged=false".to_string(),
        format!("currentExe={}", current_exe.display()),
    ];

    if let Ok(current_dir) = env::current_dir() {
        detail_lines.push(format!("currentDir={}", current_dir.display()));
    }

    if let Some(override_root) = env::var_os("CODEXIFY_DESKTOP_REPO_ROOT") {
        let override_path = PathBuf::from(override_root);
        detail_lines.push(format!("repoRootOverride={}", override_path.display()));

        if is_repo_runtime_root(&override_path) {
            detail_lines.push("repo root resolved from CODEXIFY_DESKTOP_REPO_ROOT.".to_string());
            return BootstrapRuntime::success(
                RUNTIME_CONTEXT_DEVELOPMENT,
                false,
                override_path.clone(),
                Some(override_path),
                None,
                None,
                join_lines(detail_lines),
            );
        }

        detail_lines.push(
            "The explicit CODEXIFY_DESKTOP_REPO_ROOT override did not contain the required Codexify runtime files."
                .to_string(),
        );
        return BootstrapRuntime::failure(
            RUNTIME_CONTEXT_DEVELOPMENT,
            false,
            None,
            None,
            None,
            None,
            FAILURE_KIND_REPO_RUNTIME_MISSING,
            join_lines(detail_lines),
        );
    }

    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let manifest_candidate = manifest_dir
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| manifest_dir.clone());

    detail_lines.push(format!(
        "manifestCandidate={}",
        manifest_candidate.display()
    ));
    if let Some(repo_root) = find_repo_root_from_ancestors(&manifest_candidate) {
        detail_lines.push(format!(
            "repo root resolved from cargo manifest ancestors: {}",
            repo_root.display()
        ));
        return BootstrapRuntime::success(
            RUNTIME_CONTEXT_DEVELOPMENT,
            false,
            repo_root.clone(),
            Some(repo_root),
            None,
            None,
            join_lines(detail_lines),
        );
    }

    if let Ok(current_dir) = env::current_dir() {
        if let Some(repo_root) = find_repo_root_from_ancestors(&current_dir) {
            detail_lines.push(format!(
                "repo root resolved from working directory ancestors: {}",
                repo_root.display()
            ));
            return BootstrapRuntime::success(
                RUNTIME_CONTEXT_DEVELOPMENT,
                false,
                repo_root.clone(),
                Some(repo_root),
                None,
                None,
                join_lines(detail_lines),
            );
        }
    }

    detail_lines.push(
        "Unable to resolve the Codexify repo root from the active development runtime.".to_string(),
    );
    BootstrapRuntime::failure(
        RUNTIME_CONTEXT_DEVELOPMENT,
        false,
        None,
        None,
        None,
        None,
        FAILURE_KIND_REPO_RUNTIME_MISSING,
        join_lines(detail_lines),
    )
}

fn resolve_packaged_bootstrap_runtime(
    app: &tauri::AppHandle,
    current_exe: &Path,
    packaged_bundle: &Path,
) -> BootstrapRuntime {
    let mut detail_lines = vec![
        "runtime repo resolution:".to_string(),
        format!("runtimeContext={RUNTIME_CONTEXT_PACKAGED}"),
        "packaged=true".to_string(),
        format!("currentExe={}", current_exe.display()),
        format!("appBundle={}", packaged_bundle.display()),
    ];

    if let Ok(current_dir) = env::current_dir() {
        detail_lines.push(format!("currentDir={}", current_dir.display()));
    }

    let runtime_home = match app.path().data_dir() {
        Ok(data_dir) => data_dir.join(PACKAGED_RUNTIME_METADATA_DIRNAME),
        Err(err) => {
            detail_lines.push(
                "The packaged app could not resolve its Application Support metadata home."
                    .to_string(),
            );
            detail_lines.push(format!("runtimeHomeError={err}"));
            return BootstrapRuntime::failure(
                RUNTIME_CONTEXT_PACKAGED,
                true,
                None,
                None,
                None,
                None,
                FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
                join_lines(detail_lines),
            );
        }
    };
    detail_lines.push(format!("runtimeHome={}", runtime_home.display()));

    if let Err(err) = fs::create_dir_all(&runtime_home) {
        detail_lines.push(
            "The packaged app could not create its Application Support metadata home.".to_string(),
        );
        detail_lines.push(format!("runtimeHomeCreateError={err}"));
        return BootstrapRuntime::failure(
            RUNTIME_CONTEXT_PACKAGED,
            true,
            None,
            None,
            Some(runtime_home),
            None,
            FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            join_lines(detail_lines),
        );
    }

    let runtime_root = match app.path().home_dir() {
        Ok(home_dir) => home_dir.join(PACKAGED_RUNTIME_ROOT_DIRNAME),
        Err(err) => {
            detail_lines.push(
                "The packaged app could not resolve a Docker-compatible runtime root under the user home."
                    .to_string(),
            );
            detail_lines.push(format!("runtimeRootError={err}"));
            return BootstrapRuntime::failure(
                RUNTIME_CONTEXT_PACKAGED,
                true,
                None,
                None,
                Some(runtime_home),
                None,
                FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
                join_lines(detail_lines),
            );
        }
    };
    detail_lines.push(format!("runtimeRoot={}", runtime_root.display()));

    let resource_root = match app.path().resource_dir() {
        Ok(path) => path,
        Err(err) => {
            detail_lines.push(
                "The packaged app could not resolve its bundled resource directory.".to_string(),
            );
            detail_lines.push(format!("resourceRootError={err}"));
            return BootstrapRuntime::failure(
                RUNTIME_CONTEXT_PACKAGED,
                true,
                Some(runtime_root.clone()),
                None,
                Some(runtime_home),
                None,
                FAILURE_KIND_PACKAGED_BOOTSTRAP_UNSUPPORTED,
                join_lines(detail_lines),
            );
        }
    };
    detail_lines.push(format!("resourceRoot={}", resource_root.display()));

    match materialize_packaged_runtime_assets(&resource_root, &runtime_root) {
        Ok(materialization_detail) => {
            detail_lines.extend(materialization_detail);
            BootstrapRuntime::success(
                RUNTIME_CONTEXT_PACKAGED,
                true,
                runtime_root,
                None,
                Some(runtime_home),
                Some(resource_root),
                join_lines(detail_lines),
            )
        }
        Err(err) => BootstrapRuntime::failure(
            RUNTIME_CONTEXT_PACKAGED,
            true,
            Some(runtime_root),
            None,
            Some(runtime_home),
            Some(resource_root),
            err.failure_kind,
            join_lines(vec![join_lines(detail_lines), err.detail]),
        ),
    }
}

pub fn resolve_bootstrap_runtime(app: &tauri::AppHandle) -> BootstrapRuntime {
    let current_exe = match env::current_exe() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapRuntime::failure(
                RUNTIME_CONTEXT_DEVELOPMENT,
                false,
                None,
                None,
                None,
                None,
                FAILURE_KIND_RUNTIME_PATH_UNAVAILABLE,
                join_lines(vec![
                    "runtime repo resolution: failed".to_string(),
                    format!("currentExeError={err}"),
                ]),
            );
        }
    };

    let packaged_bundle = find_macos_app_bundle(&current_exe);
    if let Some(bundle) = packaged_bundle {
        return resolve_packaged_bootstrap_runtime(app, &current_exe, &bundle);
    }

    resolve_development_bootstrap_runtime()
}

fn resolve_runtime_root_for_step(
    runtime: &BootstrapRuntime,
    step: &str,
) -> Result<PathBuf, BootstrapStepResult> {
    match runtime.runtime_root_path() {
        Some(path) => Ok(path.to_path_buf()),
        None => Err(BootstrapStepResult {
            ok: false,
            step: step.to_string(),
            detail: runtime.resolution_detail.clone(),
            failure_kind: runtime.failure_kind.clone(),
            runtime_context: Some(runtime.runtime_context.clone()),
            repo_root: runtime.repo_root_display(),
            runtime_home: runtime.runtime_home_display(),
            runtime_root: runtime.runtime_root_display(),
            packaged: Some(runtime.packaged),
            command: None,
            stdout: None,
            stderr: None,
            exit_code: None,
        }),
    }
}

fn validate_packaged_runtime(
    runtime: &BootstrapRuntime,
    step: &str,
    required_assets: &[&str],
) -> Result<(), BootstrapRuntimeValidationError> {
    if !runtime.packaged {
        return Ok(());
    }

    let runtime_root =
        runtime
            .runtime_root_path()
            .ok_or_else(|| BootstrapRuntimeValidationError {
                failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
                detail: join_lines(vec![
                    format!("Packaged {step} could not resolve a usable runtime root."),
                    format!("runtimeContext={}", runtime.runtime_context),
                    format!("packaged={}", runtime.packaged),
                    runtime
                        .runtime_home
                        .as_ref()
                        .map(|path| format!("runtimeHome={}", path.display()))
                        .unwrap_or_default(),
                    runtime.resolution_detail.clone().unwrap_or_else(|| {
                        "Packaged runtime resolution detail unavailable.".to_string()
                    }),
                ]),
            })?;
    let runtime_home = runtime
        .runtime_home
        .as_ref()
        .cloned()
        .unwrap_or_else(|| runtime_root.to_path_buf());

    fs::create_dir_all(&runtime_home).map_err(|err| BootstrapRuntimeValidationError {
        failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
        detail: join_lines(vec![
            format!("Packaged {step} could not use the packaged metadata home."),
            format!("runtimeRoot={}", runtime_root.display()),
            format!("runtimeHome={}", runtime_home.display()),
            format!("error={err}"),
        ]),
    })?;

    if !runtime_home.is_dir() {
        return Err(BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_RUNTIME_ROOT_UNAVAILABLE,
            detail: join_lines(vec![
                format!("Packaged {step} expected a directory-backed metadata home."),
                format!("runtimeRoot={}", runtime_root.display()),
                format!("runtimeHome={}", runtime_home.display()),
            ]),
        });
    }

    let marker_path = runtime_root.join(PACKAGED_RUNTIME_MARKER_FILENAME);
    let mut invalid_assets = Vec::new();
    if !marker_path.is_file() {
        invalid_assets.push(PACKAGED_RUNTIME_MARKER_FILENAME.to_string());
    }
    for relative_path in required_assets {
        let candidate = runtime_root.join(relative_path);
        if !candidate.exists() {
            invalid_assets.push(relative_path.to_string());
        }
    }

    if !invalid_assets.is_empty() {
        return Err(BootstrapRuntimeValidationError {
            failure_kind: FAILURE_KIND_PACKAGED_RUNTIME_ASSETS_INVALID,
            detail: join_lines(vec![
                format!(
                    "Packaged {step} found an incomplete or invalid materialized runtime payload."
                ),
                format!("runtimeRoot={}", runtime_root.display()),
                format!("runtimeHome={}", runtime_home.display()),
                format!("invalidAssets={}", invalid_assets.join(",")),
            ]),
        });
    }

    Ok(())
}

fn build_context_lines(label: &str, binary: &ResolvedDockerBinary) -> Vec<String> {
    let mut lines = vec![format!("{label}:"), format!("binary: {}", binary.display)];
    lines.extend(build_docker_environment_lines(&binary.environment));
    lines
}

fn spawn_docker_base_command(binary: &ResolvedDockerBinary) -> Command {
    let mut command = Command::new(&binary.command);
    apply_docker_command_environment(&mut command, &binary.environment);
    command
}

fn spawn_docker_command(binary: &ResolvedDockerBinary, args: &[&str]) -> Command {
    let mut command = spawn_docker_base_command(binary);
    command.args(args);
    command
}

fn resolve_docker_binary(runtime: &BootstrapRuntime) -> Result<ResolvedDockerBinary, CommandProbe> {
    let environment = resolve_docker_command_environment(runtime);
    let mut detail_lines = build_docker_environment_lines(&environment);
    let mut candidate_failures = Vec::new();
    let mut seen_resolved_paths = HashSet::new();
    let mut found_candidate = false;

    #[cfg(target_os = "macos")]
    {
        for candidate in MACOS_DOCKER_CANDIDATES {
            detail_lines.push(format!("checking macOS candidate: {candidate}"));

            let resolved_path = match fs::canonicalize(candidate) {
                Ok(path) => path,
                Err(err) if err.kind() == ErrorKind::NotFound => {
                    detail_lines.push(format!("candidate missing: {candidate}"));
                    continue;
                }
                Err(err) => {
                    detail_lines.push(format!("candidate resolution error for {candidate}: {err}"));
                    candidate_failures.push(FailureKind::UnexpectedCommandExecutionError);
                    continue;
                }
            };

            if !resolved_path.is_file() {
                detail_lines.push(format!(
                    "candidate resolved outside a file path: {}",
                    resolved_path.display()
                ));
                continue;
            }

            let resolved_display = resolved_path.display().to_string();
            detail_lines.push(format!(
                "candidate resolved to absolute path: {resolved_display}"
            ));
            found_candidate = true;

            if !seen_resolved_paths.insert(resolved_display.clone()) {
                detail_lines.push(format!(
                    "candidate duplicates previously tested path: {resolved_display}"
                ));
                continue;
            }

            let mut probe = Command::new(&resolved_path);
            probe.arg("--version");
            apply_docker_command_environment(&mut probe, &environment);

            match probe.output() {
                Ok(output) if output.status.success() => {
                    detail_lines.push(format!(
                        "verified docker binary from macOS candidate: {resolved_display}"
                    ));
                    detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
                    return Ok(ResolvedDockerBinary {
                        command: resolved_display.clone(),
                        display: resolved_display,
                        resolution_detail: join_lines(detail_lines),
                        environment: environment.clone(),
                    });
                }
                Ok(output) => {
                    detail_lines.push(format!(
                        "candidate failed `docker --version`: {resolved_display}"
                    ));
                    detail_lines.push(format!("exit status: {}", output.status));
                    detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
                    candidate_failures.push(if runtime.packaged {
                        FailureKind::DockerCliFoundButUnusableFromPackagedContext
                    } else {
                        FailureKind::DockerCliExecutionFailed
                    });
                }
                Err(err) if err.kind() == ErrorKind::NotFound => {
                    detail_lines.push(format!(
                        "candidate spawn failed with not found for {resolved_display}: {err}"
                    ));
                }
                Err(err) => {
                    detail_lines.push(format!(
                        "candidate spawn error for {resolved_display}: {err}"
                    ));
                    candidate_failures.push(if runtime.packaged {
                        FailureKind::DockerCliFoundButUnusableFromPackagedContext
                    } else {
                        FailureKind::DockerCliExecutionFailed
                    });
                }
            }
        }
    }

    let mut fallback = Command::new("docker");
    fallback.arg("--version");
    apply_docker_command_environment(&mut fallback, &environment);

    match fallback.output() {
        Ok(output) if output.status.success() => {
            detail_lines.push("resolved docker binary from PATH fallback: docker".to_string());
            detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
            Ok(ResolvedDockerBinary {
                command: "docker".to_string(),
                display: "docker".to_string(),
                resolution_detail: join_lines(detail_lines),
                environment,
            })
        }
        Ok(output) => {
            detail_lines.push(
                "PATH fallback located a docker command, but `docker --version` failed."
                    .to_string(),
            );
            detail_lines.push(format!("exit status: {}", output.status));
            detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
            Err(CommandProbe::failure(
                if runtime.packaged || found_candidate {
                    FailureKind::DockerCliFoundButUnusableFromPackagedContext
                } else {
                    FailureKind::DockerCliExecutionFailed
                },
                join_lines(detail_lines),
            ))
        }
        Err(err) if err.kind() == ErrorKind::NotFound => {
            detail_lines
                .push("PATH fallback failed to find a usable `docker` executable.".to_string());
            let failure_kind = candidate_failures
                .into_iter()
                .last()
                .unwrap_or(FailureKind::DockerBinaryNotFound);
            Err(CommandProbe::failure(
                failure_kind,
                join_lines(detail_lines),
            ))
        }
        Err(err) => {
            detail_lines.push(format!(
                "PATH fallback raised an unexpected execution error: {err}"
            ));
            Err(CommandProbe::failure(
                if runtime.packaged || found_candidate {
                    FailureKind::DockerCliFoundButUnusableFromPackagedContext
                } else {
                    FailureKind::UnexpectedCommandExecutionError
                },
                join_lines(detail_lines),
            ))
        }
    }
}

fn run_probe(
    binary: &ResolvedDockerBinary,
    args: &[&str],
    label: &str,
    exit_failure_kind: FailureKind,
) -> CommandProbe {
    match spawn_docker_command(binary, args).output() {
        Ok(output) if output.status.success() => {
            let mut lines = build_context_lines(label, binary);
            lines.push("status: ok".to_string());
            lines.extend(render_probe_output(&output.stdout, &output.stderr));
            CommandProbe::success(join_lines(lines))
        }
        Ok(output) => {
            let mut lines = build_context_lines(label, binary);
            lines.push(format!("status: {}", exit_failure_kind.summary()));
            lines.push(format!("exit status: {}", output.status));
            lines.extend(render_probe_output(&output.stdout, &output.stderr));
            CommandProbe::failure(exit_failure_kind, join_lines(lines))
        }
        Err(err) if err.kind() == ErrorKind::NotFound => {
            let mut lines = build_context_lines(label, binary);
            lines.push("status: Docker binary not found at execution time".to_string());
            lines.push(format!("spawn error: {err}"));
            CommandProbe::failure(FailureKind::DockerBinaryNotFound, join_lines(lines))
        }
        Err(err) => {
            let mut lines = build_context_lines(label, binary);
            lines.push("status: unexpected command execution error".to_string());
            lines.push(format!("spawn error: {err}"));
            CommandProbe::failure(
                FailureKind::UnexpectedCommandExecutionError,
                join_lines(lines),
            )
        }
    }
}

fn skipped_probe(label: &str, reason: &str) -> CommandProbe {
    CommandProbe::skipped(format!("{label}:\nskipped: {reason}"))
}

fn build_preflight_detail(probes: &[CommandProbe]) -> Option<String> {
    let detail = probes
        .iter()
        .map(|probe| probe.detail.trim())
        .filter(|detail| !detail.is_empty())
        .collect::<Vec<_>>()
        .join("\n\n");

    if detail.trim().is_empty() {
        None
    } else {
        Some(detail)
    }
}

fn is_repo_runtime_root(candidate: &Path) -> bool {
    candidate.join("docker-compose.yml").is_file()
        && candidate.join("guardian").is_dir()
        && candidate.join("frontend").is_dir()
        && candidate.join("src-tauri").is_dir()
}

fn find_repo_root_from_ancestors(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find(|candidate| is_repo_runtime_root(candidate))
        .map(Path::to_path_buf)
}

fn find_macos_app_bundle(path: &Path) -> Option<PathBuf> {
    path.ancestors().find_map(|candidate| {
        if candidate.extension() == Some(OsStr::new("app")) {
            Some(candidate.to_path_buf())
        } else {
            None
        }
    })
}

fn infer_home_from_runtime_home(runtime_home: &Path) -> Option<String> {
    runtime_home
        .parent()
        .and_then(Path::parent)
        .and_then(Path::parent)
        .filter(|candidate| candidate.is_dir())
        .map(|candidate| candidate.display().to_string())
}

fn resolve_docker_home(runtime: &BootstrapRuntime) -> Option<String> {
    env::var("HOME")
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .or_else(|| {
            runtime
                .runtime_home
                .as_deref()
                .and_then(infer_home_from_runtime_home)
        })
        .or_else(|| {
            #[cfg(target_os = "macos")]
            {
                env::var("USER")
                    .ok()
                    .map(|user| user.trim().to_string())
                    .filter(|user| !user.is_empty())
                    .map(|user| format!("/Users/{user}"))
                    .filter(|candidate| Path::new(candidate.as_str()).is_dir())
            }
            #[cfg(not(target_os = "macos"))]
            {
                None
            }
        })
}

fn resolve_docker_command_environment(runtime: &BootstrapRuntime) -> DockerCommandEnvironment {
    let home = resolve_docker_home(runtime);
    let docker_config = env::var("DOCKER_CONFIG")
        .ok()
        .map(|value| value.trim().to_string())
        .filter(|value| !value.is_empty())
        .or_else(|| home.as_ref().map(|value| format!("{value}/.docker")));

    DockerCommandEnvironment {
        home,
        docker_config,
    }
}

fn apply_runtime_command_environment(command: &mut Command, runtime: &BootstrapRuntime) {
    command.env("CODEXIFY_RUNTIME_CONTEXT", &runtime.runtime_context);
    command.env(
        "CODEXIFY_PACKAGED_RUNTIME",
        if runtime.packaged { "1" } else { "0" },
    );

    if let Some(runtime_root) = runtime.runtime_root_path() {
        command.env("CODEXIFY_RUNTIME_HOME", runtime_root);
        command.env("CODEXIFY_RUNTIME_ROOT", runtime_root);
        command.env(
            "CODEXIFY_RUNTIME_ENV_FILE",
            runtime_env_file_path(runtime_root),
        );
        command.env(
            "CODEXIFY_RUNTIME_COMPOSE_FILE",
            compose_file_path(runtime_root),
        );
        command.env(
            "CODEXIFY_RUNTIME_MANIFEST",
            packaged_runtime_manifest_path(runtime_root),
        );
    }

    if let Some(resource_root) = &runtime.resource_root {
        command.env("CODEXIFY_RUNTIME_RESOURCE_ROOT", resource_root);
    }
}

pub fn prime_packaged_runtime_environment(runtime: &BootstrapRuntime) {
    if !runtime.packaged {
        return;
    }

    let environment = resolve_docker_command_environment(runtime);
    env::set_var("PATH", NORMALIZED_DOCKER_PATH);

    if let Some(home) = environment.home {
        env::set_var("HOME", home);
    }
    if let Some(docker_config) = environment.docker_config {
        env::set_var("DOCKER_CONFIG", docker_config);
    }
    if let Some(runtime_home) = runtime.runtime_home.as_ref() {
        env::set_var(
            "CODEXIFY_PACKAGED_RUNTIME_HOME",
            runtime_home.display().to_string(),
        );
    }
    if let Some(runtime_root) = runtime.runtime_root_path() {
        env::set_var(
            "CODEXIFY_PACKAGED_RUNTIME_ROOT",
            runtime_root.display().to_string(),
        );
        env::set_var(
            "CODEXIFY_RUNTIME_ENV_FILE",
            runtime_env_file_path(runtime_root).display().to_string(),
        );
    }
}

fn build_docker_environment_lines(environment: &DockerCommandEnvironment) -> Vec<String> {
    let mut lines = vec![format!("PATH: {NORMALIZED_DOCKER_PATH}")];
    match &environment.home {
        Some(home) => lines.push(format!("HOME: {home}")),
        None => lines.push("HOME: <unresolved>".to_string()),
    }
    match &environment.docker_config {
        Some(docker_config) => lines.push(format!("DOCKER_CONFIG: {docker_config}")),
        None => lines.push("DOCKER_CONFIG: <unresolved>".to_string()),
    }
    lines
}

fn apply_docker_command_environment(command: &mut Command, environment: &DockerCommandEnvironment) {
    command.env("PATH", NORMALIZED_DOCKER_PATH);

    if let Some(home) = &environment.home {
        command.env("HOME", home);
    }
    if let Some(docker_config) = &environment.docker_config {
        command.env("DOCKER_CONFIG", docker_config);
    }
}

fn resolve_python_binary(repo_root: &Path) -> PathBuf {
    let candidates = [
        repo_root.join(".venv/bin/python"),
        repo_root.join(".venv/bin/python3"),
        repo_root.join("venv/bin/python"),
        repo_root.join("venv/bin/python3"),
    ];

    for candidate in candidates {
        if candidate.is_file() {
            return candidate;
        }
    }

    PathBuf::from("python3")
}

fn build_step_result(
    ok: bool,
    step: &str,
    detail: Option<String>,
    command: Option<String>,
    stdout: Option<String>,
    stderr: Option<String>,
    exit_code: Option<i32>,
    context: Option<&BootstrapRuntime>,
    failure_kind: Option<&str>,
) -> BootstrapStepResult {
    BootstrapStepResult {
        ok,
        step: step.to_string(),
        detail,
        failure_kind: failure_kind.map(str::to_string),
        runtime_context: context.map(|resolved| resolved.runtime_context.clone()),
        repo_root: context.and_then(|resolved| resolved.repo_root_display()),
        runtime_home: context.and_then(|resolved| resolved.runtime_home_display()),
        runtime_root: context.and_then(|resolved| resolved.runtime_root_display()),
        packaged: context.map(|resolved| resolved.packaged),
        command,
        stdout,
        stderr,
        exit_code,
    }
}

fn render_step_detail(
    prefix_lines: Vec<String>,
    stdout: Option<&String>,
    stderr: Option<&String>,
) -> Option<String> {
    let mut lines = prefix_lines;
    if let Some(stdout) = stdout {
        lines.push(String::new());
        lines.push("stdout:".to_string());
        lines.push(stdout.clone());
    }
    if let Some(stderr) = stderr {
        lines.push(String::new());
        lines.push("stderr:".to_string());
        lines.push(stderr.clone());
    }
    let detail = join_lines(lines);
    if detail.trim().is_empty() {
        None
    } else {
        Some(detail)
    }
}

fn build_generic_compose_command_display(runtime_root: &Path, compose_args: &[&str]) -> String {
    let compose_file = compose_file_path(runtime_root);
    let env_file = runtime_env_file_path(runtime_root);
    let tail = if compose_args.is_empty() {
        String::new()
    } else {
        format!(" {}", compose_args.join(" "))
    };

    format!(
        "docker compose --project-directory {} --file {}{} [env: CODEXIFY_RUNTIME_ENV_FILE={}]",
        runtime_root.display(),
        compose_file.display(),
        tail,
        env_file.display()
    )
}

fn build_compose_command_display(
    binary: &ResolvedDockerBinary,
    runtime_root: &Path,
    compose_args: &[&str],
) -> String {
    build_generic_compose_command_display(runtime_root, compose_args).replacen(
        "docker compose",
        &format!("{} compose", binary.display),
        1,
    )
}

fn spawn_compose_command(
    binary: &ResolvedDockerBinary,
    runtime: &BootstrapRuntime,
    runtime_root: &Path,
    compose_args: &[&str],
) -> Command {
    let mut command = spawn_docker_command(binary, &[]);
    command.arg("compose");
    command.arg("--project-directory").arg(runtime_root);
    command.arg("--file").arg(compose_file_path(runtime_root));
    command.args(compose_args);
    command.current_dir(runtime_root);
    apply_runtime_command_environment(&mut command, runtime);
    command
}

fn build_compose_runtime_lines(context: &BootstrapRuntime) -> Vec<String> {
    let runtime_root = context.runtime_root_path();
    let mut lines = vec![
        format!("runtimeContext={}", context.runtime_context),
        format!("packaged={}", context.packaged),
    ];

    if let Some(repo_root) = &context.repo_root {
        lines.push(format!("repoRoot={}", repo_root.display()));
    }
    if let Some(runtime_home) = &context.runtime_home {
        lines.push(format!("runtimeHome={}", runtime_home.display()));
    }
    if let Some(resource_root) = &context.resource_root {
        lines.push(format!("resourceRoot={}", resource_root.display()));
    }
    if let Some(runtime_root) = runtime_root {
        lines.push(format!("runtimeRoot={}", runtime_root.display()));
        lines.push(format!(
            "composeFile={}",
            compose_file_path(runtime_root).display()
        ));
        lines.push(format!(
            "runtimeEnvFile={}",
            runtime_env_file_path(runtime_root).display()
        ));
        lines.push(format!(
            "runtimeManifest={}",
            packaged_runtime_manifest_path(runtime_root).display()
        ));
        lines.push(format!(
            "runtimeEnvFile={}",
            runtime_env_file_path(runtime_root).display()
        ));
    }

    lines
}

fn parse_http_url(url: &str) -> Result<ParsedHttpUrl, String> {
    let trimmed = url.trim();
    let without_scheme = trimmed
        .strip_prefix("http://")
        .ok_or_else(|| format!("Only http:// URLs are supported for health checks: {trimmed}"))?;
    let (host_port, raw_path) = match without_scheme.split_once('/') {
        Some((host_port, path)) => (host_port, format!("/{}", path)),
        None => (without_scheme, "/".to_string()),
    };
    let (host, port) = match host_port.rsplit_once(':') {
        Some((host, port)) => {
            let parsed_port = port
                .parse::<u16>()
                .map_err(|_| format!("Invalid port in health URL: {trimmed}"))?;
            (host.to_string(), parsed_port)
        }
        None => (host_port.to_string(), 80),
    };

    if host.trim().is_empty() {
        return Err(format!("Missing host in health URL: {trimmed}"));
    }

    Ok(ParsedHttpUrl {
        host,
        port,
        path: raw_path,
    })
}

fn truncate_chars(value: &str, max_chars: usize) -> String {
    value.chars().take(max_chars).collect::<String>()
}

struct HttpResponseProbe {
    status_line: String,
    status_code: Option<u16>,
    body: String,
}

fn fetch_http_response(url: &str) -> Result<HttpResponseProbe, String> {
    let parsed = match parse_http_url(url) {
        Ok(parsed) => parsed,
        Err(detail) => {
            return Err(detail);
        }
    };

    let address = format!("{}:{}", parsed.host, parsed.port);
    let socket_addr = match address.to_socket_addrs() {
        Ok(mut addrs) => match addrs.next() {
            Some(addr) => addr,
            None => {
                return Err(format!("No socket addresses resolved for {address}"));
            }
        },
        Err(err) => {
            return Err(format!("Failed to resolve {address}: {err}"));
        }
    };

    let timeout = Duration::from_secs(2);
    let mut stream = match TcpStream::connect_timeout(&socket_addr, timeout) {
        Ok(stream) => stream,
        Err(err) => {
            return Err(format!("TCP connect failed: {err}"));
        }
    };

    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));

    let request = format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nUser-Agent: codexify-tauri-bootstrap\r\nAccept: application/json\r\n\r\n",
        parsed.path, parsed.host
    );

    if let Err(err) = stream.write_all(request.as_bytes()) {
        return Err(format!("Failed to write request: {err}"));
    }

    let mut response = String::new();
    if let Err(err) = stream.read_to_string(&mut response) {
        return Err(format!("Failed to read response: {err}"));
    }

    let mut lines = response.lines();
    let status_line = lines.next().unwrap_or_default().trim().to_string();
    let status_code = status_line
        .split_whitespace()
        .nth(1)
        .and_then(|value| value.parse::<u16>().ok());
    let body = response
        .split("\r\n\r\n")
        .nth(1)
        .unwrap_or_default()
        .trim()
        .to_string();

    Ok(HttpResponseProbe {
        status_line,
        status_code,
        body,
    })
}

#[allow(dead_code)]
fn probe_http_endpoint(url: &str, allow_client_errors: bool) -> HealthEndpointCheck {
    match fetch_http_response(url) {
        Ok(response) => {
            let response_excerpt = if response.body.is_empty() {
                None
            } else {
                Some(truncate_chars(&response.body, 240))
            };

            let ok = match response.status_code {
                Some(code) if allow_client_errors => (200..500).contains(&code),
                Some(code) => (200..300).contains(&code),
                None => false,
            };
            let detail = if response.status_line.is_empty() {
                Some("Missing HTTP status line in response.".to_string())
            } else {
                Some(response.status_line)
            };

            HealthEndpointCheck {
                endpoint: url.to_string(),
                ok,
                status_code: response.status_code,
                detail,
                response_excerpt,
            }
        }
        Err(detail) => HealthEndpointCheck {
            endpoint: url.to_string(),
            ok: false,
            status_code: None,
            detail: Some(detail),
            response_excerpt: None,
        },
    }
}

fn parse_json_body(body: &str) -> Option<Value> {
    serde_json::from_str(body).ok()
}

fn json_bool_field(value: &Value, key: &str) -> Option<bool> {
    value.get(key).and_then(|entry| entry.as_bool())
}

fn json_string_field(value: &Value, key: &str) -> Option<String> {
    value
        .get(key)
        .and_then(|entry| entry.as_str())
        .and_then(|text| {
            let trimmed = text.trim();
            if trimmed.is_empty() {
                None
            } else {
                Some(trimmed.to_string())
            }
        })
}

fn json_status_matches(value: &Value, expected: &str) -> bool {
    json_string_field(value, "status")
        .map(|status| status.eq_ignore_ascii_case(expected))
        .unwrap_or(false)
}

fn bool_label(value: bool) -> &'static str {
    if value {
        "true"
    } else {
        "false"
    }
}

fn option_bool_label(value: Option<bool>) -> String {
    match value {
        Some(true) => "true".to_string(),
        Some(false) => "false".to_string(),
        None => "not-gated".to_string(),
    }
}

fn probe_http_endpoint_with_body(
    url: &str,
    allow_client_errors: bool,
) -> (HealthEndpointCheck, Option<String>) {
    match fetch_http_response(url) {
        Ok(response) => {
            let body = if response.body.is_empty() {
                None
            } else {
                Some(response.body.clone())
            };
            let response_excerpt = body.as_deref().map(|body| truncate_chars(body, 240));
            let ok = match response.status_code {
                Some(code) if allow_client_errors => (200..500).contains(&code),
                Some(code) => (200..300).contains(&code),
                None => false,
            };
            let detail = if response.status_line.is_empty() {
                Some("Missing HTTP status line in response.".to_string())
            } else {
                Some(response.status_line)
            };

            (
                HealthEndpointCheck {
                    endpoint: url.to_string(),
                    ok,
                    status_code: response.status_code,
                    detail,
                    response_excerpt,
                },
                body,
            )
        }
        Err(detail) => (
            HealthEndpointCheck {
                endpoint: url.to_string(),
                ok: false,
                status_code: None,
                detail: Some(detail),
                response_excerpt: None,
            },
            None,
        ),
    }
}

#[cfg(target_os = "macos")]
fn read_keychain_password() -> Result<Option<String>, String> {
    let output = Command::new("security")
        .args([
            "find-generic-password",
            "-a",
            DESKTOP_KEYCHAIN_ACCOUNT,
            "-s",
            DESKTOP_KEYCHAIN_SERVICE,
            "-w",
        ])
        .output()
        .map_err(|err| format!("Failed to run macOS security CLI: {err}"))?;

    if output.status.success() {
        let value = String::from_utf8_lossy(&output.stdout).trim().to_string();
        if value.is_empty() {
            Ok(None)
        } else {
            Ok(Some(value))
        }
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).to_lowercase();
        if stderr.contains("could not be found") || stderr.contains("item not found") {
            Ok(None)
        } else {
            Err(format!(
                "Failed to read API key from macOS keychain: {}",
                String::from_utf8_lossy(&output.stderr)
            ))
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn read_keychain_password() -> Result<Option<String>, String> {
    Ok(None)
}

#[cfg(target_os = "macos")]
fn write_keychain_password(api_key: &str) -> Result<(), String> {
    let output = Command::new("security")
        .args([
            "add-generic-password",
            "-a",
            DESKTOP_KEYCHAIN_ACCOUNT,
            "-s",
            DESKTOP_KEYCHAIN_SERVICE,
            "-w",
            api_key,
            "-U",
        ])
        .output()
        .map_err(|err| format!("Failed to run macOS security CLI: {err}"))?;
    if output.status.success() {
        Ok(())
    } else {
        Err(format!(
            "Failed to store API key in macOS keychain: {}",
            String::from_utf8_lossy(&output.stderr)
        ))
    }
}

#[cfg(not(target_os = "macos"))]
fn write_keychain_password(_api_key: &str) -> Result<(), String> {
    Err("Desktop secure key storage is currently implemented for macOS only".to_string())
}

#[cfg(target_os = "macos")]
fn delete_keychain_password() -> Result<(), String> {
    let output = Command::new("security")
        .args([
            "delete-generic-password",
            "-a",
            DESKTOP_KEYCHAIN_ACCOUNT,
            "-s",
            DESKTOP_KEYCHAIN_SERVICE,
        ])
        .output()
        .map_err(|err| format!("Failed to run macOS security CLI: {err}"))?;
    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr).to_lowercase();
        if stderr.contains("could not be found") || stderr.contains("item not found") {
            Ok(())
        } else {
            Err(format!(
                "Failed to clear API key from macOS keychain: {}",
                String::from_utf8_lossy(&output.stderr)
            ))
        }
    }
}

#[cfg(not(target_os = "macos"))]
fn delete_keychain_password() -> Result<(), String> {
    Ok(())
}

#[tauri::command]
pub fn desktop_get_runtime_config() -> DesktopRuntimeConfig {
    let backend_base_url = desktop_backend_base_url();
    let api_base_url = resolve_api_base_url(&backend_base_url);
    let sse_url = combine_url(&api_base_url, "/events");
    let share_public_base_url = resolve_share_public_base_url(&backend_base_url);
    let auth_mode = env_first(&["GUARDIAN_AUTH_MODE"], "local");

    DesktopRuntimeConfig {
        mode: "tauri".to_string(),
        backend_base_url,
        api_base_url,
        sse_url,
        share_public_base_url,
        auth_mode,
    }
}

#[tauri::command]
pub async fn desktop_fetch_media(
    path: String,
) -> Result<DesktopFetchedMedia, DesktopFetchMediaError> {
    let canonical_path = normalize_desktop_media_fetch_path(&path)?;
    let backend_base_url = desktop_backend_base_url();
    let request_url = desktop_signed_media_url(&backend_base_url, &canonical_path)?;
    let client = reqwest::Client::builder().build().map_err(|err| {
        desktop_fetch_media_error(
            "fetch_failed",
            format!("Unable to initialize desktop media client: {err}"),
        )
    })?;

    let response = client.get(&request_url).send().await.map_err(|err| {
        desktop_fetch_media_error(
            "fetch_failed",
            format!("Desktop media fetch request failed: {err}"),
        )
    })?;

    if !response.status().is_success() {
        return Err(desktop_fetch_media_error(
            "fetch_failed",
            format!(
                "Desktop media fetch returned status {} for {}.",
                response.status(),
                canonical_path
            ),
        ));
    }

    let content_type = desktop_media_response_content_type(&response)?;
    if let Some(content_length) = response.content_length() {
        desktop_media_size_guard(content_length as usize)?;
    }

    let bytes = response.bytes().await.map_err(|err| {
        desktop_fetch_media_error(
            "fetch_failed",
            format!("Desktop media response read failed: {err}"),
        )
    })?;
    desktop_media_size_guard(bytes.len())?;

    Ok(DesktopFetchedMedia {
        content_type,
        bytes_base64: BASE64_STANDARD.encode(&bytes),
        size_bytes: bytes.len(),
    })
}

#[tauri::command]
pub fn desktop_get_api_key() -> Option<String> {
    match read_keychain_password() {
        Ok(value) => value,
        Err(_) => None,
    }
}

#[tauri::command]
pub fn desktop_set_api_key(api_key: String) -> Result<(), String> {
    let trimmed = api_key.trim();
    if trimmed.is_empty() {
        return Err("API key cannot be empty".to_string());
    }
    write_keychain_password(trimmed)
}

#[tauri::command]
pub fn desktop_clear_api_key() -> Result<(), String> {
    delete_keychain_password()
}

#[tauri::command]
pub fn desktop_open_external(url: String) -> Result<(), String> {
    let trimmed = url.trim();
    if !(trimmed.starts_with("http://") || trimmed.starts_with("https://")) {
        return Err("Only http(s) URLs are supported".to_string());
    }
    #[cfg(target_os = "macos")]
    {
        let status = Command::new("open")
            .arg(trimmed)
            .status()
            .map_err(|err| format!("Failed to open URL using macOS open command: {err}"))?;
        if status.success() {
            Ok(())
        } else {
            Err(format!("macOS open command failed with status: {status}"))
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        Err("External URL opening is currently implemented for macOS only".to_string())
    }
}

#[tauri::command]
pub fn desktop_runtime_preflight_check(
    runtime: tauri::State<'_, BootstrapRuntime>,
) -> RuntimePreflight {
    let runtime_probe = if let Some(detail) = &runtime.resolution_detail {
        CommandProbe::success(detail.clone())
    } else {
        CommandProbe::success("runtime resolution detail unavailable.".to_string())
    };
    let runtime_context = Some(runtime.runtime_context.clone());
    let repo_root = runtime.repo_root_display();
    let runtime_home = runtime.runtime_home_display();
    let runtime_root = runtime.runtime_root_display();
    let packaged = Some(runtime.packaged);

    if runtime.failure_kind.is_some() || runtime.runtime_root_path().is_none() {
        return RuntimePreflight {
            docker_cli_installed: false,
            docker_compose_available: false,
            docker_daemon_reachable: false,
            ready: false,
            detail: build_preflight_detail(&[runtime_probe]),
            failure_kind: runtime.failure_kind.clone(),
            runtime_context,
            repo_root,
            runtime_home,
            runtime_root,
            packaged,
        };
    }

    match resolve_docker_binary(&runtime) {
        Ok(binary) => {
            let resolution_probe = CommandProbe::success(format!(
                "docker binary resolution:\n{}",
                binary.resolution_detail
            ));
            let cli_probe = run_probe(
                &binary,
                &["--version"],
                "docker --version",
                if runtime.packaged {
                    FailureKind::DockerCliFoundButUnusableFromPackagedContext
                } else {
                    FailureKind::DockerCliExecutionFailed
                },
            );

            let (
                compose_probe,
                daemon_probe,
                docker_compose_available,
                docker_daemon_reachable,
                failure_kind,
            ) = if cli_probe.ok {
                let compose_probe = run_probe(
                    &binary,
                    &["compose", "version"],
                    "docker compose version",
                    FailureKind::DockerComposeUnavailable,
                );
                let daemon_probe = run_probe(
                    &binary,
                    &["info", "--format", "{{json .ServerVersion}}"],
                    "docker info --format {{json .ServerVersion}}",
                    FailureKind::DockerDaemonUnreachable,
                );
                let compose_available = compose_probe.ok;
                let daemon_reachable = daemon_probe.ok;
                let failure_kind = compose_probe
                    .failure_kind
                    .or(daemon_probe.failure_kind)
                    .map(|kind| kind.as_str().to_string());
                (
                    compose_probe,
                    daemon_probe,
                    compose_available,
                    daemon_reachable,
                    failure_kind,
                )
            } else {
                let failure_kind = cli_probe.failure_kind.map(|kind| kind.as_str().to_string());
                (
                    skipped_probe(
                        "docker compose version",
                        "skipped because the Docker CLI version check did not succeed",
                    ),
                    skipped_probe(
                        "docker info --format {{json .ServerVersion}}",
                        "skipped because the Docker CLI version check did not succeed",
                    ),
                    false,
                    false,
                    failure_kind,
                )
            };

            let ready = cli_probe.ok
                && docker_compose_available
                && docker_daemon_reachable
                && runtime.runtime_root_path().is_some();
            let detail = build_preflight_detail(&[
                runtime_probe,
                resolution_probe,
                cli_probe,
                compose_probe,
                daemon_probe,
            ]);

            RuntimePreflight {
                docker_cli_installed: true,
                docker_compose_available,
                docker_daemon_reachable,
                ready,
                detail,
                failure_kind,
                runtime_context,
                repo_root,
                runtime_home,
                runtime_root,
                packaged,
            }
        }
        Err(resolution_probe) => {
            let failure_kind = resolution_probe
                .failure_kind
                .map(|kind| kind.as_str().to_string());
            RuntimePreflight {
                docker_cli_installed: matches!(
                    resolution_probe.failure_kind,
                    Some(FailureKind::DockerCliExecutionFailed)
                        | Some(FailureKind::DockerCliFoundButUnusableFromPackagedContext)
                ),
                docker_compose_available: false,
                docker_daemon_reachable: false,
                ready: false,
                detail: build_preflight_detail(&[runtime_probe, resolution_probe]),
                failure_kind,
                runtime_context,
                repo_root,
                runtime_home,
                runtime_root,
                packaged,
            }
        }
    }
}

#[tauri::command]
pub fn desktop_run_setup_cli(runtime: tauri::State<'_, BootstrapRuntime>) -> BootstrapStepResult {
    let runtime_root = match resolve_runtime_root_for_step(&runtime, "setup") {
        Ok(path) => path,
        Err(result) => return result,
    };
    if let Err(err) = validate_packaged_runtime(&runtime, "setup", &["guardian", "backend"]) {
        return build_step_result(
            false,
            "setup",
            Some(err.detail),
            None,
            None,
            None,
            None,
            Some(&*runtime),
            Some(err.failure_kind),
        );
    }

    if runtime.packaged {
        let command_display = "native packaged setup env materialization".to_string();
        return match materialize_packaged_setup_env(runtime.runtime_home.as_deref(), &runtime_root)
        {
            Ok(result) => {
                let stdout = Some(
                    serde_json::json!({
                        "source": "desktop_run_setup_cli",
                        "mode": "packaged-native-env-materialization",
                        "runtime_root": runtime_root.display().to_string(),
                        "env_path": result.env_path.display().to_string(),
                        "preserved_keys": result.preserved_keys,
                        "generated_guardian_api_key": result.generated_guardian_api_key,
                        "created_new_env_file": result.created_new_env_file,
                        "migrated_legacy_env": result.migrated_legacy_env_source.is_some(),
                        "migrated_legacy_env_source": result
                            .migrated_legacy_env_source
                            .as_ref()
                            .map(|path| path.display().to_string()),
                        "migrated_legacy_runtime_assets": result.migrated_legacy_runtime_assets,
                    })
                    .to_string(),
                );
                let detail = render_step_detail(
                    vec![
                        format!("runtimeContext={}", runtime.runtime_context),
                        format!("packaged={}", runtime.packaged),
                        format!("runtimeRoot={}", runtime_root.display()),
                        runtime
                            .runtime_home
                            .as_ref()
                            .map(|path| format!("runtimeHome={}", path.display()))
                            .unwrap_or_default(),
                        format!("runtimeEnvFile={}", result.env_path.display()),
                        "setupSource=packaged-native-env-materialization".to_string(),
                        format!(
                            "generatedGuardianApiKey={}",
                            result.generated_guardian_api_key
                        ),
                        format!("createdNewEnvFile={}", result.created_new_env_file),
                        result
                            .migrated_legacy_env_source
                            .as_ref()
                            .map(|path| format!("migratedLegacyEnvSource={}", path.display()))
                            .unwrap_or_else(|| "migratedLegacyEnvSource=<none>".to_string()),
                        format!(
                            "migratedLegacyRuntimeAssets={}",
                            if result.migrated_legacy_runtime_assets.is_empty() {
                                "<none>".to_string()
                            } else {
                                result.migrated_legacy_runtime_assets.join(",")
                            }
                        ),
                        "status=success".to_string(),
                    ],
                    stdout.as_ref(),
                    None,
                );
                build_step_result(
                    true,
                    "setup",
                    detail,
                    Some(command_display),
                    stdout,
                    None,
                    Some(0),
                    Some(&*runtime),
                    None,
                )
            }
            Err(err) => build_step_result(
                false,
                "setup",
                Some(err.detail),
                Some(command_display),
                None,
                None,
                None,
                Some(&*runtime),
                Some(err.failure_kind),
            ),
        };
    }

    let runtime_env_file = runtime_env_file_path(&runtime_root);
    let python = resolve_python_binary(&runtime_root);
    let command_display = format!(
        "{} -c <guardian.tui.setup_wizard_app.write_wizard_env>",
        python.display()
    );
    let script = format!(
        r#"
from pathlib import Path
import json
from guardian.ops.setup_wizard import build_doctor_report, default_env_target, read_env_file
from guardian.tui.setup_wizard_app import write_wizard_env

root = Path({runtime_root:?}).resolve()
env_path = default_env_target(root)
existing = read_env_file(env_path) if env_path.exists() else {{}}
written = write_wizard_env(repo_root=root, selections=existing)
items, code = build_doctor_report(root)
payload = {{
  "source": "guardian.cli.memoryos_cli setup",
  "automation_path": "guardian.tui.setup_wizard_app.write_wizard_env",
  "repo_root": str(root),
  "env_path": str(written),
  "preserved_keys": sorted(existing.keys()),
  "doctor_exit_code": code,
  "doctor_items": [
    {{
      "name": item.name,
      "ok": item.ok,
      "required": item.required,
      "detail": item.detail
    }}
    for item in items
  ],
}}
print(json.dumps(payload, indent=2))
raise SystemExit(code)
"#,
        runtime_root = runtime_root.display().to_string()
    );

    let mut command = Command::new(&python);
    command
        .args(["-c", &script])
        .current_dir(&runtime_root)
        .env("PYTHONPATH", runtime_root.display().to_string())
        .env(
            "CODEXIFY_RUNTIME_ENV_FILE",
            runtime_env_file.display().to_string(),
        );

    match command.output() {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let failure_kind = if output.status.success() {
                None
            } else {
                Some(phase_failure_kind(
                    &runtime,
                    FAILURE_KIND_PACKAGED_SETUP_FAILED,
                    FAILURE_KIND_SETUP_FAILED,
                ))
            };
            let detail = render_step_detail(
                vec![
                    format!("runtimeContext={}", runtime.runtime_context),
                    format!("packaged={}", runtime.packaged),
                    format!("runtimeRoot={}", runtime_root.display()),
                    runtime
                        .runtime_home
                        .as_ref()
                        .map(|path| format!("runtimeHome={}", path.display()))
                        .unwrap_or_default(),
                    format!("runtimeEnvFile={}", runtime_env_file.display()),
                    "setupSource=guardian.cli.memoryos_cli setup".to_string(),
                    "automationPath=guardian.tui.setup_wizard_app.write_wizard_env".to_string(),
                    format!("status={}", output.status),
                ],
                stdout.as_ref(),
                stderr.as_ref(),
            );
            build_step_result(
                output.status.success(),
                "setup",
                detail,
                Some(command_display),
                stdout,
                stderr,
                output.status.code(),
                Some(&*runtime),
                failure_kind,
            )
        }
        Err(err) => build_step_result(
            false,
            "setup",
            Some(format!(
                "Failed to execute setup automation via {}: {err}",
                python.display()
            )),
            Some(command_display),
            None,
            None,
            None,
            Some(&*runtime),
            Some(FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR),
        ),
    }
}

#[tauri::command]
pub fn desktop_compose_up(runtime: tauri::State<'_, BootstrapRuntime>) -> BootstrapStepResult {
    let runtime_root = match runtime.runtime_root_path() {
        Some(path) => path.to_path_buf(),
        None => {
            return BootstrapStepResult {
                ok: false,
                step: "compose-up".to_string(),
                detail: runtime.resolution_detail.clone(),
                failure_kind: runtime.failure_kind.clone(),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                command: None,
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary(&runtime) {
        Ok(binary) => binary,
        Err(probe) => {
            return build_step_result(
                false,
                "compose-up",
                Some(probe.detail),
                Some(build_generic_compose_command_display(
                    &runtime_root,
                    &["up", "-d"],
                )),
                None,
                None,
                None,
                Some(&*runtime),
                probe.failure_kind.map(FailureKind::as_str),
            )
        }
    };
    let command_display = build_compose_command_display(&docker, &runtime_root, &["up", "-d"]);

    match spawn_compose_command(&docker, &runtime, &runtime_root, &["up", "-d"]).output() {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let failure_kind = if output.status.success() {
                None
            } else if runtime.packaged
                && (stdout
                    .as_ref()
                    .is_some_and(|value| detect_docker_mount_path_rejection(value))
                    || stderr
                        .as_ref()
                        .is_some_and(|value| detect_docker_mount_path_rejection(value)))
            {
                Some(FAILURE_KIND_DOCKER_MOUNT_PATH_UNSHARED_OR_UNSUPPORTED)
            } else {
                Some(phase_failure_kind(
                    &runtime,
                    FAILURE_KIND_PACKAGED_COMPOSE_UP_FAILED,
                    FAILURE_KIND_COMPOSE_UP_FAILED,
                ))
            };
            let detail = render_step_detail(
                {
                    let mut lines = build_compose_runtime_lines(&runtime);
                    lines.push(format!("status={}", output.status));
                    lines
                },
                stdout.as_ref(),
                stderr.as_ref(),
            );
            build_step_result(
                output.status.success(),
                "compose-up",
                detail,
                Some(command_display),
                stdout,
                stderr,
                output.status.code(),
                Some(&*runtime),
                failure_kind,
            )
        }
        Err(err) => build_step_result(
            false,
            "compose-up",
            Some(format!("Failed to execute `{command_display}`: {err}")),
            Some(command_display),
            None,
            None,
            None,
            Some(&*runtime),
            Some(FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR),
        ),
    }
}

#[tauri::command]
pub fn desktop_open_docker_desktop() -> BootstrapDockerOpenResult {
    #[cfg(target_os = "macos")]
    {
        let mut detail_lines = vec![
            "Attempting to open Docker Desktop via macOS Launch Services.".to_string(),
            format!("appBundle={MACOS_DOCKER_APP_BUNDLE}"),
        ];

        let primary_command = "open -a Docker";
        match Command::new("open").args(["-a", "Docker"]).output() {
            Ok(output) if output.status.success() => {
                detail_lines.push(format!("status={}", output.status));
                detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
                BootstrapDockerOpenResult {
                    ok: true,
                    detail: Some(join_lines(detail_lines)),
                    command: Some(primary_command.to_string()),
                }
            }
            Ok(output) => {
                detail_lines.push(format!("primary status={}", output.status));
                detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));

                let fallback_command = format!("open {MACOS_DOCKER_APP_BUNDLE}");
                match Command::new("open").arg(MACOS_DOCKER_APP_BUNDLE).output() {
                    Ok(fallback_output) if fallback_output.status.success() => {
                        detail_lines.push("Fallback app-bundle open succeeded.".to_string());
                        detail_lines.push(format!("fallback status={}", fallback_output.status));
                        detail_lines.extend(render_probe_output(
                            &fallback_output.stdout,
                            &fallback_output.stderr,
                        ));
                        BootstrapDockerOpenResult {
                            ok: true,
                            detail: Some(join_lines(detail_lines)),
                            command: Some(format!("{primary_command} || {fallback_command}")),
                        }
                    }
                    Ok(fallback_output) => {
                        detail_lines.push("Fallback app-bundle open failed.".to_string());
                        detail_lines.push(format!("fallback status={}", fallback_output.status));
                        detail_lines.extend(render_probe_output(
                            &fallback_output.stdout,
                            &fallback_output.stderr,
                        ));
                        detail_lines.push(
                            "Action: confirm Docker Desktop is installed in /Applications and launch it manually."
                                .to_string(),
                        );
                        BootstrapDockerOpenResult {
                            ok: false,
                            detail: Some(join_lines(detail_lines)),
                            command: Some(format!("{primary_command} || {fallback_command}")),
                        }
                    }
                    Err(err) => {
                        detail_lines.push(format!("Fallback open execution error: {err}"));
                        detail_lines.push(
                            "Action: confirm Docker Desktop is installed in /Applications and launch it manually."
                                .to_string(),
                        );
                        BootstrapDockerOpenResult {
                            ok: false,
                            detail: Some(join_lines(detail_lines)),
                            command: Some(format!("{primary_command} || {fallback_command}")),
                        }
                    }
                }
            }
            Err(err) => BootstrapDockerOpenResult {
                ok: false,
                detail: Some(format!(
                    "Failed to execute `{primary_command}` via macOS Launch Services: {err}"
                )),
                command: Some(primary_command.to_string()),
            },
        }
    }
    #[cfg(not(target_os = "macos"))]
    {
        BootstrapDockerOpenResult {
            ok: false,
            detail: Some(
                "Docker Desktop launch assistance is currently implemented for macOS only."
                    .to_string(),
            ),
            command: None,
        }
    }
}

#[tauri::command]
pub fn desktop_get_bootstrap_logs(
    runtime: tauri::State<'_, BootstrapRuntime>,
    service: String,
) -> BootstrapLogResult {
    let requested_service = service.trim().to_string();
    let service = match normalize_bootstrap_service(&requested_service) {
        Ok(service) => service,
        Err(detail) => {
            return BootstrapLogResult {
                ok: false,
                service: requested_service,
                detail: Some(detail),
                failure_kind: None,
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                logs: None,
                command: None,
                exit_code: None,
            }
        }
    };

    let runtime_root = match runtime.runtime_root_path() {
        Some(path) => path.to_path_buf(),
        None => {
            return BootstrapLogResult {
                ok: false,
                service: service.to_string(),
                detail: runtime.resolution_detail.clone(),
                failure_kind: runtime.failure_kind.clone(),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                logs: None,
                command: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary(&runtime) {
        Ok(binary) => binary,
        Err(probe) => {
            return BootstrapLogResult {
                ok: false,
                service: service.to_string(),
                detail: Some(probe.detail),
                failure_kind: probe.failure_kind.map(|kind| kind.as_str().to_string()),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                logs: None,
                command: Some(format!(
                    "docker compose logs --tail {BOOTSTRAP_LOG_TAIL_LINES} --no-color {service}"
                )),
                exit_code: None,
            }
        }
    };
    let command_display = build_compose_command_display(
        &docker,
        &runtime_root,
        &[
            "logs",
            "--tail",
            BOOTSTRAP_LOG_TAIL_LINES,
            "--no-color",
            service,
        ],
    );

    match spawn_compose_command(
        &docker,
        &runtime,
        &runtime_root,
        &[
            "logs",
            "--tail",
            BOOTSTRAP_LOG_TAIL_LINES,
            "--no-color",
            service,
        ],
    )
    .output()
    {
        Ok(output) => {
            let logs = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let mut detail_lines = build_compose_runtime_lines(&runtime);
            detail_lines.push(format!("service={service}"));
            detail_lines.push(format!("status={}", output.status));
            if let Some(stderr) = &stderr {
                detail_lines.push(String::new());
                detail_lines.push("stderr:".to_string());
                detail_lines.push(stderr.clone());
            }

            BootstrapLogResult {
                ok: output.status.success(),
                service: service.to_string(),
                detail: Some(join_lines(detail_lines)),
                failure_kind: None,
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                logs,
                command: Some(command_display),
                exit_code: output.status.code(),
            }
        }
        Err(err) => BootstrapLogResult {
            ok: false,
            service: service.to_string(),
            detail: Some(format!("Failed to execute `{command_display}`: {err}")),
            failure_kind: Some(FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR.to_string()),
            runtime_context: Some(runtime.runtime_context.clone()),
            repo_root: runtime.repo_root_display(),
            runtime_home: runtime.runtime_home_display(),
            runtime_root: runtime.runtime_root_display(),
            packaged: Some(runtime.packaged),
            logs: None,
            command: Some(command_display),
            exit_code: None,
        },
    }
}

#[tauri::command]
pub fn desktop_restart_runtime_services(
    runtime: tauri::State<'_, BootstrapRuntime>,
) -> BootstrapRestartResult {
    let runtime_root = match runtime.runtime_root_path() {
        Some(path) => path.to_path_buf(),
        None => {
            return BootstrapRestartResult {
                ok: false,
                services: BOOTSTRAP_RESTART_SERVICES
                    .iter()
                    .map(|service| service.to_string())
                    .collect(),
                detail: runtime.resolution_detail.clone(),
                failure_kind: runtime.failure_kind.clone(),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                command: None,
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary(&runtime) {
        Ok(binary) => binary,
        Err(probe) => {
            return BootstrapRestartResult {
                ok: false,
                services: BOOTSTRAP_RESTART_SERVICES
                    .iter()
                    .map(|service| service.to_string())
                    .collect(),
                detail: Some(probe.detail),
                failure_kind: probe.failure_kind.map(|kind| kind.as_str().to_string()),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                command: Some(format!(
                    "{} && {}",
                    build_generic_compose_command_display(
                        &runtime_root,
                        &["restart", "db", "redis", "backend", "worker-chat"]
                    ),
                    build_generic_compose_command_display(
                        &runtime_root,
                        &[
                            "up",
                            "-d",
                            "db",
                            "redis",
                            "migrator",
                            "backend",
                            "worker-chat",
                        ]
                    )
                )),
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };

    let restart_command_display = build_compose_command_display(
        &docker,
        &runtime_root,
        &["restart", "db", "redis", "backend", "worker-chat"],
    );
    let up_command_display = build_compose_command_display(
        &docker,
        &runtime_root,
        &[
            "up",
            "-d",
            "db",
            "redis",
            "migrator",
            "backend",
            "worker-chat",
        ],
    );
    let combined_command_display = format!("{restart_command_display} && {up_command_display}");

    let restart_output = spawn_compose_command(
        &docker,
        &runtime,
        &runtime_root,
        &["restart", "db", "redis", "backend", "worker-chat"],
    )
    .output();

    let up_output = spawn_compose_command(
        &docker,
        &runtime,
        &runtime_root,
        &[
            "up",
            "-d",
            "db",
            "redis",
            "migrator",
            "backend",
            "worker-chat",
        ],
    )
    .output();

    let mut detail_lines = build_compose_runtime_lines(&runtime);
    detail_lines.push(format!("services={}", BOOTSTRAP_RESTART_SERVICES.join(",")));

    let mut stdout_sections = Vec::new();
    let mut stderr_sections = Vec::new();

    match &restart_output {
        Ok(output) => {
            detail_lines.push(format!("restartStatus={}", output.status));
            if let Some(stdout) = normalize_output(&output.stdout) {
                stdout_sections.push(format!("restart:\n{stdout}"));
            }
            if let Some(stderr) = normalize_output(&output.stderr) {
                stderr_sections.push(format!("restart:\n{stderr}"));
            }
        }
        Err(err) => {
            detail_lines.push(format!("restartExecutionError={err}"));
        }
    }

    match &up_output {
        Ok(output) => {
            detail_lines.push(format!("upStatus={}", output.status));
            if let Some(stdout) = normalize_output(&output.stdout) {
                stdout_sections.push(format!("up:\n{stdout}"));
            }
            if let Some(stderr) = normalize_output(&output.stderr) {
                stderr_sections.push(format!("up:\n{stderr}"));
            }
        }
        Err(err) => {
            detail_lines.push(format!("upExecutionError={err}"));
        }
    }

    let ok = matches!(&up_output, Ok(output) if output.status.success());
    if ok && matches!(&restart_output, Ok(output) if !output.status.success()) {
        detail_lines.push(
            "Restart step failed, but compose up -d succeeded and recovered the targeted services."
                .to_string(),
        );
    }

    let detail = Some(join_lines(detail_lines));
    let stdout = if stdout_sections.is_empty() {
        None
    } else {
        Some(stdout_sections.join("\n\n"))
    };
    let stderr = if stderr_sections.is_empty() {
        None
    } else {
        Some(stderr_sections.join("\n\n"))
    };
    let exit_code = match &up_output {
        Ok(output) => output.status.code(),
        Err(_) => None,
    };

    if let Err(err) = &restart_output {
        if up_output.is_err() {
            return BootstrapRestartResult {
                ok: false,
                services: BOOTSTRAP_RESTART_SERVICES
                    .iter()
                    .map(|service| service.to_string())
                    .collect(),
                detail: Some(format!(
                    "{}\n\nBoth Compose recovery commands failed to execute. Restart error: {}",
                    detail.unwrap_or_default(),
                    err
                )),
                failure_kind: Some(FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR.to_string()),
                runtime_context: Some(runtime.runtime_context.clone()),
                repo_root: runtime.repo_root_display(),
                runtime_home: runtime.runtime_home_display(),
                runtime_root: runtime.runtime_root_display(),
                packaged: Some(runtime.packaged),
                command: Some(combined_command_display),
                stdout,
                stderr,
                exit_code,
            };
        }
    }

    BootstrapRestartResult {
        ok,
        services: BOOTSTRAP_RESTART_SERVICES
            .iter()
            .map(|service| service.to_string())
            .collect(),
        detail,
        failure_kind: None,
        runtime_context: Some(runtime.runtime_context.clone()),
        repo_root: runtime.repo_root_display(),
        runtime_home: runtime.runtime_home_display(),
        runtime_root: runtime.runtime_root_display(),
        packaged: Some(runtime.packaged),
        command: Some(combined_command_display),
        stdout,
        stderr,
        exit_code,
    }
}

fn runtime_readiness_snapshot(runtime: Option<&BootstrapRuntime>) -> RuntimeReadiness {
    let backend_base_url = trim_trailing_slash(&env_first(
        &[
            "CODEXIFY_DESKTOP_BACKEND_URL",
            "VITE_GUARDIAN_API_BASE",
            "GUARDIAN_API_BASE",
        ],
        "http://127.0.0.1:8888",
    ));
    let ping_url = combine_url(&backend_base_url, "/ping");
    let health_url = combine_url(&backend_base_url, "/health");
    let chat_health_url = combine_url(&backend_base_url, "/health/chat");
    let llm_health_url = combine_url(&backend_base_url, "/health/llm");

    let (ping_check, _ping_body) = probe_http_endpoint_with_body(&ping_url, false);
    let (health_check, health_body) = probe_http_endpoint_with_body(&health_url, false);
    let (chat_check, chat_body) = probe_http_endpoint_with_body(&chat_health_url, false);
    let (llm_check, llm_body) = probe_http_endpoint_with_body(&llm_health_url, false);

    let health_json = health_body.as_deref().and_then(parse_json_body);
    let chat_json = chat_body.as_deref().and_then(parse_json_body);
    let llm_json = llm_body.as_deref().and_then(parse_json_body);

    let backend_reachable = ping_check.ok;
    let startup_ready = health_check.ok
        && health_json
            .as_ref()
            .map(|value| json_status_matches(value, "ok"))
            .unwrap_or(false);

    let chat_completion_service = chat_json
        .as_ref()
        .and_then(|value| value.get("completion_service"));
    let redis_ready = chat_completion_service
        .and_then(|value| json_bool_field(value, "redis_reachable"))
        .unwrap_or(false);
    let chat_ready = chat_completion_service
        .and_then(|value| json_bool_field(value, "ok"))
        .unwrap_or(false);
    let chat_status_reason = chat_completion_service
        .and_then(|value| json_string_field(value, "status_reason"))
        .unwrap_or_else(|| "unknown".to_string());

    let llm_provider = llm_json
        .as_ref()
        .and_then(|value| json_string_field(value, "provider"));
    let llm_status = llm_json
        .as_ref()
        .and_then(|value| json_string_field(value, "status"))
        .unwrap_or_else(|| "unknown".to_string());
    let llm_ready = match llm_provider.as_deref() {
        Some(provider) if provider.eq_ignore_ascii_case("local") => Some(
            llm_check.ok
                && llm_json
                    .as_ref()
                    .map(|value| json_status_matches(value, "online"))
                    .unwrap_or(false),
        ),
        Some(_) => None,
        None => Some(false),
    };

    let ready = backend_reachable
        && startup_ready
        && redis_ready
        && chat_ready
        && llm_ready.unwrap_or(true);

    let detail = {
        let mut lines = vec![
            format!("backendBaseUrl={backend_base_url}"),
            format!("backendReachable={}", bool_label(backend_reachable)),
            format!("startupReady={}", bool_label(startup_ready)),
            format!("redisReady={}", bool_label(redis_ready)),
            format!("chatReady={}", bool_label(chat_ready)),
            format!("chatStatusReason={chat_status_reason}"),
            format!(
                "llmProvider={}",
                llm_provider.as_deref().unwrap_or("unknown")
            ),
            format!("llmStatus={llm_status}"),
            format!("llmReady={}", option_bool_label(llm_ready)),
            format!("ready={}", bool_label(ready)),
        ];

        let checks = [&ping_check, &health_check, &chat_check, &llm_check];
        for check in checks {
            let status_fragment = check
                .status_code
                .map(|code| format!(" statusCode={code}"))
                .unwrap_or_default();
            lines.push(format!(
                "{} -> ok={}{}",
                check.endpoint,
                bool_label(check.ok),
                status_fragment
            ));
            if let Some(detail) = &check.detail {
                lines.push(detail.clone());
            }
            if let Some(response_excerpt) = &check.response_excerpt {
                lines.push(response_excerpt.clone());
            }
            lines.push(String::new());
        }

        let rendered = join_lines(lines);
        if rendered.trim().is_empty() {
            None
        } else {
            Some(rendered)
        }
    };

    let failure_kind = if ready {
        None
    } else {
        Some(
            runtime
                .map(|resolved| {
                    phase_failure_kind(
                        resolved,
                        FAILURE_KIND_PACKAGED_READINESS_FAILED,
                        FAILURE_KIND_READINESS_FAILED,
                    )
                })
                .unwrap_or(FAILURE_KIND_READINESS_FAILED)
                .to_string(),
        )
    };

    RuntimeReadiness {
        ok: ready,
        step: "health-check".to_string(),
        ready,
        backend_reachable,
        startup_ready,
        redis_ready,
        chat_ready,
        llm_ready,
        detail,
        failure_kind,
        runtime_context: runtime.map(|resolved| resolved.runtime_context.clone()),
        repo_root: runtime.and_then(|resolved| resolved.repo_root_display()),
        runtime_home: runtime.and_then(|resolved| resolved.runtime_home_display()),
        runtime_root: runtime.and_then(|resolved| resolved.runtime_root_display()),
        packaged: runtime.map(|resolved| resolved.packaged),
        command: Some(format!(
            "GET {ping_url}; GET {health_url}; GET {chat_health_url}; GET {llm_health_url}"
        )),
        checks: vec![ping_check, health_check, chat_check, llm_check],
    }
}

#[tauri::command]
pub fn desktop_runtime_readiness_check(
    runtime: tauri::State<'_, BootstrapRuntime>,
) -> RuntimeReadiness {
    runtime_readiness_snapshot(Some(&*runtime))
}

#[tauri::command]
pub fn desktop_runtime_health_check(
    runtime: tauri::State<'_, BootstrapRuntime>,
) -> RuntimeReadiness {
    runtime_readiness_snapshot(Some(&*runtime))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::fs;
    use std::time::{SystemTime, UNIX_EPOCH};

    fn unique_temp_dir(prefix: &str) -> PathBuf {
        let stamp = SystemTime::now()
            .duration_since(UNIX_EPOCH)
            .expect("system time before UNIX_EPOCH")
            .as_nanos();
        let path = std::env::temp_dir().join(format!("{prefix}-{stamp}-{}", std::process::id()));
        fs::create_dir_all(&path).expect("failed to create temp dir");
        path
    }

    #[test]
    fn packaged_runtime_assets_refuse_unmanaged_existing_root() {
        let root = unique_temp_dir("codexify-packaged-root-conflict");
        let runtime_root = root.join("runtime");
        let resource_root = root.join("bundle");
        fs::create_dir_all(&runtime_root).expect("failed to create runtime root");
        fs::create_dir_all(&resource_root).expect("failed to create resource root");
        fs::write(runtime_root.join("unrelated.txt"), "source-checkout")
            .expect("failed to write sentinel");

        let err = materialize_packaged_runtime_assets(&resource_root, &runtime_root)
            .expect_err("expected unmanaged runtime root to be rejected");

        assert_eq!(
            err.failure_kind,
            FAILURE_KIND_PACKAGED_RUNTIME_MATERIALIZATION_FAILED
        );
        assert!(err
            .detail
            .contains("Refusing to overwrite a pre-existing non-managed directory."));

        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn packaged_setup_env_migrates_legacy_env_into_runtime_root() {
        let root = unique_temp_dir("codexify-packaged-env-migration");
        let runtime_home = root.join("Application Support").join("Codexify");
        let runtime_root = root.join("Codexify");
        fs::create_dir_all(&runtime_home).expect("failed to create runtime home");
        fs::create_dir_all(&runtime_root).expect("failed to create runtime root");

        let legacy_chroma = runtime_home.join(".chroma");
        let legacy_models = runtime_home.join("models");
        fs::create_dir_all(&legacy_chroma).expect("failed to create legacy chroma dir");
        fs::create_dir_all(&legacy_models).expect("failed to create legacy models dir");

        let legacy_env = runtime_home.join(".env");
        fs::write(
            &legacy_env,
            [
                "GUARDIAN_API_KEY=legacy-api-key",
                "LOCAL_CHAT_MODEL=legacy-model",
                "ALLOW_CLOUD_PROVIDERS=true",
                "",
            ]
            .join("\n"),
        )
        .expect("failed to seed legacy env");
        fs::write(legacy_chroma.join("chroma.sqlite3"), "legacy-chroma")
            .expect("failed to seed legacy chroma data");
        fs::write(legacy_models.join("model.cache"), "legacy-models")
            .expect("failed to seed legacy models data");

        let result = materialize_packaged_setup_env(Some(runtime_home.as_path()), &runtime_root)
            .expect("expected packaged setup env materialization to succeed");

        assert_eq!(result.migrated_legacy_env_source, Some(legacy_env.clone()));
        assert!(result
            .migrated_legacy_runtime_assets
            .contains(&".chroma".to_string()));
        assert!(result
            .migrated_legacy_runtime_assets
            .contains(&"models".to_string()));
        assert!(!result.created_new_env_file);
        assert!(result
            .preserved_keys
            .contains(&"GUARDIAN_API_KEY".to_string()));
        assert!(result
            .preserved_keys
            .contains(&"LOCAL_CHAT_MODEL".to_string()));

        let written = fs::read_to_string(result.env_path).expect("failed to read migrated env");
        assert!(written.contains("GUARDIAN_API_KEY=legacy-api-key"));
        assert!(written.contains("VITE_GUARDIAN_API_KEY=legacy-api-key"));
        assert!(written.contains("LOCAL_CHAT_MODEL=legacy-model"));
        assert!(written.contains("ALLOW_CLOUD_PROVIDERS=true"));
        assert!(written.contains("NEO4J_PASS=codexify"));
        assert_eq!(
            fs::read_to_string(runtime_root.join(".chroma").join("chroma.sqlite3"))
                .expect("failed to read migrated chroma data"),
            "legacy-chroma"
        );
        assert_eq!(
            fs::read_to_string(runtime_root.join("models").join("model.cache"))
                .expect("failed to read migrated model data"),
            "legacy-models"
        );

        fs::remove_dir_all(&root).ok();
    }

    #[test]
    fn desktop_media_fetch_path_requires_canonical_media_path() {
        assert_eq!(
            normalize_desktop_media_fetch_path("/media/images/example.png")
                .expect("expected canonical media path"),
            "/media/images/example.png"
        );

        let external = normalize_desktop_media_fetch_path("https://example.com/example.png")
            .expect_err("expected external URL to be rejected");
        assert_eq!(external.kind, "invalid_path");

        let query = normalize_desktop_media_fetch_path("/media/images/example.png?sig=123")
            .expect_err("expected signed URL to be rejected");
        assert_eq!(query.kind, "invalid_path");

        let traversal = normalize_desktop_media_fetch_path("/media/../secrets.txt")
            .expect_err("expected traversal path to be rejected");
        assert_eq!(traversal.kind, "invalid_path");
    }

    #[test]
    fn desktop_media_content_type_guard_enforces_image_contract() {
        desktop_media_content_type_guard("image/png")
            .expect("expected image/png to pass content-type guard");
        desktop_media_content_type_guard("image/webp; charset=binary")
            .expect("expected image/webp to pass content-type guard");

        let err = desktop_media_content_type_guard("application/json")
            .expect_err("expected non-image content type to be rejected");
        assert_eq!(err.kind, "type_not_allowed");
    }

    #[test]
    fn desktop_media_size_guard_enforces_byte_ceiling() {
        desktop_media_size_guard(DESKTOP_MEDIA_MAX_BYTES)
            .expect("expected payload at limit to pass size guard");

        let err = desktop_media_size_guard(DESKTOP_MEDIA_MAX_BYTES + 1)
            .expect_err("expected oversize payload to be rejected");
        assert_eq!(err.kind, "too_large");
    }
}
