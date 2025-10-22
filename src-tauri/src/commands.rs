use std::path::PathBuf;
use std::process::Command;

#[tauri::command]
pub fn vault_encrypt_and_store(label: String, secret: String) -> Result<(), String> {
    let python_cmd = std::env::var("PYTHON").unwrap_or_else(|_| {
        if cfg!(target_os = "windows") {
            "python".to_string()
        } else {
            "python3".to_string()
        }
    });

    let manifest_dir = std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| "".to_string());
    let mut project_root = PathBuf::from(manifest_dir);
    if project_root
        .file_name()
        .map(|name| name == "src-tauri")
        .unwrap_or(false)
    {
        project_root.pop();
    }

    let py_snippet = format!(
        "from guardian.desktop_vault import CodexifyDesktopVault; CodexifyDesktopVault().encrypt_and_store({label:?}, {secret:?})"
    );

    let output = Command::new(&python_cmd)
        .arg("-c")
        .arg(&py_snippet)
        .current_dir(&project_root)
        .output()
        .map_err(|err| format!("Failed to invoke Python interpreter: {err}"))?;

    if output.status.success() {
        Ok(())
    } else {
        let stderr = String::from_utf8_lossy(&output.stderr);
        Err(format!("Python script failed: {stderr}"))
    }
}
