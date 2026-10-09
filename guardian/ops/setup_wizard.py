from __future__ import annotations

import json
import os
import platform
import re
import secrets
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Mapping

from guardian.core.local_runtime_presets import (
    default_local_runtime_preset_id,
    local_runtime_env_defaults,
    normalize_local_runtime_preset,
)


@dataclass(frozen=True)
class DepStatus:
    name: str
    is_present: bool
    found_path: str | None
    help_text: str
    resolution_source: str | None = None


MACOS_FALLBACK_BINARIES: dict[str, tuple[str, ...]] = {
    "docker": (
        "/opt/homebrew/bin/docker",
        "/usr/local/bin/docker",
        "/Applications/Docker.app/Contents/Resources/bin/docker",
    ),
    "ollama": (
        "/opt/homebrew/bin/ollama",
        "/usr/local/bin/ollama",
        "/Applications/Ollama.app/Contents/Resources/ollama",
    ),
}

REQUIRED_CORE_CONFIG_KEYS = (
    "GUARDIAN_API_KEY",
    "NEO4J_USER",
    "NEO4J_PASS",
)

REQUIRED_INFERENCE_CONFIG_KEYS = (
    "LLM_PROVIDER",
    "LOCAL_BASE_URL",
    "LOCAL_CHAT_MODEL",
)

LOCAL_BETA_DEFAULTS = {
    "LLM_PROVIDER": "local",
    "CODEXIFY_LOCAL_ONLY_MODE": "true",
    "ALLOW_CLOUD_PROVIDERS": "false",
    "NEO4J_USER": "neo4j",
}

SECRET_CONFIG_KEYS = {
    "GUARDIAN_API_KEY",
    "VITE_GUARDIAN_API_KEY",
    "NEO4J_PASS",
    "OPENAI_API_KEY",
    "GROQ_API_KEY",
    "MINIMAX_API_KEY",
    "NOTION_API_KEY",
    "GITHUB_TOKEN",
}

PLACEHOLDER_VALUES = {
    "",
    "change-me",
    "changeme",
    "replace-me",
    "replace-with-real-key",
    "replace-with-neo4j-password",
    "dev-local-only-change-me",
    "example",
    "example-key",
    "placeholder",
    "todo",
}


from guardian.ops.bootstrap_readiness_generated import (
    BootstrapHumanAction,
    BootstrapReadiness,
    BootstrapWorkflow,
    SetupReadinessState,
)


@dataclass(frozen=True)
class SetupReadinessSummary:
    state: SetupReadinessState
    explanation: str
    recommended_action: str
    details: str = ""
    bootstrap: BootstrapReadiness | None = None


def _os_hint_lines(dep: str) -> str:
    system_name = platform.system().lower()
    if dep == "docker":
        if "darwin" in system_name:
            return (
                "Install Docker Desktop: "
                "https://www.docker.com/products/docker-desktop/"
            )
        if "windows" in system_name:
            return (
                "Install Docker Desktop (WSL2 recommended): "
                "https://www.docker.com/products/docker-desktop/"
            )
        return "Install Docker Engine: https://docs.docker.com/engine/install/"
    if dep == "ollama":
        return "Install Ollama: https://ollama.com/download"
    return ""


def _resolve_custom_binary_path(custom_path: str | None) -> str | None:
    if not custom_path:
        return None

    candidate = Path(custom_path).expanduser()
    if not candidate.is_absolute():
        candidate = (Path.cwd() / candidate).resolve()
    else:
        candidate = candidate.resolve()

    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def _macos_fallback_binary_paths(binary_name: str) -> tuple[Path, ...]:
    if platform.system().lower() != "darwin":
        return ()

    return tuple(Path(path) for path in MACOS_FALLBACK_BINARIES.get(binary_name, ()))


def _resolve_macos_fallback_binary_path(binary_name: str) -> str | None:
    for candidate in _macos_fallback_binary_paths(binary_name):
        if candidate.is_file() and os.access(candidate, os.X_OK):
            return str(candidate.resolve())
    return None


def _dependency_help_text(
    binary_name: str,
    *,
    custom_path: str | None,
    custom_resolved: bool,
    resolution_source: str | None,
    found_path: str | None,
) -> str:
    if found_path and resolution_source:
        prefix = ""
        if custom_path and not custom_resolved:
            prefix = f"Custom path is not executable: {custom_path}. "
        return f"{prefix}Resolved via {resolution_source}: {found_path}"

    if custom_path:
        custom_note = f"Custom path is not executable: {custom_path}."
        return (
            f"{custom_note} Not found via PATH or macOS fallback probe. "
            f"{_os_hint_lines(binary_name)}"
        )

    return (
        "Not found via PATH or macOS fallback probe. " f"{_os_hint_lines(binary_name)}"
    )


def detect_dependency(
    binary_name: str,
    display_name: str,
    custom_path: str | None = None,
) -> DepStatus:
    custom_resolved = _resolve_custom_binary_path(custom_path)
    resolution_source: str | None = None
    found: str | None = None

    if custom_resolved is not None:
        found = custom_resolved
        resolution_source = "custom path"
    else:
        path_resolved = shutil.which(binary_name)
        if path_resolved:
            found = path_resolved
            resolution_source = "PATH"
        else:
            fallback_resolved = _resolve_macos_fallback_binary_path(binary_name)
            if fallback_resolved:
                found = fallback_resolved
                resolution_source = "macOS fallback"

    help_text = _dependency_help_text(
        binary_name,
        custom_path=custom_path,
        custom_resolved=custom_resolved is not None,
        resolution_source=resolution_source,
        found_path=found,
    )

    return DepStatus(
        name=display_name,
        is_present=found is not None,
        found_path=found,
        help_text=help_text,
        resolution_source=resolution_source,
    )


def detect_core_dependencies(
    custom_paths: dict[str, str] | None = None,
) -> dict[str, DepStatus]:
    """
    Core deps for a local-first default experience.
    - docker: optional depending on how you run services, but common for DB/redis.
    - ollama: optional unless you want local LLM on first run.
    """

    paths = custom_paths or {}
    return {
        "docker": detect_dependency(
            "docker", "Docker", custom_path=paths.get("docker")
        ),
        "ollama": detect_dependency(
            "ollama", "Ollama", custom_path=paths.get("ollama")
        ),
    }


def env_kv_sanitize(value: str) -> str:
    # Minimal dotenv sanitization; this output is not intended for shell sourcing.
    if any(ch in value for ch in (" ", "#", ";", "'", '"')):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def write_env_file(
    env_path: Path,
    kv: dict[str, str],
    *,
    create_backup: bool = True,
    repo_root: Path | None = None,
) -> None:
    env_path = env_path.expanduser().resolve()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    original = env_path.read_text(encoding="utf-8") if env_path.exists() else ""
    existing = read_env_file(env_path) if env_path.exists() else {}
    template_root = (repo_root or env_path.parent).expanduser().resolve()
    template_path = template_root / ".env.template"
    template = read_env_file(template_path) if template_path.exists() else {}
    merged = {
        **template,
        **existing,
        **{k: str(v) for k, v in kv.items() if v is not None},
    }
    # A template is an example, never authority to enable cloud policy on a new install.
    for key, default in LOCAL_BETA_DEFAULTS.items():
        if key not in existing and key not in kv:
            merged[key] = default
    normalizer = normalize_local_beta_config_values(merged)
    if normalizer.conflict_keys:
        raise ValueError(
            "Existing configuration requires a user decision: "
            + ", ".join(normalizer.conflict_keys)
        )
    merged = normalizer.values
    key = _choose_guardian_api_key(
        existing_env_value=existing.get("GUARDIAN_API_KEY", ""),
        seed_value=template.get("GUARDIAN_API_KEY", ""),
        kv_value=merged.get("GUARDIAN_API_KEY", ""),
    )
    merged["GUARDIAN_API_KEY"] = key
    mirror = merged.get("VITE_GUARDIAN_API_KEY")
    if not is_placeholder_config_value(mirror) and mirror != key:
        raise ValueError(
            "Existing frontend API key differs; preserve it and resolve the conflict before setup."
        )
    merged["VITE_GUARDIAN_API_KEY"] = key
    lines = []
    written = set()
    for line in original.splitlines():
        match = re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z_0-9]*)\s*=", line)
        if not match:
            lines.append(line)
            continue
        name = match[1]
        written.add(name)
        if existing.get(name) == merged.get(name):
            lines.append(line)
        else:
            lines.append(f"{name}={env_kv_sanitize(merged[name])}")
    for name, value in merged.items():
        if name not in written:
            lines.append(f"{name}={env_kv_sanitize(value)}")
    content = "\n".join(lines) + "\n"
    if content == original:
        return
    if original and create_backup:
        backup = env_path.with_suffix(env_path.suffix + ".bak")
        backup.write_text(original, encoding="utf-8")
        backup.chmod(0o600)
    temporary = env_path.with_suffix(env_path.suffix + ".setup.tmp")
    temporary.write_text(content, encoding="utf-8")
    temporary.chmod(0o600)
    os.replace(temporary, env_path)


def default_env_target(repo_root: Path) -> Path:
    """
    Prefer .env.local if you want to keep developer overrides separate.
    If your repo already uses .env, switch to that for consistency.
    """

    return repo_root / ".env"


def read_env_file(env_path: Path) -> dict[str, str]:
    """
    Minimal .env parser:
    - supports KEY=VALUE
    - ignores blank lines and comments (# ...)
    - strips surrounding quotes
    """
    resolved = env_path.expanduser().resolve()
    if not resolved.exists():
        return {}

    output: dict[str, str] = {}
    for raw in resolved.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        output[key] = value
    return output


def _parse_env_line(raw: str) -> tuple[str, str] | None:
    line = raw.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None

    key, value = line.split("=", 1)
    key = key.strip()
    value = value.strip()
    if len(value) >= 2 and (
        (value[0] == value[-1] == '"') or (value[0] == value[-1] == "'")
    ):
        value = value[1:-1]
    return key, value


def _read_env_with_order(env_path: Path) -> tuple[list[str], dict[str, str]]:
    order: list[str] = []
    values: dict[str, str] = {}
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        parsed = _parse_env_line(raw)
        if parsed is None:
            continue
        key, value = parsed
        order.append(key)
        values[key] = value
    return order, values


def _is_placeholder_guardian_api_key(value: str) -> bool:
    lowered = value.strip().lower()
    if not lowered:
        return True
    return lowered in {
        "dev-local-only-change-me",
        "change-me",
        "changeme",
        "replace-me",
        "replace-with-real-key",
        "example",
        "example-key",
    }


def is_placeholder_config_value(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if normalized in PLACEHOLDER_VALUES:
        return True
    return normalized.startswith("replace-with-") or normalized.endswith("-change-me")


@dataclass(frozen=True)
class ConfigNormalizationResult:
    values: dict[str, str]
    generated_keys: tuple[str, ...]
    repaired_keys: tuple[str, ...]
    conflict_keys: tuple[str, ...]
    required_order: tuple[str, ...]


def normalize_local_beta_config_values(
    env: Mapping[str, str],
) -> ConfigNormalizationResult:
    values = {str(key): str(value) for key, value in env.items()}
    generated: list[str] = []
    repaired: list[str] = []
    conflicts: list[str] = []

    if is_placeholder_config_value(values.get("GUARDIAN_API_KEY")):
        values["GUARDIAN_API_KEY"] = secrets.token_hex(32)
        generated.append("GUARDIAN_API_KEY")

    for key, value in LOCAL_BETA_DEFAULTS.items():
        existing = values.get(key)
        if is_placeholder_config_value(existing):
            values[key] = value
            repaired.append(key)

    if str(values.get("LLM_PROVIDER", "")).strip().lower() != "local":
        if str(values.get("LLM_PROVIDER", "")).strip():
            conflicts.append("LLM_PROVIDER")
        # A conflicting valid choice is preserved for explicit user resolution.

    # Apply canonical local runtime preset env defaults.
    preset_id = normalize_local_runtime_preset(values.get("LOCAL_RUNTIME_PRESET"))
    preset_env = local_runtime_env_defaults(preset_id, docker=True)
    for key, value in preset_env.items():
        existing = values.get(key)
        if is_placeholder_config_value(existing):
            values[key] = value
            repaired.append(key)

    if is_placeholder_config_value(values.get("NEO4J_PASS")):
        values["NEO4J_PASS"] = secrets.token_urlsafe(24)
        generated.append("NEO4J_PASS")

    return ConfigNormalizationResult(
        values=values,
        generated_keys=tuple(dict.fromkeys(generated)),
        repaired_keys=tuple(dict.fromkeys(repaired)),
        conflict_keys=tuple(dict.fromkeys(conflicts)),
        required_order=(
            "GUARDIAN_API_KEY",
            "VITE_GUARDIAN_API_KEY",
            "LLM_PROVIDER",
            "LOCAL_RUNTIME_PRESET",
            "CODEXIFY_LOCAL_ONLY_MODE",
            "ALLOW_CLOUD_PROVIDERS",
            "LOCAL_BASE_URL",
            "LOCAL_CHAT_MODEL",
            "NEO4J_USER",
            "NEO4J_PASS",
        ),
    )


def normalize_local_beta_config_file(env_path: Path) -> ConfigNormalizationResult:
    env_path = env_path.expanduser().resolve()
    existing = read_env_file(env_path) if env_path.exists() else {}
    result = normalize_local_beta_config_values(existing)
    write_env_file(env_path, result.values)
    return result


def redact_diagnostic_value(key: str, value: str) -> str:
    if key in SECRET_CONFIG_KEYS or key.endswith("_KEY") or key.endswith("_TOKEN"):
        return "<redacted>"
    return value


def redacted_config_diagnostics(env: Mapping[str, str]) -> dict[str, str]:
    return {
        key: redact_diagnostic_value(key, str(value))
        for key, value in sorted(env.items())
    }


def _choose_guardian_api_key(
    *,
    existing_env_value: str,
    seed_value: str,
    kv_value: str | None,
) -> str:
    existing = existing_env_value.strip()
    if existing and not _is_placeholder_guardian_api_key(existing):
        return existing

    provided = (kv_value or "").strip()
    if provided:
        return provided

    seeded = seed_value.strip()
    if seeded and not _is_placeholder_guardian_api_key(seeded):
        return seeded

    return secrets.token_hex(32)


@dataclass(frozen=True)
class DoctorItem:
    name: str
    ok: bool
    required: bool
    detail: str = ""


def _truthy(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _notion_target_mode(env: dict[str, str]) -> str:
    mode = (env.get("NOTION_TARGET_MODE") or "").strip().lower()
    return mode or "database"


def _has_any(env: dict[str, str], keys: list[str]) -> bool:
    return any(env.get(key, "").strip() for key in keys)


def build_doctor_report(repo_root: Path) -> tuple[list[DoctorItem], int]:
    """
    Returns (items, exit_code).
    exit_code is 0 if all REQUIRED items are ok, else 1.
    """
    root = repo_root.resolve()
    env_path = default_env_target(root)
    env = read_env_file(env_path)

    deps = detect_core_dependencies()

    allow_cloud = _truthy(env.get("ALLOW_CLOUD_PROVIDERS", "true"))
    ollama_required = (
        False  # Inference is a later capability, never a core prerequisite.
    )

    # Docker requiredness: enforce only if existing config explicitly implies it.
    docker_required = False
    if "DATABASE_URL" in env and not env.get("DATABASE_URL", "").strip():
        docker_required = True
    if "ENABLE_OUTBOX" in env and _truthy(env.get("ENABLE_OUTBOX")):
        docker_required = True

    items: list[DoctorItem] = []
    items.append(
        DoctorItem(
            name=".env present",
            ok=env_path.exists(),
            required=True,
            detail=str(env_path),
        )
    )

    docker = deps["docker"]
    items.append(
        DoctorItem(
            name="Docker available",
            ok=docker.is_present,
            required=docker_required,
            detail=docker.help_text,
        )
    )

    ollama = deps["ollama"]
    items.append(
        DoctorItem(
            name="Ollama available",
            ok=ollama.is_present,
            required=ollama_required,
            detail=ollama.help_text,
        )
    )

    def req_if_enabled(flag_key: str, secret_key: str, label: str) -> DoctorItem:
        enabled = _truthy(env.get(flag_key, "false"))
        secret = env.get(secret_key, "").strip()
        ok = (not enabled) or bool(secret)
        detail = "enabled" if enabled else "disabled"
        if enabled and not secret:
            detail = f"enabled but {secret_key} missing"
        return DoctorItem(name=label, ok=ok, required=enabled, detail=detail)

    def notion_connector_item() -> DoctorItem:
        enabled = _truthy(env.get("CONNECTOR_NOTION_ENABLED", "false"))
        if not enabled:
            return DoctorItem(
                name="Notion connector config",
                ok=True,
                required=False,
                detail="disabled",
            )

        notion_api_key = env.get("NOTION_API_KEY", "").strip()
        if not notion_api_key:
            return DoctorItem(
                name="Notion connector config",
                ok=False,
                required=True,
                detail="enabled but NOTION_API_KEY missing",
            )

        mode = _notion_target_mode(env)
        if mode == "database":
            if not _has_any(env, ["NOTION_DATABASES", "NOTION_DATABASE_ID"]):
                return DoctorItem(
                    name="Notion connector config",
                    ok=False,
                    required=True,
                    detail=(
                        "enabled mode=database but missing "
                        "NOTION_DATABASES/NOTION_DATABASE_ID"
                    ),
                )
            return DoctorItem(
                name="Notion connector config",
                ok=True,
                required=True,
                detail="enabled mode=database",
            )

        if mode == "page":
            notion_parent_page_id = env.get("NOTION_PARENT_PAGE_ID", "").strip()
            if not notion_parent_page_id:
                return DoctorItem(
                    name="Notion connector config",
                    ok=False,
                    required=True,
                    detail="enabled mode=page but NOTION_PARENT_PAGE_ID missing",
                )
            return DoctorItem(
                name="Notion connector config",
                ok=True,
                required=True,
                detail="enabled mode=page",
            )

        return DoctorItem(
            name="Notion connector config",
            ok=False,
            required=True,
            detail=f"enabled but invalid NOTION_TARGET_MODE={mode!r}",
        )

    items.append(notion_connector_item())
    items.append(
        req_if_enabled(
            "CONNECTOR_GITHUB_ENABLED",
            "GITHUB_TOKEN",
            "GitHub connector config",
        )
    )

    exit_code = 0
    for item in items:
        if item.required and not item.ok:
            exit_code = 1
            break

    return items, exit_code


CommandRunner = Callable[..., subprocess.CompletedProcess[str]]
HttpGetter = Callable[[str, float], tuple[int, str]]


def _run_command(
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 10,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=str(cwd) if cwd else None,
        check=False,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _http_get(url: str, timeout: float = 3) -> tuple[int, str]:
    request = urllib.request.Request(url, headers={"Accept": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return int(response.status), response.read().decode("utf-8", "replace")


def _summary(
    state: SetupReadinessState,
    explanation: str,
    recommended_action: str,
    details: str = "",
) -> SetupReadinessSummary:
    core_ready = state in (
        SetupReadinessState.CORE_READY,
        SetupReadinessState.INFERENCE_READY,
    )
    inference_ready = state == SetupReadinessState.INFERENCE_READY
    action = BootstrapHumanAction.NONE
    if core_ready and not inference_ready:
        action = BootstrapHumanAction.PROVIDER_MODEL_CHOICE_REQUIRED
    elif state in (
        SetupReadinessState.DOCKER_MISSING,
        SetupReadinessState.DOCKER_NOT_RUNNING,
        SetupReadinessState.DOCKER_COMPOSE_MISSING,
    ):
        action = BootstrapHumanAction.PREREQUISITE_UNAVAILABLE
    elif state in (
        SetupReadinessState.MISSING_CONFIG,
        SetupReadinessState.CONFIG_INCOMPLETE,
    ):
        action = BootstrapHumanAction.CREDENTIALS_REQUIRED
    elif state == SetupReadinessState.CONFIG_CONFLICT:
        action = BootstrapHumanAction.CONSENT_REQUIRED
    return SetupReadinessSummary(
        state=state,
        explanation=explanation,
        recommended_action=recommended_action,
        details=details.strip(),
        bootstrap=BootstrapReadiness(
            (
                BootstrapWorkflow.COMPLETE
                if core_ready
                else BootstrapWorkflow.ACTION_REQUIRED
            ),
            core_ready,
            inference_ready,
            action,
        ),
    )


def _missing_or_placeholder_required_keys(
    env: Mapping[str, str], required_keys: tuple[str, ...]
) -> list[str]:
    return [key for key in required_keys if is_placeholder_config_value(env.get(key))]


def classify_config_readiness(env_path: Path) -> SetupReadinessSummary | None:
    if not env_path.exists():
        return _summary(
            SetupReadinessState.MISSING_CONFIG,
            "Local config is missing. Codexify needs to create your runtime config.",
            "Run the setup wizard to create .env for the supported local runtime preset.",
            f"env_path={env_path}",
        )

    env = read_env_file(env_path)
    missing = _missing_or_placeholder_required_keys(env, REQUIRED_CORE_CONFIG_KEYS)
    if missing:
        return _summary(
            SetupReadinessState.CONFIG_INCOMPLETE,
            "Local config is incomplete. Codexify needs to create or repair your runtime config.",
            "Run the setup wizard to repair missing local beta config values.",
            "missing_or_placeholder_keys=" + ",".join(missing),
        )

    conflicts: list[str] = []
    if env.get("LLM_PROVIDER", "").strip().lower() == "ollama":
        conflicts.append(
            "LLM_PROVIDER=ollama is not a valid provider; use LLM_PROVIDER=local"
        )
    if (
        not is_placeholder_config_value(env.get("LLM_PROVIDER"))
        and env.get("LLM_PROVIDER", "").strip().lower() != "local"
    ):
        conflicts.append("LLM_PROVIDER must be local")
    if conflicts:
        return _summary(
            SetupReadinessState.CONFIG_CONFLICT,
            "Config conflict found. Current local setup requires LLM_PROVIDER=local.",
            "Repair config so LLM_PROVIDER=local.",
            "conflicts=" + "; ".join(conflicts),
        )

    return None


def _command_ok(
    runner: CommandRunner,
    args: list[str],
    *,
    cwd: Path | None = None,
    timeout: float = 10,
) -> tuple[bool, str]:
    try:
        result = runner(args, cwd=cwd, timeout=timeout)
    except FileNotFoundError:
        return False, "not found"
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except Exception as exc:  # pragma: no cover - defensive for platform errors.
        return False, str(exc)

    detail = "\n".join(
        part.strip()
        for part in (result.stdout or "", result.stderr or "")
        if part.strip()
    )
    return result.returncode == 0, detail[:1200]


def _http_ok(getter: HttpGetter, url: str, timeout: float = 3) -> tuple[bool, str]:
    try:
        status, body = getter(url, timeout)
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace") if exc.fp else ""
        return False, f"status={exc.code} {body[:500]}"
    except Exception as exc:
        return False, str(exc)
    if 200 <= status < 300:
        return True, body[:1200]
    return False, f"status={status} {body[:500]}"


def _ollama_model_names(body: str) -> set[str]:
    import json

    try:
        payload = json.loads(body)
    except Exception:
        return set()
    models = payload.get("models", []) if isinstance(payload, dict) else []
    names: set[str] = set()
    for model in models:
        if isinstance(model, dict):
            name = str(model.get("name") or model.get("model") or "").strip()
            if name:
                names.add(name)
    return names


def classify_setup_readiness(
    repo_root: Path,
    *,
    runner: CommandRunner = _run_command,
    http_getter: HttpGetter = _http_get,
) -> SetupReadinessSummary:
    root = repo_root.resolve()
    env_path = default_env_target(root)
    config_result = classify_config_readiness(env_path)
    if config_result is not None:
        return config_result

    env = read_env_file(env_path)
    docker = detect_dependency("docker", "Docker", custom_path=env.get("DOCKER_BIN"))
    if not docker.is_present:
        return _summary(
            SetupReadinessState.DOCKER_MISSING,
            "Docker is not installed or could not be found.",
            "Install Docker Desktop, then retry.",
            docker.help_text,
        )

    docker_cmd = docker.found_path or "docker"
    ok, detail = _command_ok(runner, [docker_cmd, "info"], cwd=root)
    if not ok:
        return _summary(
            SetupReadinessState.DOCKER_NOT_RUNNING,
            "Docker is installed, but the daemon is not running.",
            "Open Docker Desktop, then retry.",
            detail,
        )

    ok, detail = _command_ok(runner, [docker_cmd, "compose", "version"], cwd=root)
    if not ok:
        return _summary(
            SetupReadinessState.DOCKER_COMPOSE_MISSING,
            "Docker Compose is not available through the Docker CLI.",
            "Install or update Docker Desktop, then retry.",
            detail,
        )

    ok, detail = _command_ok(runner, [docker_cmd, "compose", "config"], cwd=root)
    if not ok:
        return _summary(
            SetupReadinessState.COMPOSE_CONFIG_INVALID,
            "Docker Compose config is invalid.",
            "Repair the compose/env configuration, then retry.",
            detail,
        )

    # Existing volumes are owned state, never a reason to block a healthy rerun.
    backend_base = "http://127.0.0.1:" + env.get("CODEXIFY_BACKEND_PORT", "8888")
    frontend_base = "http://127.0.0.1:" + env.get("CODEXIFY_FRONTEND_PORT", "5173")
    backend_ok, backend_detail = _http_ok(http_getter, backend_base + "/ping")
    if not backend_ok:
        return _summary(
            SetupReadinessState.BACKEND_NOT_RUNNING,
            "Backend is not running.",
            "Start the backend service, then retry.",
            backend_detail,
        )

    health_ok, health_detail = _http_ok(http_getter, backend_base + "/health")
    if not health_ok or '"ok"' not in health_detail.lower():
        return _summary(
            SetupReadinessState.BACKEND_UNHEALTHY,
            "Backend is reachable but not healthy.",
            "Check backend and worker health, then retry.",
            health_detail,
        )

    chat_ok, chat_detail = _http_ok(http_getter, backend_base + "/health/chat")
    try:
        completion = json.loads(chat_detail).get("completion_service", {})
    except (ValueError, AttributeError):
        completion = {}
    if (
        not chat_ok
        or completion.get("ok") is not True
        or completion.get("redis_reachable") is not True
    ):
        return _summary(
            SetupReadinessState.BACKEND_UNHEALTHY,
            "Core queue and chat worker health have not passed.",
            "Run ./scripts/setup to verify or resume core services.",
            chat_detail,
        )

    frontend_ok, frontend_detail = _http_ok(http_getter, frontend_base + "/")
    if not frontend_ok:
        return _summary(
            SetupReadinessState.FRONTEND_NOT_RUNNING,
            "Frontend is not running.",
            "Start the Web UI service.",
            frontend_detail,
        )

    missing_inference = _missing_or_placeholder_required_keys(
        env, REQUIRED_INFERENCE_CONFIG_KEYS
    )
    if missing_inference:
        return _summary(
            SetupReadinessState.CORE_READY,
            "Your workspace is ready; inference configuration is incomplete.",
            "Open Codexify and choose local inference when ready. Chat is unavailable until its health checks pass.",
            "missing_or_placeholder_keys=" + ",".join(missing_inference),
        )

    llm_ok, llm_detail = _http_ok(http_getter, backend_base + "/health/llm")
    try:
        llm = json.loads(llm_detail)
        details = llm.get("details", {})
        inference_ready = bool(
            llm_ok
            and llm.get("status") in ("ok", "healthy", "online")
            and details.get("provider") == "local"
            and details.get("configured_model_available") is True
            and details.get("models_available") is True
            and details.get("ok") is not False
            and details.get("provider_runtime", {}).get("available") is not False
        )
    except (ValueError, AttributeError):
        inference_ready = False
    return _summary(
        (
            SetupReadinessState.INFERENCE_READY
            if inference_ready
            else SetupReadinessState.CORE_READY
        ),
        (
            "Your workspace is ready."
            if inference_ready
            else "Your workspace is ready; inference setup is incomplete."
        ),
        (
            "Open Codexify."
            if inference_ready
            else "Open Codexify and choose local inference when ready. Chat is unavailable until its health checks pass."
        ),
        "provider=" + env.get("LOCAL_PROVIDER_DISPLAY_NAME", "Local"),
    )
