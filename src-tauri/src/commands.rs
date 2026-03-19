use serde::Serialize;
use serde_json::Value;
use std::collections::HashSet;
use std::env;
use std::ffi::OsStr;
use std::fs;
use std::io::{ErrorKind, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

const DESKTOP_KEYCHAIN_SERVICE: &str = "com.codexify.desktop";
const DESKTOP_KEYCHAIN_ACCOUNT: &str = "guardian_api_key";
const NORMALIZED_DOCKER_PATH: &str = "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin";
const BOOTSTRAP_LOG_TAIL_LINES: &str = "200";
const BOOTSTRAP_LOG_SERVICES: [&str; 5] = ["backend", "worker-chat", "db", "redis", "migrator"];
const BOOTSTRAP_RESTART_SERVICES: [&str; 5] = ["db", "redis", "migrator", "backend", "worker-chat"];
const FAILURE_KIND_RUNTIME_PATH_UNAVAILABLE: &str = "runtime-path-unavailable";
const FAILURE_KIND_REPO_RUNTIME_MISSING: &str = "repo-runtime-missing";
const FAILURE_KIND_PACKAGED_BOOTSTRAP_UNSUPPORTED: &str = "packaged-bootstrap-unsupported";
const FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR: &str = "unexpected-execution-error";
const RUNTIME_CONTEXT_DEVELOPMENT: &str = "development";
const RUNTIME_CONTEXT_PACKAGED: &str = "packaged";

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
    DockerCliInvocationFailed,
    DockerComposeUnavailable,
    DockerDaemonUnreachable,
    UnexpectedCommandExecutionError,
}

impl FailureKind {
    fn as_str(self) -> &'static str {
        match self {
            Self::DockerBinaryNotFound => "docker-binary-not-found",
            Self::DockerCliInvocationFailed => "docker-cli-invocation-failed",
            Self::DockerComposeUnavailable => "docker-compose-unavailable",
            Self::DockerDaemonUnreachable => "docker-daemon-unreachable",
            Self::UnexpectedCommandExecutionError => "unexpected-command-execution-error",
        }
    }

    fn summary(self) -> &'static str {
        match self {
            Self::DockerBinaryNotFound => "Docker binary not found",
            Self::DockerCliInvocationFailed => "Docker CLI invocation failed",
            Self::DockerComposeUnavailable => "Docker Compose unavailable",
            Self::DockerDaemonUnreachable => "Docker daemon unreachable",
            Self::UnexpectedCommandExecutionError => "Unexpected command execution error",
        }
    }
}

#[derive(Debug)]
struct ResolvedDockerBinary {
    command: String,
    display: String,
    resolution_detail: String,
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
struct ResolvedRuntimeRepo {
    repo_root: PathBuf,
    runtime_context: &'static str,
    packaged: bool,
    resolution_detail: String,
}

#[derive(Debug)]
struct RuntimeRepoResolutionError {
    failure_kind: &'static str,
    runtime_context: &'static str,
    packaged: bool,
    detail: String,
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

fn build_context_lines(label: &str, binary: &ResolvedDockerBinary) -> Vec<String> {
    vec![
        format!("{label}:"),
        format!("binary: {}", binary.display),
        format!("PATH: {NORMALIZED_DOCKER_PATH}"),
    ]
}

fn spawn_docker_command(binary: &ResolvedDockerBinary, args: &[&str]) -> Command {
    let mut command = Command::new(&binary.command);
    command.args(args).env("PATH", NORMALIZED_DOCKER_PATH);

    if let Ok(home) = env::var("HOME") {
        command.env("HOME", &home);
        command.env("DOCKER_CONFIG", format!("{home}/.docker"));
    }

    command
}

fn resolve_docker_binary() -> Result<ResolvedDockerBinary, CommandProbe> {
    let mut detail_lines = vec![format!("PATH: {NORMALIZED_DOCKER_PATH}")];
    let mut candidate_failures = Vec::new();
    let mut seen_resolved_paths = HashSet::new();

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

            if !seen_resolved_paths.insert(resolved_display.clone()) {
                detail_lines.push(format!(
                    "candidate duplicates previously tested path: {resolved_display}"
                ));
                continue;
            }

            let mut probe = Command::new(&resolved_path);
            probe.arg("--version").env("PATH", NORMALIZED_DOCKER_PATH);
            if let Ok(home) = env::var("HOME") {
                probe.env("HOME", &home);
                probe.env("DOCKER_CONFIG", format!("{home}/.docker"));
            }

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
                    });
                }
                Ok(output) => {
                    detail_lines.push(format!(
                        "candidate failed `docker --version`: {resolved_display}"
                    ));
                    detail_lines.push(format!("exit status: {}", output.status));
                    detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
                    candidate_failures.push(FailureKind::DockerCliInvocationFailed);
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
                    candidate_failures.push(FailureKind::UnexpectedCommandExecutionError);
                }
            }
        }
    }

    let mut fallback = Command::new("docker");
    fallback
        .arg("--version")
        .env("PATH", NORMALIZED_DOCKER_PATH);
    if let Ok(home) = env::var("HOME") {
        fallback.env("HOME", &home);
        fallback.env("DOCKER_CONFIG", format!("{home}/.docker"));
    }

    match fallback.output() {
        Ok(output) if output.status.success() => {
            detail_lines.push("resolved docker binary from PATH fallback: docker".to_string());
            detail_lines.extend(render_probe_output(&output.stdout, &output.stderr));
            Ok(ResolvedDockerBinary {
                command: "docker".to_string(),
                display: "docker".to_string(),
                resolution_detail: join_lines(detail_lines),
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
                FailureKind::DockerCliInvocationFailed,
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
                FailureKind::UnexpectedCommandExecutionError,
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

fn has_repo_runtime_hints(candidate: &Path) -> bool {
    candidate.join(".git").exists()
        || candidate.join("docker-compose.yml").exists()
        || candidate.join("guardian").exists()
        || candidate.join("frontend").exists()
        || candidate.join("src-tauri").exists()
}

fn find_repo_root_from_ancestors(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find(|candidate| is_repo_runtime_root(candidate))
        .map(Path::to_path_buf)
}

fn find_repo_hint_from_ancestors(start: &Path) -> Option<PathBuf> {
    start
        .ancestors()
        .find(|candidate| has_repo_runtime_hints(candidate))
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

fn build_runtime_resolution_detail(lines: Vec<String>) -> String {
    join_lines(lines)
}

fn resolve_repo_root() -> Result<ResolvedRuntimeRepo, RuntimeRepoResolutionError> {
    let current_exe = env::current_exe().map_err(|err| RuntimeRepoResolutionError {
        failure_kind: FAILURE_KIND_RUNTIME_PATH_UNAVAILABLE,
        runtime_context: RUNTIME_CONTEXT_DEVELOPMENT,
        packaged: false,
        detail: build_runtime_resolution_detail(vec![
            "runtime repo resolution: failed".to_string(),
            format!("currentExeError={err}"),
        ]),
    })?;

    let packaged_bundle = find_macos_app_bundle(&current_exe);
    let packaged = packaged_bundle.is_some();
    let runtime_context = if packaged {
        RUNTIME_CONTEXT_PACKAGED
    } else {
        RUNTIME_CONTEXT_DEVELOPMENT
    };

    let mut detail_lines = vec![
        "runtime repo resolution:".to_string(),
        format!("runtimeContext={runtime_context}"),
        format!("packaged={packaged}"),
        format!("currentExe={}", current_exe.display()),
    ];

    if let Some(bundle) = &packaged_bundle {
        detail_lines.push(format!("appBundle={}", bundle.display()));
    }

    if let Ok(current_dir) = env::current_dir() {
        detail_lines.push(format!("currentDir={}", current_dir.display()));
    }

    if let Some(override_root) = env::var_os("CODEXIFY_DESKTOP_REPO_ROOT") {
        let override_path = PathBuf::from(override_root);
        detail_lines.push(format!(
            "repoRootOverride={}",
            override_path.display()
        ));

        if is_repo_runtime_root(&override_path) {
            detail_lines.push("repo root resolved from CODEXIFY_DESKTOP_REPO_ROOT.".to_string());
            return Ok(ResolvedRuntimeRepo {
                repo_root: override_path,
                runtime_context,
                packaged,
                resolution_detail: build_runtime_resolution_detail(detail_lines),
            });
        }

        detail_lines.push(
            "The explicit CODEXIFY_DESKTOP_REPO_ROOT override did not contain the required Codexify runtime files."
                .to_string(),
        );
        return Err(RuntimeRepoResolutionError {
            failure_kind: FAILURE_KIND_REPO_RUNTIME_MISSING,
            runtime_context,
            packaged,
            detail: build_runtime_resolution_detail(detail_lines),
        });
    }

    if packaged {
        if let Some(repo_root) = find_repo_root_from_ancestors(&current_exe) {
            detail_lines.push(format!(
                "repo root resolved from packaged executable ancestors: {}",
                repo_root.display()
            ));
            return Ok(ResolvedRuntimeRepo {
                repo_root,
                runtime_context,
                packaged,
                resolution_detail: build_runtime_resolution_detail(detail_lines),
            });
        }

        if let Some(bundle) = &packaged_bundle {
            if let Some(repo_root) = find_repo_root_from_ancestors(bundle) {
                detail_lines.push(format!(
                    "repo root resolved from packaged app bundle ancestors: {}",
                    repo_root.display()
                ));
                return Ok(ResolvedRuntimeRepo {
                    repo_root,
                    runtime_context,
                    packaged,
                    resolution_detail: build_runtime_resolution_detail(detail_lines),
                });
            }
        }

        if let Some(hint_root) = find_repo_hint_from_ancestors(&current_exe) {
            detail_lines.push(format!(
                "Found a partial repo-like ancestor, but the required runtime files were missing: {}",
                hint_root.display()
            ));
            detail_lines.push(
                "Required files: docker-compose.yml, guardian/, frontend/, and src-tauri/."
                    .to_string(),
            );
            return Err(RuntimeRepoResolutionError {
                failure_kind: FAILURE_KIND_REPO_RUNTIME_MISSING,
                runtime_context,
                packaged,
                detail: build_runtime_resolution_detail(detail_lines),
            });
        }

        detail_lines.push(
            "The packaged app is not running inside a supported local Codexify repo context."
                .to_string(),
        );
        detail_lines.push(
            "Supported packaged beta context: run the built .app from a Codexify checkout or set CODEXIFY_DESKTOP_REPO_ROOT explicitly."
                .to_string(),
        );
        return Err(RuntimeRepoResolutionError {
            failure_kind: FAILURE_KIND_PACKAGED_BOOTSTRAP_UNSUPPORTED,
            runtime_context,
            packaged,
            detail: build_runtime_resolution_detail(detail_lines),
        });
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
        return Ok(ResolvedRuntimeRepo {
            repo_root,
            runtime_context,
            packaged,
            resolution_detail: build_runtime_resolution_detail(detail_lines),
        });
    }

    if let Ok(current_dir) = env::current_dir() {
        if let Some(repo_root) = find_repo_root_from_ancestors(&current_dir) {
            detail_lines.push(format!(
                "repo root resolved from working directory ancestors: {}",
                repo_root.display()
            ));
            return Ok(ResolvedRuntimeRepo {
                repo_root,
                runtime_context,
                packaged,
                resolution_detail: build_runtime_resolution_detail(detail_lines),
            });
        }
    }

    detail_lines.push(
        "Unable to resolve the Codexify repo root from the active development runtime."
            .to_string(),
    );
    Err(RuntimeRepoResolutionError {
        failure_kind: FAILURE_KIND_REPO_RUNTIME_MISSING,
        runtime_context,
        packaged,
        detail: build_runtime_resolution_detail(detail_lines),
    })
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
    context: Option<&ResolvedRuntimeRepo>,
    failure_kind: Option<&str>,
) -> BootstrapStepResult {
    BootstrapStepResult {
        ok,
        step: step.to_string(),
        detail,
        failure_kind: failure_kind.map(str::to_string),
        runtime_context: context.map(|resolved| resolved.runtime_context.to_string()),
        repo_root: context.map(|resolved| resolved.repo_root.display().to_string()),
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

fn build_compose_runtime_lines(context: &ResolvedRuntimeRepo) -> Vec<String> {
    vec![
        format!("runtimeContext={}", context.runtime_context),
        format!("packaged={}", context.packaged),
        format!("repoRoot={}", context.repo_root.display()),
        format!(
            "composeFile={}",
            context.repo_root.join("docker-compose.yml").display()
        ),
    ]
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
    value.get(key).and_then(|entry| entry.as_str()).and_then(|text| {
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
            let response_excerpt = body
                .as_deref()
                .map(|body| truncate_chars(body, 240));
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
    let backend_base_url = trim_trailing_slash(&env_first(
        &[
            "CODEXIFY_DESKTOP_BACKEND_URL",
            "VITE_GUARDIAN_API_BASE",
            "GUARDIAN_API_BASE",
        ],
        "http://127.0.0.1:8888",
    ));
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
pub fn desktop_runtime_preflight_check() -> RuntimePreflight {
    let runtime_repo = resolve_repo_root();
    let (runtime_context, packaged, repo_root, runtime_probe, runtime_failure_kind) =
        match &runtime_repo {
            Ok(resolved) => (
                Some(resolved.runtime_context.to_string()),
                Some(resolved.packaged),
                Some(resolved.repo_root.display().to_string()),
                CommandProbe::success(resolved.resolution_detail.clone()),
                None,
            ),
            Err(err) => (
                Some(err.runtime_context.to_string()),
                Some(err.packaged),
                None,
                CommandProbe::failure(
                    FailureKind::UnexpectedCommandExecutionError,
                    err.detail.clone(),
                ),
                Some(err.failure_kind.to_string()),
            ),
        };

    match resolve_docker_binary() {
        Ok(binary) => {
            let resolution_probe = CommandProbe::success(format!(
                "docker binary resolution:\n{}",
                binary.resolution_detail
            ));
            let cli_probe = run_probe(
                &binary,
                &["--version"],
                "docker --version",
                FailureKind::DockerCliInvocationFailed,
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
                && runtime_repo.is_ok();
            let detail = build_preflight_detail(&[
                runtime_probe,
                resolution_probe,
                cli_probe,
                compose_probe,
                daemon_probe,
            ]);
            let failure_kind = failure_kind.or(runtime_failure_kind);

            RuntimePreflight {
                docker_cli_installed: true,
                docker_compose_available,
                docker_daemon_reachable,
                ready,
                detail,
                failure_kind,
                runtime_context,
                repo_root,
                packaged,
            }
        }
        Err(resolution_probe) => {
            let failure_kind = resolution_probe
                .failure_kind
                .map(|kind| kind.as_str().to_string())
                .or(runtime_failure_kind);
            RuntimePreflight {
                docker_cli_installed: false,
                docker_compose_available: false,
                docker_daemon_reachable: false,
                ready: false,
                detail: build_preflight_detail(&[runtime_probe, resolution_probe]),
                failure_kind,
                runtime_context,
                repo_root,
                packaged,
            }
        }
    }
}

#[tauri::command]
pub fn desktop_run_setup_cli() -> BootstrapStepResult {
    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapStepResult {
                ok: false,
                step: "setup".to_string(),
                detail: Some(err.detail),
                failure_kind: Some(err.failure_kind.to_string()),
                runtime_context: Some(err.runtime_context.to_string()),
                repo_root: None,
                packaged: Some(err.packaged),
                command: None,
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };
    let python = resolve_python_binary(&repo_root.repo_root);
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

root = Path({repo_root:?}).resolve()
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
        repo_root = repo_root.repo_root.display().to_string()
    );

    match Command::new(&python)
        .args(["-c", &script])
        .current_dir(&repo_root.repo_root)
        .output()
    {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let detail = render_step_detail(
                vec![
                    format!("runtimeContext={}", repo_root.runtime_context),
                    format!("packaged={}", repo_root.packaged),
                    format!("repoRoot={}", repo_root.repo_root.display()),
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
                Some(&repo_root),
                None,
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
            Some(&repo_root),
            Some(FAILURE_KIND_UNEXPECTED_EXECUTION_ERROR),
        ),
    }
}

#[tauri::command]
pub fn desktop_compose_up() -> BootstrapStepResult {
    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapStepResult {
                ok: false,
                step: "compose-up".to_string(),
                detail: Some(err.detail),
                failure_kind: Some(err.failure_kind.to_string()),
                runtime_context: Some(err.runtime_context.to_string()),
                repo_root: None,
                packaged: Some(err.packaged),
                command: None,
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary() {
        Ok(binary) => binary,
        Err(probe) => {
            return build_step_result(
                false,
                "compose-up",
                Some(probe.detail),
                Some("docker compose up -d".to_string()),
                None,
                None,
                None,
                Some(&repo_root),
                probe.failure_kind.map(FailureKind::as_str),
            )
        }
    };
    let command_display = format!("{} compose up -d", docker.display);

    match spawn_docker_command(&docker, &["compose", "up", "-d"])
        .current_dir(&repo_root.repo_root)
        .output()
    {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let detail = render_step_detail(
                {
                    let mut lines = build_compose_runtime_lines(&repo_root);
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
                Some(&repo_root),
                None,
            )
        }
        Err(err) => build_step_result(
            false,
            "compose-up",
            Some(format!("Failed to execute docker compose up -d: {err}")),
            Some(command_display),
            None,
            None,
            None,
            Some(&repo_root),
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
                        detail_lines
                            .extend(render_probe_output(&fallback_output.stdout, &fallback_output.stderr));
                        BootstrapDockerOpenResult {
                            ok: true,
                            detail: Some(join_lines(detail_lines)),
                            command: Some(format!("{primary_command} || {fallback_command}")),
                        }
                    }
                    Ok(fallback_output) => {
                        detail_lines.push("Fallback app-bundle open failed.".to_string());
                        detail_lines.push(format!("fallback status={}", fallback_output.status));
                        detail_lines
                            .extend(render_probe_output(&fallback_output.stdout, &fallback_output.stderr));
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
pub fn desktop_get_bootstrap_logs(service: String) -> BootstrapLogResult {
    let requested_service = service.trim().to_string();
    let service = match normalize_bootstrap_service(&requested_service) {
        Ok(service) => service,
        Err(detail) => {
            return BootstrapLogResult {
                ok: false,
                service: requested_service,
                detail: Some(detail),
                failure_kind: None,
                runtime_context: None,
                repo_root: None,
                packaged: None,
                logs: None,
                command: None,
                exit_code: None,
            }
        }
    };

    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapLogResult {
                ok: false,
                service: service.to_string(),
                detail: Some(err.detail),
                failure_kind: Some(err.failure_kind.to_string()),
                runtime_context: Some(err.runtime_context.to_string()),
                repo_root: None,
                packaged: Some(err.packaged),
                logs: None,
                command: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary() {
        Ok(binary) => binary,
        Err(probe) => {
            return BootstrapLogResult {
                ok: false,
                service: service.to_string(),
                detail: Some(probe.detail),
                failure_kind: probe.failure_kind.map(|kind| kind.as_str().to_string()),
                runtime_context: Some(repo_root.runtime_context.to_string()),
                repo_root: Some(repo_root.repo_root.display().to_string()),
                packaged: Some(repo_root.packaged),
                logs: None,
                command: Some(format!("docker compose logs --tail {BOOTSTRAP_LOG_TAIL_LINES} --no-color {service}")),
                exit_code: None,
            }
        }
    };

    let command_display = format!(
        "{} compose logs --tail {} --no-color {}",
        docker.display, BOOTSTRAP_LOG_TAIL_LINES, service
    );

    match spawn_docker_command(
        &docker,
        &[
            "compose",
            "logs",
            "--tail",
            BOOTSTRAP_LOG_TAIL_LINES,
            "--no-color",
            service,
        ],
    )
    .current_dir(&repo_root.repo_root)
    .output()
    {
        Ok(output) => {
            let logs = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let mut detail_lines = build_compose_runtime_lines(&repo_root);
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
                runtime_context: Some(repo_root.runtime_context.to_string()),
                repo_root: Some(repo_root.repo_root.display().to_string()),
                packaged: Some(repo_root.packaged),
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
            runtime_context: Some(repo_root.runtime_context.to_string()),
            repo_root: Some(repo_root.repo_root.display().to_string()),
            packaged: Some(repo_root.packaged),
            logs: None,
            command: Some(command_display),
            exit_code: None,
        },
    }
}

#[tauri::command]
pub fn desktop_restart_runtime_services() -> BootstrapRestartResult {
    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(err) => {
            return BootstrapRestartResult {
                ok: false,
                services: BOOTSTRAP_RESTART_SERVICES
                    .iter()
                    .map(|service| service.to_string())
                    .collect(),
                detail: Some(err.detail),
                failure_kind: Some(err.failure_kind.to_string()),
                runtime_context: Some(err.runtime_context.to_string()),
                repo_root: None,
                packaged: Some(err.packaged),
                command: None,
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };
    let docker = match resolve_docker_binary() {
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
                runtime_context: Some(repo_root.runtime_context.to_string()),
                repo_root: Some(repo_root.repo_root.display().to_string()),
                packaged: Some(repo_root.packaged),
                command: Some(format!(
                    "docker compose restart {} && docker compose up -d {}",
                    ["db", "redis", "backend", "worker-chat"].join(" "),
                    BOOTSTRAP_RESTART_SERVICES.join(" ")
                )),
                stdout: None,
                stderr: None,
                exit_code: None,
            }
        }
    };

    let restart_services = ["db", "redis", "backend", "worker-chat"];
    let restart_command_display = format!(
        "{} compose restart {}",
        docker.display,
        restart_services.join(" ")
    );
    let up_command_display = format!(
        "{} compose up -d {}",
        docker.display,
        BOOTSTRAP_RESTART_SERVICES.join(" ")
    );
    let combined_command_display =
        format!("{restart_command_display} && {up_command_display}");

    let restart_output = spawn_docker_command(
        &docker,
        &[
            "compose",
            "restart",
            "db",
            "redis",
            "backend",
            "worker-chat",
        ],
    )
    .current_dir(&repo_root.repo_root)
    .output();

    let up_output = spawn_docker_command(
        &docker,
        &[
            "compose",
            "up",
            "-d",
            "db",
            "redis",
            "migrator",
            "backend",
            "worker-chat",
        ],
    )
    .current_dir(&repo_root.repo_root)
    .output();

    let mut detail_lines = build_compose_runtime_lines(&repo_root);
    detail_lines.push(format!(
        "services={}",
        BOOTSTRAP_RESTART_SERVICES.join(",")
    ));

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
                runtime_context: Some(repo_root.runtime_context.to_string()),
                repo_root: Some(repo_root.repo_root.display().to_string()),
                packaged: Some(repo_root.packaged),
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
        runtime_context: Some(repo_root.runtime_context.to_string()),
        repo_root: Some(repo_root.repo_root.display().to_string()),
        packaged: Some(repo_root.packaged),
        command: Some(combined_command_display),
        stdout,
        stderr,
        exit_code,
    }
}

fn runtime_readiness_snapshot() -> RuntimeReadiness {
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
    let (health_check, health_body) =
        probe_http_endpoint_with_body(&health_url, false);
    let (chat_check, chat_body) =
        probe_http_endpoint_with_body(&chat_health_url, false);
    let (llm_check, llm_body) =
        probe_http_endpoint_with_body(&llm_health_url, false);

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

    let ready =
        backend_reachable && startup_ready && redis_ready && chat_ready && llm_ready.unwrap_or(true);

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
        command: Some(format!(
            "GET {ping_url}; GET {health_url}; GET {chat_health_url}; GET {llm_health_url}"
        )),
        checks: vec![ping_check, health_check, chat_check, llm_check],
    }
}

#[tauri::command]
pub fn desktop_runtime_readiness_check() -> RuntimeReadiness {
    runtime_readiness_snapshot()
}

#[tauri::command]
pub fn desktop_runtime_health_check() -> RuntimeReadiness {
    runtime_readiness_snapshot()
}
