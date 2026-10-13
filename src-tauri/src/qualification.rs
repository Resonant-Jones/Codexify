//! Opt-in, packaged macOS proof namespace. No normal-launch defaults live here.
use sha2::{Digest, Sha256};
use std::{
    collections::BTreeMap,
    env,
    net::TcpListener,
    path::{Path, PathBuf},
    process::Command,
    sync::OnceLock,
};

pub const CONTROL: &str = "CODEXIFY_DESKTOP_QUALIFICATION_ID";
static ACTIVE: OnceLock<Option<Qualification>> = OnceLock::new();
static RUNTIME_ROOT: OnceLock<PathBuf> = OnceLock::new();
pub fn bind_runtime_root(path: PathBuf) -> Result<(), String> {
    RUNTIME_ROOT
        .set(path)
        .map_err(|_| "Qualification runtime root already bound".into())
}
pub fn runtime_env_path() -> Option<PathBuf> {
    RUNTIME_ROOT.get().map(|root| root.join(".env"))
}

#[derive(Debug, Clone)]
pub struct Qualification {
    pub id: String,
    pub project: String,
    pub store: [u8; 16],
    pub ports: [u16; 6],
}

impl Qualification {
    pub fn new(id: &str) -> Result<Self, String> {
        if id.is_empty()
            || id.len() > 48
            || !id
                .bytes()
                .all(|c| c.is_ascii_lowercase() || c.is_ascii_digit() || c == b'-')
            || !id.as_bytes()[0].is_ascii_alphanumeric()
            || !id.as_bytes()[id.len() - 1].is_ascii_alphanumeric()
        {
            return Err(format!("{CONTROL} must be 1-48 lowercase letters, digits or hyphens, beginning and ending with a letter or digit"));
        }
        let digest = Sha256::digest(format!("codexify-desktop-qualification-v1:{id}"));
        let mut store = [0; 16];
        store.copy_from_slice(&digest[..16]);
        store[6] = (store[6] & 0x0f) | 0x50;
        store[8] = (store[8] & 0x3f) | 0x80;
        let base = 20000 + (u16::from_be_bytes([digest[16], digest[17]]) % 3000) * 10;
        Ok(Self {
            id: id.into(),
            project: format!("codexify-qualification-{id}"),
            store,
            ports: std::array::from_fn(|i| base + i as u16),
        })
    }
    pub fn runtime_root(&self, home: &Path) -> PathBuf {
        home.join("CodexifyQualifications")
            .join(&self.id)
            .join("runtime")
    }
    pub fn data_root(&self, support: &Path) -> PathBuf {
        support.join("CodexifyQualifications").join(&self.id)
    }
    pub fn keychain_service(&self) -> String {
        format!("com.codexify.desktop.qualification.{}", self.id)
    }
    pub fn environment(&self) -> BTreeMap<String, String> {
        let mut result = BTreeMap::new();
        result.insert("COMPOSE_PROJECT_NAME".into(), self.project.clone());
        for (key, port) in [
            "CODEXIFY_BACKEND_PORT",
            "CODEXIFY_FRONTEND_PORT",
            "CODEXIFY_POSTGRES_PORT",
            "CODEXIFY_NEO4J_HTTP_PORT",
            "CODEXIFY_NEO4J_BOLT_PORT",
        ]
        .iter()
        .zip(self.ports)
        {
            result.insert((*key).into(), port.to_string());
        }
        let backend = format!("http://127.0.0.1:{}", self.ports[0]);
        let frontend = format!("http://127.0.0.1:{}", self.ports[1]);
        for key in [
            "CODEXIFY_DESKTOP_BACKEND_URL",
            "VITE_GUARDIAN_API_BASE",
            "GUARDIAN_API_BASE",
        ] {
            result.insert(key.into(), backend.clone());
        }
        for key in ["CODEXIFY_DESKTOP_API_BASE_URL", "VITE_API_BASE_URL"] {
            result.insert(key.into(), format!("{backend}/api"));
        }
        for key in [
            "CODEXIFY_DESKTOP_SHARE_BASE_URL",
            "VITE_SHARE_PUBLIC_BASE_URL",
        ] {
            result.insert(key.into(), frontend.clone());
        }
        result.insert(
            "GUARDIAN_ALLOWED_ORIGINS".into(),
            format!("{frontend},tauri://localhost,http://tauri.localhost,https://tauri.localhost"),
        );
        result
    }
    pub fn setup_values(
        &self,
        values: &mut BTreeMap<String, String>,
        fresh: bool,
    ) -> Result<(), String> {
        if values.get(CONTROL).is_some_and(|id| id != &self.id) {
            return Err("Configuration belongs to another qualification identity; no configuration was changed".into());
        }
        values.insert(CONTROL.into(), self.id.clone());
        values.extend(self.environment());
        if fresh {
            // Never discover an unrelated provider at a coincidentally occupied derived port.
            let _guard = TcpListener::bind(("127.0.0.1", self.ports[5])).map_err(|_| {
                "Initial qualification inference port is occupied; choose another qualification ID"
            })?;
            values.extend(self.initial_inference());
        }
        Ok(())
    }
    pub fn initial_inference(&self) -> BTreeMap<String, String> {
        let base = format!("http://host.docker.internal:{}", self.ports[5]);
        [
            ("LOCAL_BASE_URL", format!("{base}/v1")),
            ("LOCAL_DOCKER_FALLBACK_BASE_URL", format!("{base}/v1")),
            ("VAULTNODE_BASE_URL", base.clone()),
            ("CODEXIFY_LOCAL_VOICE_BASE_URL", base),
        ]
        .into_iter()
        .map(|(k, v)| (k.into(), v))
        .collect()
    }
    // A hash collision or unrelated listener must stop launch, including readiness probes.
    // Existing containers belonging to this exact project may retain ports on relaunch.
    fn docker_command(&self, docker: &str) -> Command {
        let mut command = Command::new(docker);
        command.env_clear();
        command.env(
            "PATH",
            "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin",
        );
        for key in ["HOME", "DOCKER_CONFIG"] {
            if let Some(value) = env::var_os(key) {
                command.env(key, value);
            }
        }
        command
    }
    pub fn validate_ports(&self) -> Result<(), String> {
        let occupied: Vec<_> = self.ports[..5]
            .iter()
            .filter(|p| TcpListener::bind(("127.0.0.1", **p)).is_err())
            .copied()
            .collect();
        if occupied.is_empty() {
            return Ok(());
        }
        let docker = [
            "/opt/homebrew/bin/docker",
            "/usr/local/bin/docker",
            "/Applications/Docker.app/Contents/Resources/bin/docker",
        ]
        .into_iter()
        .find(|p| Path::new(p).is_file())
        .ok_or("Cannot establish ownership of occupied qualification ports")?;
        let output = self
            .docker_command(docker)
            .args([
                "ps",
                "--filter",
                &format!("label=com.docker.compose.project={}", self.project),
                "--format",
                "{{.ID}}",
            ])
            .output()
            .map_err(|e| e.to_string())?;
        if !output.status.success() {
            return Err(
                "Docker ownership inventory unavailable for occupied qualification ports".into(),
            );
        }
        let ids = String::from_utf8_lossy(&output.stdout);
        let ids: Vec<_> = ids.split_whitespace().collect();
        if ids.is_empty() {
            return Err(format!(
                "Qualification ports {occupied:?} are already in use by another runtime"
            ));
        }
        let output = self
            .docker_command(docker)
            .arg("inspect")
            .args(ids)
            .output()
            .map_err(|e| e.to_string())?;
        if !output.status.success() {
            return Err("Cannot inspect qualification port ownership".into());
        }
        let rows: serde_json::Value =
            serde_json::from_slice(&output.stdout).map_err(|e| e.to_string())?;
        let mut owned = Vec::new();
        for row in rows.as_array().ok_or("Invalid Docker inventory")? {
            if let Some(ports) = row["NetworkSettings"]["Ports"].as_object() {
                for bindings in ports.values().filter_map(|v| v.as_array()) {
                    for binding in bindings {
                        if binding["HostIp"].as_str() == Some("127.0.0.1") {
                            if let Some(port) = binding["HostPort"]
                                .as_str()
                                .and_then(|v| v.parse::<u16>().ok())
                            {
                                owned.push(port);
                            }
                        }
                    }
                }
            }
        }
        if occupied.iter().all(|p| owned.contains(p)) {
            Ok(())
        } else {
            Err(format!(
                "Qualification ports {occupied:?} are not exclusively owned by {}",
                self.project
            ))
        }
    }
}

pub fn active() -> Option<&'static Qualification> {
    ACTIVE.get().and_then(Option::as_ref)
}
pub fn initialize() -> Result<(), String> {
    let value = match env::var_os(CONTROL) {
        None => None,
        Some(id) => {
            let q = Qualification::new(id.to_str().ok_or("Qualification ID is not UTF-8")?)?;
            #[cfg(target_os = "macos")]
            {
                let exe = env::current_exe().map_err(|e| e.to_string())?;
                if !exe
                    .ancestors()
                    .any(|p| p.extension().is_some_and(|e| e == "app"))
                {
                    return Err("Qualification mode requires a packaged .app".into());
                }
                let version = Command::new("/usr/bin/sw_vers")
                    .arg("-productVersion")
                    .output()
                    .map_err(|e| e.to_string())?;
                let major = String::from_utf8_lossy(&version.stdout)
                    .split('.')
                    .next()
                    .and_then(|v| v.trim().parse::<u32>().ok())
                    .unwrap_or(0);
                if !version.status.success() || major < 14 {
                    return Err("Qualification mode requires macOS 14+ for a distinct persistent WebKit datastore".into());
                }
                q.validate_ports()?;
            }
            #[cfg(not(target_os = "macos"))]
            {
                return Err("Packaged qualification mode is currently macOS only".into());
            }
            Some(q)
        }
    };
    ACTIVE
        .set(value)
        .map_err(|_| "Qualification namespace already initialized".into())
}

pub fn reject_symlinks(path: &Path) -> Result<(), String> {
    for component in path.ancestors() {
        if std::fs::symlink_metadata(component).is_ok_and(|m| m.file_type().is_symlink()) {
            return Err(format!(
                "Qualification path cannot traverse a symlink: {}",
                component.display()
            ));
        }
    }
    Ok(())
}

#[cfg(test)]
mod tests {
    use super::*;
    #[test]
    fn identity_is_strict_and_stable() {
        for id in [
            "",
            "../normal",
            "Normal",
            "-bad",
            "bad-",
            "a/b",
            "with space",
        ] {
            assert!(Qualification::new(id).is_err());
        }
        assert!(Qualification::new(&"a".repeat(49)).is_err());
        let a = Qualification::new("proof-1").unwrap();
        let again = Qualification::new("proof-1").unwrap();
        let b = Qualification::new("proof-2").unwrap();
        assert_eq!(a.store, again.store);
        assert_eq!(a.ports, again.ports);
        assert_ne!(a.store, b.store);
        assert_ne!(a.project, b.project);
        assert_eq!(a.environment()["COMPOSE_PROJECT_NAME"], a.project);
        assert!(!a
            .ports
            .iter()
            .any(|p| [8888, 3000, 5433, 7474, 7687, 8000].contains(p)));
        assert_ne!(
            a.runtime_root(Path::new("/Users/operator")),
            Path::new("/Users/operator/Codexify")
        );
        assert_ne!(
            a.data_root(Path::new("/support")),
            Path::new("/support/Codexify")
        );
        assert_ne!(a.keychain_service(), "com.codexify.desktop");
    }
    #[test]
    fn symlink_paths_are_rejected() {
        #[cfg(unix)]
        {
            let root =
                std::env::temp_dir().join(format!("qualification-symlink-{}", std::process::id()));
            std::fs::create_dir_all(&root).unwrap();
            let link = root.join("alias");
            std::os::unix::fs::symlink("/", &link).unwrap();
            assert!(reject_symlinks(&link.join("state")).is_err());
            std::fs::remove_dir_all(root).unwrap();
        }
    }
    #[test]
    fn setup_forces_namespace_and_preserves_later_inference() {
        let q = Qualification::new("setup-proof").unwrap();
        let mut values = BTreeMap::from([
            ("COMPOSE_PROJECT_NAME".into(), "codexify".into()),
            ("CODEXIFY_BACKEND_PORT".into(), "8888".into()),
            ("LOCAL_BASE_URL".into(), "http://ordinary:8000/v1".into()),
            ("GUARDIAN_API_KEY".into(), "isolated-secret".into()),
        ]);
        q.setup_values(&mut values, true).unwrap();
        assert_eq!(values["COMPOSE_PROJECT_NAME"], q.project);
        assert_eq!(
            values["LOCAL_BASE_URL"],
            q.initial_inference()["LOCAL_BASE_URL"]
        );
        assert_eq!(values["GUARDIAN_API_KEY"], "isolated-secret");
        values.insert(
            "LOCAL_BASE_URL".into(),
            "http://chosen-isolated-provider/v1".into(),
        );
        q.setup_values(&mut values, false).unwrap();
        assert_eq!(
            values["LOCAL_BASE_URL"],
            "http://chosen-isolated-provider/v1"
        );
        values.insert(CONTROL.into(), "different-id".into());
        let before = values.clone();
        assert!(q.setup_values(&mut values, false).is_err());
        assert_eq!(values, before);
    }
    #[test]
    fn fresh_inference_collision_fails_closed() {
        let q = Qualification::new("occupied-proof").unwrap();
        let _listener = TcpListener::bind(("127.0.0.1", q.ports[5])).unwrap();
        assert!(q.setup_values(&mut BTreeMap::new(), true).is_err());
    }
    #[test]
    fn absent_control_has_no_namespace() {
        assert!(active().is_none());
    }
}
