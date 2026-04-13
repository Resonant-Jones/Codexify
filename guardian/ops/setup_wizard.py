from __future__ import annotations

import json
import os
import platform
import secrets
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

import requests


@dataclass(frozen=True)
class DepStatus:
    name: str
    is_present: bool
    found_path: str | None
    help_text: str


DockerReadinessStatus = Literal[
    "missing",
    "binary_only",
    "daemon_unreachable",
    "compose_unavailable",
    "ready",
]

_DOCKER_READINESS_STATUS_VALUES = {
    "missing",
    "binary_only",
    "daemon_unreachable",
    "compose_unavailable",
    "ready",
}


ComposeBootstrapStatus = Literal[
    "skipped",
    "preflight_failed",
    "compose_missing",
    "bootstrap_failed",
    "started",
]

_COMPOSE_BOOTSTRAP_STATUS_VALUES = {
    "skipped",
    "preflight_failed",
    "compose_missing",
    "bootstrap_failed",
    "started",
}

SUPPORTED_LOCAL_COMPOSE_BOOTSTRAP_SERVICES = (
    "db",
    "redis",
    "backend",
    "worker-chat",
    "worker-document-embed",
)


@dataclass(frozen=True)
class DockerReadiness:
    status: DockerReadinessStatus
    ok: bool
    docker_binary_present: bool
    docker_binary_path: str | None
    docker_daemon_reachable: bool
    docker_compose_available: bool
    detail: str


@dataclass(frozen=True)
class ComposeBootstrapResult:
    ok: bool
    status: ComposeBootstrapStatus
    detail: str
    command: list[str]
    returncode: int | None


RuntimeReadinessStatus = Literal[
    "skipped",
    "unreachable",
    "degraded",
    "not_ready",
    "ready",
]

_RUNTIME_READINESS_STATUS_VALUES = {
    "skipped",
    "unreachable",
    "degraded",
    "not_ready",
    "ready",
}


@dataclass(frozen=True)
class RuntimeReadinessResult:
    ok: bool
    status: RuntimeReadinessStatus
    detail: str
    checked_urls: list[str]


@dataclass(frozen=True)
class LauncherHandoffResult:
    should_run_wizard: bool
    setup_complete: bool
    runtime_profile: str
    env_path: str | None
    handoff_target: str | None
    detail: str


@dataclass(frozen=True)
class InstallerBootstrapState:
    setup_complete: bool = False
    runtime_profile: str = "docker"
    allow_cloud_providers: bool = True
    env_path: str = ""
    last_updated_at: str = ""


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


def _probe_command(
    command: list[str],
    timeout_seconds: float,
) -> tuple[bool, str]:
    try:
        completed = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except FileNotFoundError as exc:
        return False, str(exc)
    except PermissionError as exc:
        return False, str(exc)
    except subprocess.TimeoutExpired:
        return False, f"timed out after {timeout_seconds:.1f}s"
    except OSError as exc:
        return False, str(exc)

    output_parts = [
        part.strip()
        for part in (completed.stdout, completed.stderr)
        if part and part.strip()
    ]
    detail = "\n".join(output_parts).strip()
    if completed.returncode == 0:
        return True, detail
    return False, detail or f"exit code {completed.returncode}"


def _looks_like_daemon_unreachable(detail: str) -> bool:
    lowered = detail.lower()
    return any(
        needle in lowered
        for needle in (
            "cannot connect to the docker daemon",
            "is the docker daemon running",
            "error during connect",
            "connection refused",
            "dial unix",
            "permission denied",
            "no such file or directory",
        )
    )


def _probe_compose_availability(
    docker_binary_path: str,
    timeout_seconds: float,
) -> tuple[bool, str]:
    compose_invocation, compose_detail = _resolve_compose_invocation(
        docker_binary_path,
        timeout_seconds,
    )
    return compose_invocation is not None, compose_detail


def _resolve_compose_invocation(
    docker_binary_path: str,
    timeout_seconds: float,
) -> tuple[list[str] | None, str]:
    plugin_ok, plugin_detail = _probe_command(
        [docker_binary_path, "compose", "version", "--short"],
        timeout_seconds,
    )
    if plugin_ok:
        return [docker_binary_path, "compose"], (
            plugin_detail or "docker compose is available"
        )

    legacy_binary = shutil.which("docker-compose")
    if legacy_binary:
        legacy_ok, legacy_detail = _probe_command(
            [legacy_binary, "version", "--short"],
            timeout_seconds,
        )
        if legacy_ok:
            return [
                legacy_binary
            ], legacy_detail or "docker-compose is available"
        legacy_message = legacy_detail or "docker-compose probe failed"
    else:
        legacy_message = "docker-compose binary not found"

    plugin_message = plugin_detail or "docker compose probe failed"
    return None, "; ".join(
        message for message in (plugin_message, legacy_message) if message
    )


def _compose_bootstrap_command(compose_invocation: list[str]) -> list[str]:
    return [
        *compose_invocation,
        "up",
        "-d",
        *SUPPORTED_LOCAL_COMPOSE_BOOTSTRAP_SERVICES,
    ]


def _summarize_process_output(
    stdout: str | None,
    stderr: str | None,
    *,
    limit: int = 400,
) -> str:
    parts = [part.strip() for part in (stdout, stderr) if part and part.strip()]
    detail = "\n".join(parts).strip()
    if len(detail) > limit:
        detail = detail[: limit - 3].rstrip() + "..."
    return detail


def _resolve_runtime_api_base(api_base: str | None = None) -> str:
    candidate = (
        api_base
        or os.getenv("GUARDIAN_API_BASE")
        or os.getenv("API_BASE")
        or "http://127.0.0.1:8888"
    ).strip()
    return candidate.rstrip("/") or "http://127.0.0.1:8888"


def default_local_runtime_handoff_target(api_base: str | None = None) -> str:
    return _resolve_runtime_api_base(api_base)


def _probe_runtime_surface(
    url: str,
    timeout_seconds: float,
) -> tuple[int | None, dict[str, object] | None, str]:
    try:
        response = requests.get(url, timeout=timeout_seconds)
    except requests.exceptions.RequestException as exc:
        return None, None, f"{type(exc).__name__}: {exc}"
    except OSError as exc:
        return None, None, f"{type(exc).__name__}: {exc}"

    payload: dict[str, object] | None = None
    try:
        parsed = response.json()
    except ValueError:
        parsed = None
    if isinstance(parsed, dict):
        payload = parsed

    raw_text = response.text.strip()
    detail = f"HTTP {response.status_code}"
    if payload is None and raw_text:
        detail = f"{detail}: {raw_text[:200]}"
    return response.status_code, payload, detail


def _payload_status(payload: dict[str, object] | None) -> str:
    if not isinstance(payload, dict):
        return ""
    return str(payload.get("status") or "").strip().lower()


def _payload_detail_value(
    payload: dict[str, object] | None,
    *keys: str,
) -> str:
    if not isinstance(payload, dict):
        return ""
    for key in keys:
        value = payload.get(key)
        if isinstance(value, str):
            text = value.strip()
            if text:
                return text
    return ""


def _summarize_core_health(
    http_status: int | None,
    payload: dict[str, object] | None,
    transport_detail: str,
) -> str:
    if http_status is None:
        return f"/health unreachable: {transport_detail}"

    parts = [f"/health HTTP {http_status}"]
    status = _payload_status(payload)
    if status:
        parts.append(f"status={status}")
    supported_profile = _payload_detail_value(
        payload.get("details") if isinstance(payload, dict) else None,
        "supported_profile",
    )
    if not supported_profile and isinstance(payload, dict):
        supported_profile = _payload_detail_value(payload, "supported_profile")
    if supported_profile:
        parts.append(f"supported_profile={supported_profile}")
    if transport_detail and transport_detail != f"HTTP {http_status}":
        parts.append(transport_detail)
    return ", ".join(parts)


def _summarize_chat_health(
    http_status: int | None,
    payload: dict[str, object] | None,
    transport_detail: str,
) -> str:
    if http_status is None:
        return f"/health/chat unreachable: {transport_detail}"

    parts = [f"/health/chat HTTP {http_status}"]
    status = _payload_status(payload)
    if status:
        parts.append(f"status={status}")
    notes = payload.get("notes") if isinstance(payload, dict) else None
    if isinstance(notes, list):
        note_text = "; ".join(
            str(note).strip() for note in notes if str(note).strip()
        )
        if note_text:
            parts.append(note_text)
    worker = payload.get("worker") if isinstance(payload, dict) else None
    if isinstance(worker, dict):
        worker_status = str(worker.get("status") or "").strip().lower()
        if worker_status:
            parts.append(f"worker={worker_status}")
        worker_reason = _payload_detail_value(worker, "reason", "detail")
        if worker_reason:
            parts.append(worker_reason)
    queue = payload.get("queue") if isinstance(payload, dict) else None
    if isinstance(queue, dict):
        queue_status = str(queue.get("status") or "").strip().lower()
        if queue_status:
            parts.append(f"queue={queue_status}")
    error = _payload_detail_value(payload, "error", "message")
    if error:
        parts.append(error)
    if transport_detail and transport_detail != f"HTTP {http_status}":
        parts.append(transport_detail)
    return ", ".join(parts)


def _summarize_llm_health(
    http_status: int | None,
    payload: dict[str, object] | None,
    transport_detail: str,
) -> str:
    if http_status is None:
        return f"/api/health/llm unreachable: {transport_detail}"

    parts = [f"/api/health/llm HTTP {http_status}"]
    status = _payload_status(payload)
    if status:
        parts.append(f"status={status}")
    details = None
    if isinstance(payload, dict):
        details = payload.get("details")
    if isinstance(details, dict):
        provider = str(details.get("provider") or "").strip()
        if provider:
            parts.append(f"provider={provider}")
        model = str(details.get("model") or "").strip()
        if model:
            parts.append(f"model={model}")
        error = _payload_detail_value(details, "error", "message")
        if error:
            parts.append(error)
        provider_runtime = details.get("provider_runtime")
        if isinstance(provider_runtime, dict):
            runtime_state = str(
                provider_runtime.get("state")
                or provider_runtime.get("status")
                or ""
            ).strip()
            if runtime_state:
                parts.append(f"runtime={runtime_state}")
    error = _payload_detail_value(payload, "error", "message")
    if error:
        parts.append(error)
    if transport_detail and transport_detail != f"HTTP {http_status}":
        parts.append(transport_detail)
    return ", ".join(parts)


def _summarize_retrieval_health(
    http_status: int | None,
    payload: dict[str, object] | None,
    transport_detail: str,
) -> str:
    if http_status is None:
        return f"/api/health/retrieval unreachable: {transport_detail}"

    parts = [f"/api/health/retrieval HTTP {http_status}"]
    status = _payload_status(payload)
    if status:
        parts.append(f"status={status}")
    reason = _payload_detail_value(payload, "reason", "error", "message")
    if reason:
        parts.append(reason)
    proof_capable = None
    if isinstance(payload, dict):
        proof_capable = payload.get("proof_capable")
    if proof_capable is not None:
        parts.append(f"proof_capable={proof_capable}")
    if transport_detail and transport_detail != f"HTTP {http_status}":
        parts.append(transport_detail)
    return ", ".join(parts)


def detect_runtime_readiness(
    *,
    runtime_profile: str = "docker",
    api_base: str | None = None,
    timeout_seconds: float = 3.0,
) -> RuntimeReadinessResult:
    if runtime_profile != "docker":
        return RuntimeReadinessResult(
            ok=False,
            status="skipped",
            detail=(
                "Runtime readiness check skipped for "
                f"runtime_profile={runtime_profile!r}."
            ),
            checked_urls=[],
        )

    base_url = _resolve_runtime_api_base(api_base)
    checked_urls = [
        f"{base_url}/health",
        f"{base_url}/health/chat",
        f"{base_url}/api/health/llm",
        f"{base_url}/api/health/retrieval",
    ]

    core_status, core_payload, core_detail = _probe_runtime_surface(
        checked_urls[0],
        timeout_seconds,
    )
    core_summary = _summarize_core_health(
        core_status,
        core_payload,
        core_detail,
    )
    if core_status is None or core_status >= 400:
        return RuntimeReadinessResult(
            ok=False,
            status="unreachable",
            detail=f"Backend is not reachable. {core_summary}",
            checked_urls=[checked_urls[0]],
        )

    chat_status, chat_payload, chat_detail = _probe_runtime_surface(
        checked_urls[1],
        timeout_seconds,
    )
    chat_summary = _summarize_chat_health(
        chat_status,
        chat_payload,
        chat_detail,
    )
    chat_ok = (
        chat_status is not None
        and chat_status < 400
        and str((chat_payload or {}).get("status") or "").strip().lower()
        in {"healthy", "ok"}
    )

    llm_status, llm_payload, llm_detail = _probe_runtime_surface(
        checked_urls[2],
        timeout_seconds,
    )
    llm_summary = _summarize_llm_health(
        llm_status,
        llm_payload,
        llm_detail,
    )

    (
        retrieval_status,
        retrieval_payload,
        retrieval_detail,
    ) = _probe_runtime_surface(
        checked_urls[3],
        timeout_seconds,
    )
    retrieval_summary = _summarize_retrieval_health(
        retrieval_status,
        retrieval_payload,
        retrieval_detail,
    )

    llm_ok = (
        llm_status is not None
        and llm_status < 400
        and _payload_status(llm_payload) in {"ok", "healthy", "online"}
    )
    retrieval_ok = (
        retrieval_status is not None
        and retrieval_status < 400
        and _payload_status(retrieval_payload) in {"ready", "ok"}
        and bool((retrieval_payload or {}).get("ok"))
    )
    if not chat_ok:
        return RuntimeReadinessResult(
            ok=False,
            status="not_ready",
            detail=(
                "Backend is reachable, but chat runtime is not ready. "
                f"{core_summary}; {chat_summary}; {llm_summary}; "
                f"{retrieval_summary}"
            ),
            checked_urls=checked_urls,
        )

    if not llm_ok or not retrieval_ok:
        return RuntimeReadinessResult(
            ok=False,
            status="degraded",
            detail=(
                "Backend and chat are ready, but provider or retrieval "
                "is degraded. "
                f"{core_summary}; {chat_summary}; {llm_summary}; "
                f"{retrieval_summary}"
            ),
            checked_urls=checked_urls,
        )

    return RuntimeReadinessResult(
        ok=True,
        status="ready",
        detail=(
            "Local runtime is ready for handoff. "
            f"{core_summary}; {chat_summary}; {llm_summary}; "
            f"{retrieval_summary}"
        ),
        checked_urls=checked_urls,
    )


def resolve_launcher_startup_handoff(
    repo_root: Path,
    *,
    runtime_readiness: RuntimeReadinessResult | None = None,
    api_base: str | None = None,
) -> LauncherHandoffResult:
    state = effective_installer_bootstrap_state(repo_root)
    setup_complete = bool(state.setup_complete)
    runtime_profile = str(state.runtime_profile or "docker").strip() or "docker"
    env_path = state.env_path.strip() or str(default_env_target(repo_root))

    if not setup_complete:
        return LauncherHandoffResult(
            should_run_wizard=True,
            setup_complete=False,
            runtime_profile=runtime_profile,
            env_path=env_path,
            handoff_target=None,
            detail=(
                "Installer bootstrap state is incomplete or unavailable; "
                "launch the setup wizard."
            ),
        )

    if runtime_profile != "docker":
        return LauncherHandoffResult(
            should_run_wizard=False,
            setup_complete=True,
            runtime_profile=runtime_profile,
            env_path=env_path,
            handoff_target=None,
            detail=(
                f"Installer bootstrap is complete for "
                f"runtime_profile={runtime_profile!r}; "
                "local runtime handoff is not required."
            ),
        )

    readiness = runtime_readiness or detect_runtime_readiness(
        runtime_profile=runtime_profile,
        api_base=api_base,
    )
    if readiness.status != "ready":
        return LauncherHandoffResult(
            should_run_wizard=True,
            setup_complete=True,
            runtime_profile=runtime_profile,
            env_path=env_path,
            handoff_target=None,
            detail=(
                "Installer bootstrap is complete, but the local runtime "
                f"is not ready. {readiness.detail}"
            ),
        )

    handoff_target = default_local_runtime_handoff_target(api_base)
    return LauncherHandoffResult(
        should_run_wizard=False,
        setup_complete=True,
        runtime_profile=runtime_profile,
        env_path=env_path,
        handoff_target=handoff_target,
        detail=(
            "Installer bootstrap is complete and the local runtime is ready "
            f"for handoff. Target: {handoff_target}."
        ),
    )


def attempt_compose_bootstrap(
    repo_root: Path,
    *,
    requested: bool,
    runtime_profile: str,
    docker_custom_path: str | None = None,
    docker_readiness: DockerReadiness | None = None,
    readiness_timeout_seconds: float = 4.0,
    bootstrap_timeout_seconds: float = 120.0,
) -> ComposeBootstrapResult:
    planned_command = _compose_bootstrap_command(["docker", "compose"])
    if not requested or runtime_profile != "docker":
        detail = f"Compose bootstrap skipped for runtime_profile={runtime_profile!r}."
        return ComposeBootstrapResult(
            ok=False,
            status="skipped",
            detail=detail,
            command=planned_command,
            returncode=None,
        )

    readiness = docker_readiness or detect_docker_readiness(
        docker_custom_path,
        timeout_seconds=readiness_timeout_seconds,
    )
    if not readiness.ok:
        status = (
            "compose_missing"
            if readiness.status == "compose_unavailable"
            else "preflight_failed"
        )
        detail = readiness.detail
        return ComposeBootstrapResult(
            ok=False,
            status=status,
            detail=detail,
            command=planned_command,
            returncode=None,
        )

    compose_invocation, compose_detail = _resolve_compose_invocation(
        readiness.docker_binary_path or "docker",
        readiness_timeout_seconds,
    )
    if compose_invocation is None:
        return ComposeBootstrapResult(
            ok=False,
            status="compose_missing",
            detail=compose_detail,
            command=planned_command,
            returncode=None,
        )

    command = _compose_bootstrap_command(compose_invocation)
    try:
        completed = subprocess.run(
            command,
            cwd=str(repo_root),
            capture_output=True,
            text=True,
            check=False,
            timeout=bootstrap_timeout_seconds,
        )
    except FileNotFoundError as exc:
        return ComposeBootstrapResult(
            ok=False,
            status="bootstrap_failed",
            detail=str(exc),
            command=command,
            returncode=None,
        )
    except PermissionError as exc:
        return ComposeBootstrapResult(
            ok=False,
            status="bootstrap_failed",
            detail=str(exc),
            command=command,
            returncode=None,
        )
    except subprocess.TimeoutExpired:
        return ComposeBootstrapResult(
            ok=False,
            status="bootstrap_failed",
            detail=(
                f"Compose bootstrap timed out after "
                f"{bootstrap_timeout_seconds:.1f}s"
            ),
            command=command,
            returncode=None,
        )
    except OSError as exc:
        return ComposeBootstrapResult(
            ok=False,
            status="bootstrap_failed",
            detail=str(exc),
            command=command,
            returncode=None,
        )

    if completed.returncode != 0:
        detail = _summarize_process_output(
            completed.stdout,
            completed.stderr,
        )
        if detail:
            detail = (
                f"Compose bootstrap failed with exit code "
                f"{completed.returncode}: {detail}"
            )
        else:
            detail = (
                f"Compose bootstrap failed with exit code "
                f"{completed.returncode}"
            )
        return ComposeBootstrapResult(
            ok=False,
            status="bootstrap_failed",
            detail=detail,
            command=command,
            returncode=completed.returncode,
        )

    services = ", ".join(SUPPORTED_LOCAL_COMPOSE_BOOTSTRAP_SERVICES)
    detail = f"Started local Compose stack for {services}."
    output_detail = _summarize_process_output(
        completed.stdout,
        completed.stderr,
    )
    if output_detail:
        detail = f"{detail} {output_detail}"

    return ComposeBootstrapResult(
        ok=True,
        status="started",
        detail=detail,
        command=command,
        returncode=completed.returncode,
    )


def detect_docker_readiness(
    custom_path: str | None = None,
    *,
    timeout_seconds: float = 4.0,
) -> DockerReadiness:
    custom_resolved = _resolve_custom_binary_path(custom_path)
    custom_prefix = ""
    if custom_path and custom_resolved is None:
        custom_prefix = f"Custom Docker path is not executable: {custom_path}. "

    binary_path = custom_resolved or shutil.which("docker")
    if not binary_path:
        return DockerReadiness(
            status="missing",
            ok=False,
            docker_binary_present=False,
            docker_binary_path=None,
            docker_daemon_reachable=False,
            docker_compose_available=False,
            detail=f"{custom_prefix}Docker CLI not found. {_os_hint_lines('docker')}",
        )

    daemon_ok, daemon_detail = _probe_command(
        [binary_path, "info"],
        timeout_seconds,
    )
    if not daemon_ok:
        if _looks_like_daemon_unreachable(daemon_detail):
            status = "daemon_unreachable"
            detail = (
                f"{custom_prefix}Docker binary found at {binary_path}, "
                f"but the daemon is not reachable. {daemon_detail}"
            )
        else:
            status = "binary_only"
            detail = (
                f"{custom_prefix}Docker binary found at {binary_path}, "
                f"but readiness could not be confirmed. {daemon_detail}"
            )
        return DockerReadiness(
            status=status,
            ok=False,
            docker_binary_present=True,
            docker_binary_path=binary_path,
            docker_daemon_reachable=False,
            docker_compose_available=False,
            detail=detail,
        )

    compose_ok, compose_detail = _probe_compose_availability(
        binary_path,
        timeout_seconds,
    )
    if not compose_ok:
        return DockerReadiness(
            status="compose_unavailable",
            ok=False,
            docker_binary_present=True,
            docker_binary_path=binary_path,
            docker_daemon_reachable=True,
            docker_compose_available=False,
            detail=(
                f"{custom_prefix}Docker daemon is reachable at {binary_path}, "
                f"but Compose is unavailable. {compose_detail}"
            ),
        )

    return DockerReadiness(
        status="ready",
        ok=True,
        docker_binary_present=True,
        docker_binary_path=binary_path,
        docker_daemon_reachable=True,
        docker_compose_available=True,
        detail=(
            f"{custom_prefix}Docker daemon is reachable and Compose is "
            f"available at {binary_path}. {compose_detail}"
        ),
    )


def detect_dependency(
    binary_name: str,
    display_name: str,
    custom_path: str | None = None,
) -> DepStatus:
    custom_resolved = _resolve_custom_binary_path(custom_path)
    found = custom_resolved or shutil.which(binary_name)
    help_text = _os_hint_lines(binary_name)

    if custom_path and custom_resolved is None:
        help_text = f"Custom path is not executable: {custom_path}. {help_text}"

    return DepStatus(
        name=display_name,
        is_present=found is not None,
        found_path=found,
        help_text=help_text,
    )


def detect_core_dependencies(
    custom_paths: dict[str, str] | None = None,
    *,
    docker_readiness: DockerReadiness | None = None,
) -> dict[str, DepStatus]:
    """
    Core deps for a local-first default experience.
    - docker: optional depending on how you run services, but common for DB/redis.
    - ollama: optional unless you want local LLM on first run.
    """

    paths = custom_paths or {}
    readiness = docker_readiness or detect_docker_readiness(paths.get("docker"))
    return {
        "docker": DepStatus(
            name="Docker",
            is_present=readiness.ok,
            found_path=readiness.docker_binary_path,
            help_text=readiness.detail,
        ),
        "ollama": detect_dependency(
            "ollama", "Ollama", custom_path=paths.get("ollama")
        ),
    }


def env_kv_sanitize(value: str) -> str:
    # Minimal sanitization for .env values.
    if any(ch in value for ch in (" ", "#")):
        escaped = value.replace("\\", "\\\\").replace('"', '\\"')
        return f'"{escaped}"'
    return value


def write_env_file(
    env_path: Path,
    kv: dict[str, str],
    *,
    create_backup: bool = True,
) -> None:
    env_path = env_path.expanduser().resolve()
    env_path.parent.mkdir(parents=True, exist_ok=True)

    if env_path.exists() and create_backup:
        backup_path = env_path.with_suffix(env_path.suffix + ".bak")
        backup_path.write_text(
            env_path.read_text(encoding="utf-8"), encoding="utf-8"
        )

    existing_env_values = (
        _read_env_with_order(env_path)[1] if env_path.exists() else {}
    )
    template_path = env_path.parent / ".env.template"
    if template_path.exists():
        base_order, base_values = _read_env_with_order(template_path)
    elif env_path.exists():
        base_order, base_values = _read_env_with_order(env_path)
    else:
        base_order, base_values = ([], {})

    merged_values = dict(base_values)
    for key, value in kv.items():
        if value is None:
            continue
        merged_values[key] = value

    guardian_api_key = _choose_guardian_api_key(
        existing_env_value=existing_env_values.get("GUARDIAN_API_KEY", ""),
        seed_value=base_values.get("GUARDIAN_API_KEY", ""),
        kv_value=kv.get("GUARDIAN_API_KEY", ""),
    )
    merged_values["GUARDIAN_API_KEY"] = guardian_api_key
    merged_values["VITE_GUARDIAN_API_KEY"] = guardian_api_key

    lines = []
    lines.append("# Generated by Codexify Setup Wizard")
    lines.append(
        "# Safe to edit. Re-running the wizard will overwrite this file "
        "(and create a .bak)."
    )

    written: set[str] = set()
    for key in base_order:
        if key in merged_values and key not in written:
            lines.append(f"{key}={env_kv_sanitize(merged_values[key])}")
            written.add(key)

    for key in kv:
        if key in merged_values and key not in written:
            lines.append(f"{key}={env_kv_sanitize(merged_values[key])}")
            written.add(key)

    for key, value in merged_values.items():
        if key in written:
            continue
        lines.append(f"{key}={env_kv_sanitize(value)}")

    lines.append("")
    env_path.write_text("\n".join(lines), encoding="utf-8")


def default_env_target(repo_root: Path) -> Path:
    """
    Prefer .env.local if you want to keep developer overrides separate.
    If your repo already uses .env, switch to that for consistency.
    """

    return repo_root / ".env"


def default_installer_state_path(repo_root: Path) -> Path:
    return repo_root / ".codexify" / "installer-bootstrap-state.json"


def default_installer_bootstrap_state(
    repo_root: Path,
) -> InstallerBootstrapState:
    return InstallerBootstrapState(env_path=str(default_env_target(repo_root)))


def _coerce_bool(value: object, default: bool) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized in {"1", "true", "yes", "y", "on"}:
            return True
        if normalized in {"0", "false", "no", "n", "off"}:
            return False
    return default


def write_installer_state_file(
    state_path: Path,
    state: InstallerBootstrapState,
) -> None:
    resolved = state_path.expanduser().resolve()
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(
        json.dumps(asdict(state), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def read_installer_state_file(repo_root: Path) -> InstallerBootstrapState:
    state_path = default_installer_state_path(repo_root).expanduser().resolve()
    default_state = default_installer_bootstrap_state(repo_root)

    try:
        raw_state = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        return default_state

    if not isinstance(raw_state, dict):
        return default_state

    runtime_profile = str(
        raw_state.get("runtime_profile") or default_state.runtime_profile
    )
    if runtime_profile not in {"docker", "external"}:
        runtime_profile = default_state.runtime_profile

    env_path = str(raw_state.get("env_path") or default_state.env_path)
    last_updated_at = str(
        raw_state.get("last_updated_at") or default_state.last_updated_at
    )

    return InstallerBootstrapState(
        setup_complete=_coerce_bool(
            raw_state.get("setup_complete"), default_state.setup_complete
        ),
        runtime_profile=runtime_profile,
        allow_cloud_providers=_coerce_bool(
            raw_state.get("allow_cloud_providers"),
            default_state.allow_cloud_providers,
        ),
        env_path=env_path,
        last_updated_at=last_updated_at,
    )


def effective_installer_bootstrap_state(
    repo_root: Path,
) -> InstallerBootstrapState:
    return read_installer_state_file(repo_root)


def installer_bootstrap_is_complete(repo_root: Path) -> bool:
    return effective_installer_bootstrap_state(repo_root).setup_complete


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
    ollama_required = not allow_cloud

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
            detail=ollama.found_path or ollama.help_text,
        )
    )

    def req_if_enabled(
        flag_key: str, secret_key: str, label: str
    ) -> DoctorItem:
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
