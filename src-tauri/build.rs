use std::{
    collections::HashSet,
    env, fs,
    path::{Path, PathBuf},
};

const BUNDLE_RESOURCE_PATHS: &[&str] = &[
    ".env.example",
    ".env.template",
    "backend",
    "docker",
    "docker-compose.yml",
    "guardian",
    "plugins",
    "pytest.ini",
    "requirements",
    "requirements.txt",
    "scripts",
    "tests",
];

const STAGING_DIR: &str = "target/bundle-resources";

fn main() {
    if let Err(err) = stage_bundle_resources() {
        panic!("failed to stage bundle resources: {err}");
    }

    tauri_build::build()
}

fn stage_bundle_resources() -> Result<(), String> {
    let manifest_dir =
        PathBuf::from(env::var("CARGO_MANIFEST_DIR").map_err(|err| {
            format!("failed to read CARGO_MANIFEST_DIR for bundle staging: {err}")
        })?);
    let repo_root = manifest_dir.parent().ok_or_else(|| {
        format!(
            "failed to resolve the repository root from {}",
            manifest_dir.display()
        )
    })?;
    let staging_root = manifest_dir.join(STAGING_DIR);

    println!(
        "cargo:warning=staging Codexify bundle resources at {}",
        staging_root.display()
    );
    println!("cargo:rerun-if-changed=build.rs");

    if staging_root.exists() {
        fs::remove_dir_all(&staging_root).map_err(|err| {
            format!(
                "failed to clear existing bundle staging directory {}: {err}",
                staging_root.display()
            )
        })?;
    }
    fs::create_dir_all(&staging_root).map_err(|err| {
        format!(
            "failed to create bundle staging directory {}: {err}",
            staging_root.display()
        )
    })?;

    let mut visited_directories = HashSet::new();

    for relative_path in BUNDLE_RESOURCE_PATHS {
        let source_path = repo_root.join(relative_path);
        let destination_path = staging_root.join(relative_path);

        println!("cargo:rerun-if-changed={}", source_path.display());
        copy_resource_path(&source_path, &destination_path, &mut visited_directories)?;
    }

    Ok(())
}

fn copy_resource_path(
    source_path: &Path,
    destination_path: &Path,
    visited_directories: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    match bundle_source_metadata(source_path, "bundle symlink")? {
        Some(metadata) if metadata.is_dir() => {
            copy_directory(source_path, destination_path, visited_directories)
        }
        Some(_) => copy_file(source_path, destination_path),
        None => Ok(()),
    }
}

fn copy_directory(
    source_path: &Path,
    destination_path: &Path,
    visited_directories: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    let canonical_source = fs::canonicalize(source_path).map_err(|err| {
        format!(
            "failed to resolve bundle directory {}: {err}",
            source_path.display()
        )
    })?;

    if !visited_directories.insert(canonical_source.clone()) {
        println!(
            "cargo:warning=skipping already-visited bundle directory {} -> {}",
            source_path.display(),
            canonical_source.display()
        );
        return Ok(());
    }

    fs::create_dir_all(destination_path).map_err(|err| {
        format!(
            "failed to create bundle directory {}: {err}",
            destination_path.display()
        )
    })?;

    for entry in fs::read_dir(source_path).map_err(|err| {
        format!(
            "failed to read bundle directory {}: {err}",
            source_path.display()
        )
    })? {
        let entry = entry.map_err(|err| {
            format!(
                "failed to inspect bundle directory entry under {}: {err}",
                source_path.display()
            )
        })?;
        let entry_source = entry.path();
        let entry_destination = destination_path.join(entry.file_name());
        copy_resource_entry(&entry_source, &entry_destination, visited_directories)?;
    }

    Ok(())
}

fn copy_resource_entry(
    source_path: &Path,
    destination_path: &Path,
    visited_directories: &mut HashSet<PathBuf>,
) -> Result<(), String> {
    match bundle_source_metadata(source_path, "nested bundle symlink")? {
        Some(metadata) if metadata.is_dir() => {
            copy_directory(source_path, destination_path, visited_directories)
        }
        Some(_) => copy_file(source_path, destination_path),
        None => Ok(()),
    }
}

fn copy_file(source_path: &Path, destination_path: &Path) -> Result<(), String> {
    if let Some(parent) = destination_path.parent() {
        fs::create_dir_all(parent).map_err(|err| {
            format!(
                "failed to create bundle parent directory {}: {err}",
                parent.display()
            )
        })?;
    }

    fs::copy(source_path, destination_path).map_err(|err| {
        format!(
            "failed to copy bundle file {} -> {}: {err}",
            source_path.display(),
            destination_path.display()
        )
    })?;

    Ok(())
}

fn bundle_source_metadata(
    source_path: &Path,
    symlink_label: &str,
) -> Result<Option<fs::Metadata>, String> {
    let link_metadata = fs::symlink_metadata(source_path).map_err(|err| {
        format!(
            "bundle resource path {} does not exist: {err}",
            source_path.display()
        )
    })?;

    if link_metadata.file_type().is_symlink() {
        let link_target = fs::read_link(source_path).unwrap_or_default();
        let target_metadata = match fs::metadata(source_path) {
            Ok(metadata) => metadata,
            Err(err) => {
                println!(
                    "cargo:warning=skipping broken {} {} -> {} ({err})",
                    symlink_label,
                    source_path.display(),
                    link_target.display()
                );
                return Ok(None);
            }
        };

        return Ok(Some(target_metadata));
    }

    fs::metadata(source_path).map(Some).map_err(|err| {
        format!(
            "bundle resource path {} does not exist: {err}",
            source_path.display()
        )
    })
}
