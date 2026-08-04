fn main() {
    const COMMANDS: &[&str] = &[
        "candidate_get_state",
        "candidate_navigate",
        "candidate_back",
        "candidate_forward",
        "candidate_reload",
        "candidate_begin_capture",
        "candidate_return_capture",
        "candidate_get_preview",
        "candidate_attach",
        "candidate_cancel",
        "candidate_trigger_renderer_failure",
    ];

    let attributes = tauri_build::Attributes::new()
        .app_manifest(tauri_build::AppManifest::new().commands(COMMANDS));
    tauri_build::try_build(attributes).expect("failed to build proof-only Tauri candidate");
}
