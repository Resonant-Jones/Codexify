use serde::Serialize;
use std::collections::HashSet;
use std::env;
use std::fs;
use std::io::{ErrorKind, Read, Write};
use std::net::{TcpStream, ToSocketAddrs};
use std::path::{Path, PathBuf};
use std::process::Command;
use std::time::Duration;

const DESKTOP_KEYCHAIN_SERVICE: &str = "com.codexify.desktop";
const DESKTOP_KEYCHAIN_ACCOUNT: &str = "guardian_api_key";
const NORMALIZED_DOCKER_PATH: &str = "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin";

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
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
pub struct BootstrapStepResult {
    pub ok: bool,
    pub step: String,
    pub detail: Option<String>,
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
pub struct RuntimeHealthCheckResult {
    pub ok: bool,
    pub step: String,
    pub ready: bool,
    pub detail: Option<String>,
    #[serde(skip_serializing_if = "Option::is_none")]
    pub command: Option<String>,
    pub checks: Vec<HealthEndpointCheck>,
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

fn resolve_repo_root() -> Result<PathBuf, String> {
    let manifest_dir = PathBuf::from(env!("CARGO_MANIFEST_DIR"));
    let manifest_candidate = manifest_dir
        .parent()
        .map(Path::to_path_buf)
        .unwrap_or_else(|| manifest_dir.clone());

    for candidate in [
        manifest_candidate,
        env::current_dir().unwrap_or_else(|_| PathBuf::from(".")),
    ] {
        if candidate.join("docker-compose.yml").is_file()
            && candidate.join("guardian").is_dir()
            && candidate.join("frontend").is_dir()
        {
            return Ok(candidate);
        }
    }

    Err("Unable to resolve the Codexify repo root from the Tauri runtime.".to_string())
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
) -> BootstrapStepResult {
    BootstrapStepResult {
        ok,
        step: step.to_string(),
        detail,
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

fn probe_http_endpoint(url: &str, allow_client_errors: bool) -> HealthEndpointCheck {
    let parsed = match parse_http_url(url) {
        Ok(parsed) => parsed,
        Err(detail) => {
            return HealthEndpointCheck {
                endpoint: url.to_string(),
                ok: false,
                status_code: None,
                detail: Some(detail),
                response_excerpt: None,
            }
        }
    };

    let address = format!("{}:{}", parsed.host, parsed.port);
    let socket_addr = match address.to_socket_addrs() {
        Ok(mut addrs) => match addrs.next() {
            Some(addr) => addr,
            None => {
                return HealthEndpointCheck {
                    endpoint: url.to_string(),
                    ok: false,
                    status_code: None,
                    detail: Some(format!("No socket addresses resolved for {address}")),
                    response_excerpt: None,
                }
            }
        },
        Err(err) => {
            return HealthEndpointCheck {
                endpoint: url.to_string(),
                ok: false,
                status_code: None,
                detail: Some(format!("Failed to resolve {address}: {err}")),
                response_excerpt: None,
            }
        }
    };

    let timeout = Duration::from_secs(2);
    let mut stream = match TcpStream::connect_timeout(&socket_addr, timeout) {
        Ok(stream) => stream,
        Err(err) => {
            return HealthEndpointCheck {
                endpoint: url.to_string(),
                ok: false,
                status_code: None,
                detail: Some(format!("TCP connect failed: {err}")),
                response_excerpt: None,
            }
        }
    };

    let _ = stream.set_read_timeout(Some(timeout));
    let _ = stream.set_write_timeout(Some(timeout));

    let request = format!(
        "GET {} HTTP/1.1\r\nHost: {}\r\nConnection: close\r\nUser-Agent: codexify-tauri-bootstrap\r\nAccept: application/json\r\n\r\n",
        parsed.path, parsed.host
    );

    if let Err(err) = stream.write_all(request.as_bytes()) {
        return HealthEndpointCheck {
            endpoint: url.to_string(),
            ok: false,
            status_code: None,
            detail: Some(format!("Failed to write request: {err}")),
            response_excerpt: None,
        };
    }

    let mut response = String::new();
    if let Err(err) = stream.read_to_string(&mut response) {
        return HealthEndpointCheck {
            endpoint: url.to_string(),
            ok: false,
            status_code: None,
            detail: Some(format!("Failed to read response: {err}")),
            response_excerpt: None,
        };
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
    let response_excerpt = if body.is_empty() {
        None
    } else {
        Some(truncate_chars(&body, 240))
    };

    let ok = match status_code {
        Some(code) if allow_client_errors => (200..500).contains(&code),
        Some(code) => (200..300).contains(&code),
        None => false,
    };
    let detail = if status_line.is_empty() {
        Some("Missing HTTP status line in response.".to_string())
    } else {
        Some(status_line)
    };

    HealthEndpointCheck {
        endpoint: url.to_string(),
        ok,
        status_code,
        detail,
        response_excerpt,
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

            let ready = cli_probe.ok && docker_compose_available && docker_daemon_reachable;
            let detail =
                build_preflight_detail(&[resolution_probe, cli_probe, compose_probe, daemon_probe]);

            RuntimePreflight {
                docker_cli_installed: true,
                docker_compose_available,
                docker_daemon_reachable,
                ready,
                detail,
                failure_kind,
            }
        }
        Err(resolution_probe) => {
            let failure_kind = resolution_probe
                .failure_kind
                .map(|kind| kind.as_str().to_string());
            RuntimePreflight {
                docker_cli_installed: false,
                docker_compose_available: false,
                docker_daemon_reachable: false,
                ready: false,
                detail: build_preflight_detail(&[resolution_probe]),
                failure_kind,
            }
        }
    }
}

#[tauri::command]
pub fn desktop_run_setup_cli() -> BootstrapStepResult {
    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(detail) => {
            return build_step_result(false, "setup", Some(detail), None, None, None, None)
        }
    };
    let python = resolve_python_binary(&repo_root);
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
        repo_root = repo_root.display().to_string()
    );

    match Command::new(&python)
        .args(["-c", &script])
        .current_dir(&repo_root)
        .output()
    {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let detail = render_step_detail(
                vec![
                    format!("repoRoot={}", repo_root.display()),
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
        ),
    }
}

#[tauri::command]
pub fn desktop_compose_up() -> BootstrapStepResult {
    let repo_root = match resolve_repo_root() {
        Ok(path) => path,
        Err(detail) => {
            return build_step_result(false, "compose-up", Some(detail), None, None, None, None)
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
            )
        }
    };
    let command_display = format!("{} compose up -d", docker.display);

    match spawn_docker_command(&docker, &["compose", "up", "-d"])
        .current_dir(&repo_root)
        .output()
    {
        Ok(output) => {
            let stdout = normalize_output(&output.stdout);
            let stderr = normalize_output(&output.stderr);
            let detail = render_step_detail(
                vec![
                    format!("repoRoot={}", repo_root.display()),
                    format!(
                        "composeFile={}",
                        repo_root.join("docker-compose.yml").display()
                    ),
                    format!("status={}", output.status),
                ],
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
        ),
    }
}

#[tauri::command]
pub fn desktop_runtime_health_check() -> RuntimeHealthCheckResult {
    let backend_base_url = trim_trailing_slash(&env_first(
        &[
            "CODEXIFY_DESKTOP_BACKEND_URL",
            "VITE_GUARDIAN_API_BASE",
            "GUARDIAN_API_BASE",
        ],
        "http://127.0.0.1:8888",
    ));
    let ping_url = combine_url(&backend_base_url, "/ping");
    let llm_health_url = combine_url(&backend_base_url, "/api/health/llm");

    let checks = vec![
        probe_http_endpoint(&ping_url, false),
        probe_http_endpoint(&llm_health_url, true),
    ];
    let ready = checks.iter().all(|check| check.ok);
    let detail = {
        let mut lines = vec![format!("backendBaseUrl={backend_base_url}")];
        for check in &checks {
            let status_fragment = check
                .status_code
                .map(|code| format!(" statusCode={code}"))
                .unwrap_or_default();
            lines.push(format!(
                "{} -> ok={}{}",
                check.endpoint, check.ok, status_fragment
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

    RuntimeHealthCheckResult {
        ok: ready,
        step: "health-check".to_string(),
        ready,
        detail,
        command: Some(format!("GET {ping_url}; GET {llm_health_url}")),
        checks,
    }
}
