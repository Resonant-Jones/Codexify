#!/usr/bin/env python3
"""Verify that the live image-turn containment proof is running on the expected runtime.

This helper does not assert containment. It fails closed when the proof runtime
is stale or unhealthy, and emits both a human-readable summary and a JSON report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import requests

FRESH_HEARTBEAT_THRESHOLD_SECONDS = 10.0
DEAD_HEARTBEAT_THRESHOLD_SECONDS = 60.0

_MARKER_KEY_RE = re.compile(r"(commit|sha|version|revision)", re.IGNORECASE)
_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
_HASH_EXTRACT_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)
_VERSION_EXTRACT_RE = re.compile(
    r"\b\d+(?:\.\d+){1,3}(?:[-+][0-9A-Za-z._-]+)?\b"
)


def _run_command(
    command: list[str],
    *,
    cwd: Path | None = None,
    timeout: int = 30,
    capture_output: bool = True,
    text: bool = True,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        cwd=str(cwd) if cwd is not None else None,
        timeout=timeout,
        capture_output=capture_output,
        text=text,
        check=check,
    )


def _json_response(
    url: str,
    *,
    timeout: float,
    http_get: Callable[..., Any],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    try:
        response = http_get(url, timeout=timeout)
    except Exception as exc:  # pragma: no cover - network/runtime failure
        if errors is not None:
            errors.append(f"{url} request failed: {type(exc).__name__}: {exc}")
        return {
            "status_code": None,
            "body": {
                "status": "unavailable",
                "error": f"{type(exc).__name__}: {exc}",
            },
        }
    try:
        body = response.json()
    except Exception:
        body = {"raw_text": getattr(response, "text", "")}
    if not isinstance(body, dict):
        body = {"value": body}
    return {
        "status_code": getattr(response, "status_code", None),
        "body": body,
    }


def _compose_prefix(
    *,
    compose_file: str | None,
    compose_project: str | None,
) -> list[str]:
    prefix = ["docker", "compose"]
    if compose_file:
        prefix.extend(["-f", compose_file])
    if compose_project:
        prefix.extend(["-p", compose_project])
    return prefix


def _run_command_stdout(
    command: list[str],
    *,
    cwd: Path | None,
    timeout: int = 30,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> str:
    try:
        completed = run_command(
            command,
            cwd=cwd,
            timeout=timeout,
            capture_output=True,
            text=True,
            check=True,
        )
    except Exception as exc:  # pragma: no cover - defensive fallback
        if errors is not None:
            errors.append(
                f"{' '.join(command)} failed: {type(exc).__name__}: {exc}"
            )
        return ""
    stdout = getattr(completed, "stdout", "")
    if stdout is None:
        return ""
    return str(stdout).strip()


def _parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    normalized = value.strip()
    if not normalized:
        return None
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _git_rev_parse(
    repo_root: Path,
    ref: str,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> str:
    return _run_command_stdout(
        ["git", "rev-parse", "--verify", ref],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )


def _git_commit_timestamp(
    repo_root: Path,
    commit: str,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> datetime | None:
    output = _run_command_stdout(
        ["git", "show", "-s", "--format=%cI", commit],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )
    return _parse_datetime(output)


def _git_head(
    repo_root: Path,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> str:
    return _run_command_stdout(
        ["git", "rev-parse", "HEAD"],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )


def _inspect_compose_container(
    service: str,
    *,
    compose_prefix: list[str],
    repo_root: Path,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> dict[str, Any]:
    container_id = _run_command_stdout(
        [*compose_prefix, "ps", "-q", service],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )
    if not container_id:
        return {
            "service": service,
            "container_id": None,
            "container_image_id": None,
            "container_created_at": None,
            "runtime_commit_source": "unavailable",
            "runtime_commit": None,
            "runtime_version": None,
            "runtime_commit_candidates": [],
            "runtime_version_candidates": [],
            "container_rebuilt_after_expected_commit_timestamp": None,
        }

    inspect_raw = _run_command_stdout(
        ["docker", "inspect", container_id],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )
    try:
        inspect_payload = json.loads(inspect_raw or "[]")
    except json.JSONDecodeError as exc:  # pragma: no cover - defensive fallback
        if errors is not None:
            errors.append(
                f"docker inspect for {service} returned invalid JSON: {exc}"
            )
        inspect_payload = []
    if not inspect_payload:
        return {
            "service": service,
            "container_id": container_id,
            "container_image_id": None,
            "container_created_at": None,
            "runtime_commit_source": "unavailable",
            "runtime_commit": None,
            "runtime_version": None,
            "runtime_commit_candidates": [],
            "runtime_version_candidates": [],
            "container_rebuilt_after_expected_commit_timestamp": None,
        }
    container = inspect_payload[0]
    image_id = str(container.get("Image") or "")
    created_at = str(container.get("Created") or "")

    return {
        "service": service,
        "container_id": str(container.get("Id") or container_id),
        "container_image_id": image_id or None,
        "container_created_at": created_at or None,
        "runtime_commit_source": "unavailable",
        "runtime_commit": None,
        "runtime_version": None,
        "runtime_commit_candidates": [],
        "runtime_version_candidates": [],
        "container_rebuilt_after_expected_commit_timestamp": None,
    }


def _walk_markers(
    value: Any,
    *,
    path: str = "",
) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            next_path = f"{path}.{key}" if path else key
            if _MARKER_KEY_RE.search(key) and isinstance(
                nested, (str, int, float)
            ):
                markers.append(
                    {
                        "path": next_path,
                        "key": str(key),
                        "value": str(nested),
                    }
                )
            markers.extend(_walk_markers(nested, path=next_path))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            markers.extend(_walk_markers(item, path=f"{path}[{index}]"))
    return markers


def _extract_runtime_identity(
    payloads: list[dict[str, Any]],
    logs: str | None,
) -> dict[str, Any]:
    endpoint_markers: list[dict[str, str]] = []
    for payload in payloads:
        endpoint_markers.extend(_walk_markers(payload))

    log_markers: list[dict[str, str]] = []
    if logs:
        for line in logs.splitlines():
            lowered = line.lower()
            if not _MARKER_KEY_RE.search(lowered):
                continue
            matches = _HASH_EXTRACT_RE.findall(line)
            if matches:
                for match in matches:
                    log_markers.append(
                        {
                            "path": "logs",
                            "key": "commit",
                            "value": match,
                        }
                    )
            else:
                version_matches = _VERSION_EXTRACT_RE.findall(line)
                if version_matches:
                    for match in version_matches:
                        log_markers.append(
                            {
                                "path": "logs",
                                "key": "version",
                                "value": match,
                            }
                        )

    def pick_commit(markers: list[dict[str, str]]) -> str | None:
        for marker in markers:
            value = marker.get("value", "")
            key = marker.get("key", "").lower()
            if ("commit" in key or "sha" in key) and _HASH_RE.match(value):
                return value
        return None

    def pick_version(markers: list[dict[str, str]]) -> str | None:
        for marker in markers:
            value = marker.get("value", "")
            key = marker.get("key", "").lower()
            if "version" in key or "revision" in key:
                return value
        return None

    endpoint_commit = pick_commit(endpoint_markers)
    endpoint_version = pick_version(endpoint_markers)
    log_commit = pick_commit(log_markers)
    log_version = pick_version(log_markers)

    runtime_commit_source = "unavailable"
    runtime_commit = None
    runtime_version = None
    runtime_commit_candidates = endpoint_markers if endpoint_markers else []
    runtime_version_candidates = endpoint_markers if endpoint_markers else []

    if endpoint_commit:
        runtime_commit_source = "endpoint"
        runtime_commit = endpoint_commit
    elif endpoint_version:
        runtime_commit_source = "endpoint"
        runtime_version = endpoint_version
    elif log_commit:
        runtime_commit_source = "logs"
        runtime_commit = log_commit
    elif log_version:
        runtime_commit_source = "logs"
        runtime_version = log_version

    return {
        "runtime_commit_source": runtime_commit_source,
        "runtime_commit": runtime_commit,
        "runtime_version": runtime_version,
        "runtime_commit_candidates": endpoint_markers + log_markers,
        "runtime_version_candidates": endpoint_markers + log_markers,
        "endpoint_commit": endpoint_commit,
        "endpoint_version": endpoint_version,
        "log_commit": log_commit,
        "log_version": log_version,
    }


def _collect_service_provenance(
    service: str,
    *,
    compose_prefix: list[str],
    repo_root: Path,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
    endpoint_payloads: list[dict[str, Any]],
    logs: str | None,
    expected_commit_timestamp: datetime | None,
) -> dict[str, Any]:
    service_info = _inspect_compose_container(
        service,
        compose_prefix=compose_prefix,
        repo_root=repo_root,
        run_command=run_command,
        errors=errors,
    )
    runtime_identity = _extract_runtime_identity(endpoint_payloads, logs)
    created_at = _parse_datetime(service_info.get("container_created_at"))

    container_rebuilt_after_expected_commit_timestamp = None
    if expected_commit_timestamp is not None and created_at is not None:
        container_rebuilt_after_expected_commit_timestamp = (
            created_at >= expected_commit_timestamp
        )

    service_info.update(runtime_identity)
    service_info["container_created_at"] = service_info.get(
        "container_created_at"
    )
    service_info["container_created_at_parsed"] = (
        created_at.isoformat() if created_at is not None else None
    )
    service_info["container_rebuilt_after_expected_commit_timestamp"] = (
        container_rebuilt_after_expected_commit_timestamp
    )
    return service_info


def _worker_heartbeat_ok(health_chat: dict[str, Any]) -> tuple[bool, str]:
    worker = health_chat.get("worker") or {}
    completion_service = health_chat.get("completion_service") or {}
    age = worker.get("heartbeat_age_seconds")
    if age is None:
        age = completion_service.get("worker_heartbeat_age_seconds")
    if worker.get("status") != "fresh":
        return False, "worker.status not fresh"
    if completion_service.get("worker_heartbeat_status") != "fresh":
        return False, "completion_service.worker_heartbeat_status not fresh"
    if not isinstance(age, (int, float)):
        return False, "worker heartbeat age missing"
    if float(age) > FRESH_HEARTBEAT_THRESHOLD_SECONDS:
        return False, f"worker heartbeat stale ({age})"
    return True, "worker heartbeat fresh"


def _health_ok(
    name: str,
    payload: dict[str, Any],
    *,
    required_status: str,
) -> tuple[bool, str]:
    status_code = payload.get("status_code")
    body = payload.get("body") or {}
    if status_code != 200:
        return False, f"{name} returned {status_code}"
    if body.get("status") != required_status:
        return False, f"{name} status {body.get('status')!r} != {required_status!r}"
    return True, f"{name} healthy"


def collect_runtime_provenance(
    expected_commit: str,
    *,
    base_url: str = "http://127.0.0.1:8888",
    backend_service: str = "backend",
    worker_service: str = "worker-chat",
    compose_file: str | None = None,
    compose_project: str | None = None,
    repo_root: Path | None = None,
    run_command: Callable[..., subprocess.CompletedProcess[str]] | None = None,
    http_get: Callable[..., Any] | None = None,
) -> dict[str, Any]:
    repo_root = repo_root or Path(__file__).resolve().parents[2]
    run_command = run_command or _run_command
    http_get = http_get or requests.get
    compose_prefix = _compose_prefix(
        compose_file=compose_file,
        compose_project=compose_project,
    )

    errors: list[str] = []
    health_paths = ["/health", "/health/chat", "/api/health/llm", "/api/llm/catalog"]
    health_payloads: dict[str, dict[str, Any]] = {
        path: _json_response(
            f"{base_url}{path}",
            timeout=30.0,
            http_get=http_get,
            errors=errors,
        )
        for path in health_paths
    }

    checks: list[dict[str, Any]] = []

    local_head = _git_head(repo_root, run_command=run_command, errors=errors)
    expected_commit_resolved = _git_rev_parse(
        repo_root,
        expected_commit,
        run_command=run_command,
        errors=errors,
    )
    expected_commit_timestamp = _git_commit_timestamp(
        repo_root,
        expected_commit_resolved,
        run_command=run_command,
        errors=errors,
    )

    backend_endpoint_payloads = [
        health_payloads["/health"],
        health_payloads["/health/chat"],
        health_payloads["/api/health/llm"],
        health_payloads["/api/llm/catalog"],
    ]
    worker_endpoint_payloads = [
        health_payloads["/health/chat"],
    ]

    backend_logs = _run_command_stdout(
        [*compose_prefix, "logs", "--no-color", "--tail", "200", backend_service],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )
    worker_logs = _run_command_stdout(
        [*compose_prefix, "logs", "--no-color", "--tail", "200", worker_service],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )

    backend = _collect_service_provenance(
        backend_service,
        compose_prefix=compose_prefix,
        repo_root=repo_root,
        run_command=run_command,
        errors=errors,
        endpoint_payloads=backend_endpoint_payloads,
        logs=backend_logs,
        expected_commit_timestamp=expected_commit_timestamp,
    )
    worker = _collect_service_provenance(
        worker_service,
        compose_prefix=compose_prefix,
        repo_root=repo_root,
        run_command=run_command,
        errors=errors,
        endpoint_payloads=worker_endpoint_payloads,
        logs=worker_logs,
        expected_commit_timestamp=expected_commit_timestamp,
    )

    # Top-level runtime_commit_source is endpoint-based only.
    runtime_commit_source = (
        "endpoint"
        if backend.get("runtime_commit_source") == "endpoint"
        or worker.get("runtime_commit_source") == "endpoint"
        else "unavailable"
    )

    backend_health_ok, backend_health_reason = _health_ok(
        "GET /health", health_payloads["/health"], required_status="ok"
    )
    worker_health_ok, worker_health_reason = _health_ok(
        "GET /health/chat", health_payloads["/health/chat"], required_status="healthy"
    )
    llm_health_ok, llm_health_reason = _health_ok(
        "GET /api/health/llm",
        health_payloads["/api/health/llm"],
        required_status="ok",
    )
    catalog_payload = health_payloads["/api/llm/catalog"]
    catalog_ok = catalog_payload.get("status_code") == 200
    catalog_reason = (
        "GET /api/llm/catalog healthy"
        if catalog_ok
        else f"GET /api/llm/catalog returned {catalog_payload.get('status_code')}"
    )

    heartbeat_ok, heartbeat_reason = _worker_heartbeat_ok(
        health_payloads["/health/chat"].get("body") or {}
    )

    if local_head != expected_commit_resolved:
        errors.append(
            f"local HEAD {local_head} does not match expected commit {expected_commit_resolved}"
        )
    if not backend_health_ok:
        errors.append(backend_health_reason)
    if not worker_health_ok:
        errors.append(worker_health_reason)
    if not llm_health_ok:
        errors.append(llm_health_reason)
    if not catalog_ok:
        errors.append(catalog_reason)
    if not heartbeat_ok:
        errors.append(heartbeat_reason)

    if expected_commit_timestamp is not None:
        for service_name, service_info in (
            (backend_service, backend),
            (worker_service, worker),
        ):
            rebuilt = service_info.get(
                "container_rebuilt_after_expected_commit_timestamp"
            )
            if rebuilt is False:
                errors.append(
                    f"{service_name} container was created before expected commit timestamp"
                )
            elif rebuilt is None:
                errors.append(
                    f"{service_name} container creation time unavailable"
                )

    for service_name, service_info in (
        (backend_service, backend),
        (worker_service, worker),
    ):
        runtime_commit = service_info.get("runtime_commit")
        if (
            isinstance(runtime_commit, str)
            and _HASH_RE.match(runtime_commit)
            and runtime_commit != expected_commit_resolved
        ):
            errors.append(
                f"{service_name} runtime commit {runtime_commit} does not match expected {expected_commit_resolved}"
            )

    checks.extend(
        [
            {
                "name": "local_git_head_matches_expected",
                "ok": local_head == expected_commit_resolved,
                "detail": (
                    "match"
                    if local_head == expected_commit_resolved
                    else f"local HEAD {local_head} != expected {expected_commit_resolved}"
                ),
            },
            {
                "name": "backend_health_green",
                "ok": backend_health_ok,
                "detail": backend_health_reason,
            },
            {
                "name": "worker_health_green",
                "ok": worker_health_ok,
                "detail": worker_health_reason,
            },
            {
                "name": "llm_health_green",
                "ok": llm_health_ok,
                "detail": llm_health_reason,
            },
            {
                "name": "catalog_available",
                "ok": catalog_ok,
                "detail": catalog_reason,
            },
            {
                "name": "worker_heartbeat_fresh",
                "ok": heartbeat_ok,
                "detail": heartbeat_reason,
            },
            {
                "name": "backend_container_rebuilt_after_expected_commit",
                "ok": backend.get(
                    "container_rebuilt_after_expected_commit_timestamp"
                )
                is True,
                "detail": str(
                    backend.get("container_rebuilt_after_expected_commit_timestamp")
                ),
            },
            {
                "name": "worker_container_rebuilt_after_expected_commit",
                "ok": worker.get(
                    "container_rebuilt_after_expected_commit_timestamp"
                )
                is True,
                "detail": str(
                    worker.get("container_rebuilt_after_expected_commit_timestamp")
                ),
            },
        ]
    )

    proof_ready = not errors
    report = {
        "ok": proof_ready,
        "proof_ready": proof_ready,
        "expected_commit": expected_commit,
        "expected_commit_resolved": expected_commit_resolved,
        "expected_commit_timestamp": (
            expected_commit_timestamp.isoformat()
            if expected_commit_timestamp is not None
            else None
        ),
        "local_git_head": local_head,
        "local_git_head_short": local_head[:8] if local_head else None,
        "runtime_commit_source": runtime_commit_source,
        "backend": backend,
        "worker": worker,
        "health": health_payloads,
        "checks": checks,
        "errors": errors,
    }
    return report


def _format_human_report(report: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append("Runtime provenance check")
    lines.append(f"  proof_ready: {report.get('proof_ready')}")
    lines.append(f"  expected_commit: {report.get('expected_commit')}")
    lines.append(f"  local_git_head: {report.get('local_git_head')}")
    lines.append(
        "  expected_commit_timestamp: "
        f"{report.get('expected_commit_timestamp') or 'unavailable'}"
    )
    lines.append(
        "  runtime_commit_source: "
        f"{report.get('runtime_commit_source')}"
    )
    for service_name in ("backend", "worker"):
        service = report.get(service_name) or {}
        lines.append(f"  {service_name}:")
        lines.append(f"    container_id: {service.get('container_id')}")
        lines.append(f"    container_image_id: {service.get('container_image_id')}")
        lines.append(
            "    container_created_at: "
            f"{service.get('container_created_at')}"
        )
        lines.append(
            "    runtime_commit_source: "
            f"{service.get('runtime_commit_source')}"
        )
        lines.append(f"    runtime_commit: {service.get('runtime_commit')}")
        lines.append(f"    runtime_version: {service.get('runtime_version')}")
        lines.append(
            "    rebuilt_after_expected_commit_timestamp: "
            f"{service.get('container_rebuilt_after_expected_commit_timestamp')}"
        )
    lines.append("  health:")
    for path, payload in (report.get("health") or {}).items():
        body = payload.get("body") or {}
        lines.append(
            f"    {path}: status_code={payload.get('status_code')} "
            f"status={body.get('status')}"
        )
    if report.get("checks"):
        lines.append("  checks:")
        for check in report["checks"]:
            lines.append(
                f"    - {check.get('name')}: {check.get('ok')} ({check.get('detail')})"
            )
    if report.get("errors"):
        lines.append("  errors:")
        for error in report["errors"]:
            lines.append(f"    - {error}")
    return "\n".join(lines)


def emit_report(report: dict[str, Any]) -> None:
    print(_format_human_report(report), file=sys.stderr)
    print(json.dumps(report, indent=2, sort_keys=True))


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the live image-turn containment proof is running on the "
            "expected runtime provenance."
        )
    )
    parser.add_argument(
        "--expected-commit",
        required=True,
        help="Expected git commit hash for the runtime under proof.",
    )
    parser.add_argument(
        "--base-url",
        default=os.getenv("PROOF_BASE_URL", "http://127.0.0.1:8888"),
        help="Backend base URL used to query health surfaces.",
    )
    parser.add_argument(
        "--backend-service",
        default="backend",
        help="Docker Compose service name for the backend container.",
    )
    parser.add_argument(
        "--worker-service",
        default="worker-chat",
        help="Docker Compose service name for the chat worker container.",
    )
    parser.add_argument(
        "--compose-file",
        default=os.getenv("PROOF_COMPOSE_FILE"),
        help="Optional docker compose file used to locate the live services.",
    )
    parser.add_argument(
        "--compose-project",
        default=os.getenv("COMPOSE_PROJECT_NAME"),
        help="Optional compose project name for the live services.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    report = collect_runtime_provenance(
        args.expected_commit,
        base_url=args.base_url,
        backend_service=args.backend_service,
        worker_service=args.worker_service,
        compose_file=args.compose_file,
        compose_project=args.compose_project,
    )
    emit_report(report)
    return 0 if report.get("proof_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
