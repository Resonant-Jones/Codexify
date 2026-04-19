use std::fs;
use std::path::Path;

/// Copies a file or directory tree from src to dst.
fn copy_path(src: &Path, dst: &Path) -> std::io::Result<()> {
    if src.is_dir() {
        fs::create_dir_all(dst)?;
        for entry in fs::read_dir(src)? {
            let entry = entry?;
            let ty = entry.file_type()?;
            let dest_path = dst.join(entry.file_name());
            if ty.is_dir() {
                copy_path(&entry.path(), &dest_path)?;
            } else {
                fs::copy(entry.path(), dest_path)?;
            }
        }
    } else {
        if let Some(parent) = dst.parent() {
            fs::create_dir_all(parent)?;
        }
        fs::copy(src, dst)?;
    }
    Ok(())
}

fn main() {
    tauri_build::build();

    // Stage runtime assets under OUT_DIR so the Tauri bundler can pick them up.
    // bundle.resources in tauri.conf.json uses paths relative to src-tauri, but we
    // also stage here so custom copy logic can intervene if needed.
    let out_dir_var = std::env::var("OUT_DIR").unwrap();
    let out_dir = Path::new(&out_dir_var);
    let staging = out_dir.join("codexify_staging");
    let _ = fs::remove_dir_all(&staging);
    fs::create_dir_all(&staging).ok();

    // Repo root is one directory up from src-tauri (CARGO_MANIFEST_DIR = src-tauri/).
    let repo_root = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();

    // The packaged runtime assets required by the desktop shell launcher.
    // These are listed in commands.rs as PACKAGED_RUNTIME_REQUIRED_ASSETS and
    // PACKAGED_RUNTIME_PLACEHOLDER_DIRS.
    let runtime_assets = [
        "backend",
        "guardian",
        "docker",
        "plugins",
        "scripts",
        "requirements",
        "tests",
        ".env.example",
        ".env.template",
        "pytest.ini",
        "requirements.txt",
        "docker-compose.yml",
    ];

    for name in &runtime_assets {
        let src = repo_root.join(name);
        let dst = staging.join(name);
        if src.exists() {
            if let Err(e) = copy_path(&src, &dst) {
                eprintln!(
                    "warning: build.rs: failed to copy runtime asset {}: {}",
                    name, e
                );
            }
        }
    }

    // Create placeholder dirs (models, .chroma) if they don't exist in the repo.
    let placeholder_dirs = ["models/bge-large-en-v1.5", ".chroma"];
    for dir in placeholder_dirs {
        let dst = staging.join(dir);
        if !dst.exists() {
            fs::create_dir_all(&dst).ok();
        }
    }

    for asset in [
        "backend",
        "guardian",
        "docker",
        "plugins",
        "scripts",
        "requirements",
        "tests",
        ".env.example",
        ".env.template",
        "pytest.ini",
        "requirements.txt",
        "docker-compose.yml",
    ] {
        println!("cargo:rerun-if-changed={}", repo_root.join(asset).display());
    }
}
