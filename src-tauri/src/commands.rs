use serde::Serialize;
use std::process::Command;

const DESKTOP_KEYCHAIN_SERVICE: &str = "com.codexify.desktop";
const DESKTOP_KEYCHAIN_ACCOUNT: &str = "guardian_api_key";

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

fn env_first(keys: &[&str], fallback: &str) -> String {
    for key in keys {
        if let Ok(value) = std::env::var(key) {
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
        // Default to web share surface, not tauri:// origins.
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
