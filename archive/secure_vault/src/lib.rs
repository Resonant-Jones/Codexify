/// Tauri plugin entry point for the `secure_vault` plugin.
/// Registers all commands that expose secure vault functionality to the frontend.
use tauri::plugin::{Builder, TauriPlugin};
use tauri::Runtime;

/// Re-export command functions for the plugin builder.
mod commands;
mod biometric;
mod linking;
mod vault;

/// Initialize the plugin. This function is called from the Tauri
/// `tauri.conf.json` `plugins` section.
pub fn init<R: Runtime>() -> TauriPlugin<R> {
    Builder::new("secure_vault")
        .invoke_handler(tauri::generate_handler![
            commands::get_vault_key,
            commands::encrypt_vault,
            commands::decrypt_vault,
            commands::biometric_auth,
            commands::link_device,
            commands::export_vault,
            commands::import_vault,
            commands::shred_vault,
        ])
        .build()
}
