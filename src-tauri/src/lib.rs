mod commands;

use tauri::Manager;

fn initialize_bootstrap_runtime(handle: &tauri::AppHandle) -> commands::BootstrapRuntime {
    let bootstrap_runtime = commands::resolve_bootstrap_runtime(handle);
    commands::prime_packaged_runtime_environment(&bootstrap_runtime);
    bootstrap_runtime
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
            let handle = app.handle().clone();
            let bootstrap_runtime = initialize_bootstrap_runtime(&handle);
            app.manage(bootstrap_runtime);
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::desktop_get_runtime_config,
            commands::desktop_get_launcher_startup_handoff,
            commands::desktop_fetch_media,
            commands::desktop_get_api_key,
            commands::desktop_set_api_key,
            commands::desktop_clear_api_key,
            commands::desktop_open_external,
            commands::desktop_open_docker_desktop,
            commands::desktop_runtime_preflight_check,
            commands::desktop_run_setup_cli,
            commands::desktop_compose_up,
            commands::desktop_get_bootstrap_logs,
            commands::desktop_restart_runtime_services,
            commands::desktop_runtime_readiness_check,
            commands::desktop_runtime_health_check
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
