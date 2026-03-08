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
}

mod runtime_preflight {
    use super::{Command, RuntimePreflight};

    #[derive(Debug)]
    struct CommandProbe {
        ok: bool,
        detail: String,
    }

    fn render_probe_output(stdout: &[u8], stderr: &[u8]) -> String {
        let stdout = String::from_utf8_lossy(stdout).trim().to_string();
        let stderr = String::from_utf8_lossy(stderr).trim().to_string();

        match (stdout.is_empty(), stderr.is_empty()) {
            (false, false) => format!("{stdout}\n{stderr}"),
            (false, true) => stdout,
            (true, false) => stderr,
            (true, true) => String::new(),
        }
    }

    fn run_probe(program: &str, args: &[&str], label: &str) -> CommandProbe {
        match Command::new(program).args(args).output() {
            Ok(output) => {
                let message = render_probe_output(&output.stdout, &output.stderr);
                if output.status.success() {
                    let detail = if message.is_empty() {
                        format!("{label}: ok")
                    } else {
                        format!("{label}: {message}")
                    };
                    CommandProbe { ok: true, detail }
                } else {
                    let detail = if message.is_empty() {
                        format!("{label}: exited with status {}", output.status)
                    } else {
                        format!("{label}: {message}")
                    };
                    CommandProbe { ok: false, detail }
                }
            }
            Err(err) => CommandProbe {
                ok: false,
                detail: format!("{label}: failed to execute ({err})"),
            },
        }
    }

    fn build_preflight_detail(probes: &[CommandProbe]) -> Option<String> {
        let detail = probes
            .iter()
            .map(|probe| probe.detail.trim())
            .filter(|detail| !detail.is_empty())
            .collect::<Vec<_>>()
            .join("\n");

        if detail.trim().is_empty() {
            None
        } else {
            Some(detail)
        }
    }

    #[tauri::command]
    pub fn desktop_runtime_preflight_check() -> RuntimePreflight {
        let cli_probe = run_probe("docker", &["--version"], "docker --version");
        let compose_probe = if cli_probe.ok {
            run_probe("docker", &["compose", "version"], "docker compose version")
        } else {
            CommandProbe {
                ok: false,
                detail:
                    "docker compose version: skipped because Docker CLI is unavailable"
                        .to_string(),
            }
        };
        let daemon_probe = if cli_probe.ok {
            run_probe(
                "docker",
                &["info", "--format", "{{json .ServerVersion}}"],
                "docker info --format {{json .ServerVersion}}",
            )
        } else {
            CommandProbe {
                ok: false,
                detail: "docker info: skipped because Docker CLI is unavailable".to_string(),
            }
        };

        let docker_cli_installed = cli_probe.ok;
        let docker_compose_available = compose_probe.ok;
        let docker_daemon_reachable = daemon_probe.ok;
        let ready =
            docker_cli_installed && docker_compose_available && docker_daemon_reachable;
        let detail = build_preflight_detail(&[cli_probe, compose_probe, daemon_probe]);

        RuntimePreflight {
            docker_cli_installed,
            docker_compose_available,
            docker_daemon_reachable,
            ready,
            detail,
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
