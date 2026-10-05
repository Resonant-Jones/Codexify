mod bootstrap_readiness_generated;
mod commands;
mod qualification;

use tauri::Manager;

fn initialize_bootstrap_runtime(handle: &tauri::AppHandle) -> commands::BootstrapRuntime {
    let bootstrap_runtime = commands::resolve_bootstrap_runtime(handle);
    commands::prime_packaged_runtime_environment(&bootstrap_runtime);
    bootstrap_runtime
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    qualification::initialize().expect("qualification isolation could not be established");
    let mut context = tauri::generate_context!();
    let mut qualification_windows = Vec::new();
    if let Some(q) = qualification::active() {
        context.config_mut().identifier = q.keychain_service();
        for window in &mut context.config_mut().app.windows {
            if window.create {
                qualification_windows.push(window.clone());
                window.create = false;
            }
        }
    }
    tauri::Builder::default()
        .setup(move |app| {
            let mut logger = tauri_plugin_log::Builder::default().level(log::LevelFilter::Info);
            if let Some(q) = qualification::active() {
                let data = q.data_root(&app.path().data_dir()?);
                let root = q.runtime_root(&app.path().home_dir()?);
                qualification::reject_symlinks(&root)?;
                qualification::bind_runtime_root(root)?;
                qualification::reject_symlinks(&data)?;
                let path = data.join("logs");
                qualification::reject_symlinks(&path)?;
                std::fs::create_dir_all(&data)?;
                let receipt = data.join("qualification.json");
                qualification::reject_symlinks(&receipt)?;
                std::fs::write(
                    receipt,
                    serde_json::to_vec_pretty(&serde_json::json!({
                        "qualificationId": q.id, "composeProject": q.project,
                        "webKitDataStore": q.store, "ports": q.ports,
                        "runtimeRoot": q.runtime_root(&app.path().home_dir()?),
                        "dataRoot": data, "keychainService": q.keychain_service()
                    }))?,
                )?;
                logger = logger.targets([tauri_plugin_log::Target::new(
                    tauri_plugin_log::TargetKind::Folder {
                        path,
                        file_name: Some("desktop".into()),
                    },
                )]);
            }
            app.handle().plugin(logger.build())?;
            let handle = app.handle().clone();
            let bootstrap_runtime = initialize_bootstrap_runtime(&handle);
            if qualification::active().is_some() {
                if let Some(failure) = bootstrap_runtime.qualification_failure() {
                    return Err(failure.to_string().into());
                }
            }
            commands::prime_packaged_launcher_startup_state(&bootstrap_runtime);
            app.manage(bootstrap_runtime);
            if let Some(q) = qualification::active() {
                for config in &qualification_windows {
                    #[cfg(target_os = "macos")]
                    tauri::WebviewWindowBuilder::from_config(app, config)?
                        .data_store_identifier(q.store)
                        .build()?;
                }
            }
            Ok(())
        })
        .invoke_handler(tauri::generate_handler![
            commands::desktop_get_runtime_config,
            commands::desktop_get_runtime_auth_config,
            commands::desktop_get_launcher_startup_handoff,
            commands::desktop_fetch_media,
            commands::desktop_get_api_key,
            commands::desktop_set_api_key,
            commands::desktop_clear_api_key,
            commands::desktop_open_external,
            commands::desktop_open_webui,
            commands::desktop_open_docker_desktop,
            commands::desktop_runtime_preflight_check,
            commands::desktop_run_setup_cli,
            commands::desktop_pull_registry_runtime_images,
            commands::desktop_compose_up,
            commands::desktop_get_bootstrap_logs,
            commands::desktop_restart_runtime_services,
            commands::desktop_runtime_readiness_check,
            commands::desktop_runtime_health_check
        ])
        .run(context)
        .expect("error while running tauri application");
}
