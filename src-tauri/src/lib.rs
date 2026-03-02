mod commands;

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
            commands::desktop_open_external
        ])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}
