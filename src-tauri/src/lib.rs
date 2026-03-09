mod commands;

use serde::Serialize;
use std::process::Command;

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

mod runtime_preflight {
    use super::{Command, RuntimePreflight};
    use std::collections::HashSet;
    use std::env;
    use std::fs;
    use std::io::ErrorKind;

    const NORMALIZED_DOCKER_PATH: &str = "/opt/homebrew/bin:/usr/local/bin:/Applications/Docker.app/Contents/Resources/bin:/usr/bin:/bin:/usr/sbin:/sbin";

    #[cfg(target_os = "macos")]
    const MACOS_DOCKER_CANDIDATES: [&str; 3] = [
        "/opt/homebrew/bin/docker",
        "/usr/local/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
    ];

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
                Self::UnexpectedCommandExecutionError => {
                    "unexpected-command-execution-error"
                }
            }
        }

        fn summary(self) -> &'static str {
            match self {
                Self::DockerBinaryNotFound => "Docker binary not found",
                Self::DockerCliInvocationFailed => "Docker CLI invocation failed",
                Self::DockerComposeUnavailable => "Docker Compose unavailable",
                Self::DockerDaemonUnreachable => "Docker daemon unreachable",
                Self::UnexpectedCommandExecutionError => {
                    "Unexpected command execution error"
                }
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

    fn join_lines(lines: Vec<String>) -> String {
        lines
            .into_iter()
            .filter(|line| !line.trim().is_empty())
            .collect::<Vec<_>>()
            .join("\n")
    }

    fn render_probe_output(stdout: &[u8], stderr: &[u8]) -> Vec<String> {
        let stdout = String::from_utf8_lossy(stdout).trim().to_string();
        let stderr = String::from_utf8_lossy(stderr).trim().to_string();

        let mut lines = Vec::new();
        if !stdout.is_empty() {
            lines.push(format!("stdout: {stdout}"));
        }
        if !stderr.is_empty() {
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
                        detail_lines.push(format!(
                            "candidate resolution error for {candidate}: {err}"
                        ));
                        candidate_failures
                            .push(FailureKind::UnexpectedCommandExecutionError);
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
                        detail_lines.extend(render_probe_output(
                            &output.stdout,
                            &output.stderr,
                        ));
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
                        detail_lines.extend(render_probe_output(
                            &output.stdout,
                            &output.stderr,
                        ));
                        candidate_failures
                            .push(FailureKind::DockerCliInvocationFailed);
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
                        candidate_failures
                            .push(FailureKind::UnexpectedCommandExecutionError);
                    }
                }
            }
        }

        let mut fallback = Command::new("docker");
        fallback.arg("--version").env("PATH", NORMALIZED_DOCKER_PATH);
        if let Ok(home) = env::var("HOME") {
            fallback.env("HOME", &home);
            fallback.env("DOCKER_CONFIG", format!("{home}/.docker"));
        }

        match fallback.output()
        {
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
                detail_lines.push(
                    "PATH fallback failed to find a usable `docker` executable.".to_string(),
                );
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

                let (compose_probe, daemon_probe, docker_compose_available, docker_daemon_reachable, failure_kind) =
                    if cli_probe.ok {
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
                        let failure_kind = compose_probe
                            .failure_kind
                            .or(daemon_probe.failure_kind)
                            .map(|kind| kind.as_str().to_string());
                        let compose_available = compose_probe.ok;
                        let daemon_reachable = daemon_probe.ok;
                        (
                            compose_probe,
                            daemon_probe,
                            compose_available,
                            daemon_reachable,
                            failure_kind,
                        )
                    } else {
                        let failure_kind = cli_probe
                            .failure_kind
                            .map(|kind| kind.as_str().to_string());
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
                let detail = build_preflight_detail(&[
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
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    tauri::Builder::default()
        .setup(|app| {
            if cfg!(debug_assertions) {
                app.handle().plugin(
                    tauri_plugin_log::Builder::default()
                        .level(log::LevelFilter::Info)
                        .build(),
                )?;
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::desktop_get_runtime_config,
            commands::desktop_get_api_key,
            commands::desktop_set_api_key,
            commands::desktop_clear_api_key,
            commands::desktop_open_external,
            runtime_preflight::desktop_runtime_preflight_check
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
