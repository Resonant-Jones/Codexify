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

REQUIRED_IMAGE_ROUTING_FIX_COMMIT = "2bce6aeb9416a25d77b931b4974db7573e8951b8"

RUNTIME_COMMIT_SOURCE_AUTHORITATIVE = "authoritative_runtime_commit"
RUNTIME_COMMIT_SOURCE_BUILD_METADATA = "build_metadata_commit"
RUNTIME_COMMIT_SOURCE_LOG_HINT = "log_hint_commit"
RUNTIME_COMMIT_SOURCE_UNAVAILABLE = "unavailable"
RUNTIME_COMMIT_SOURCE_UNTRUSTED = "untrusted"

_RUNTIME_SOURCE_PRIORITY = {
    RUNTIME_COMMIT_SOURCE_UNAVAILABLE: 0,
    RUNTIME_COMMIT_SOURCE_UNTRUSTED: 1,
    RUNTIME_COMMIT_SOURCE_LOG_HINT: 2,
    RUNTIME_COMMIT_SOURCE_BUILD_METADATA: 3,
    RUNTIME_COMMIT_SOURCE_AUTHORITATIVE: 4,
}

_MARKER_KEY_RE = re.compile(r"(commit|sha|version|revision)", re.IGNORECASE)
_UNTRUSTED_LOG_MARKER_RE = re.compile(
    r"(alembic[_-]?version|migration[_-]?revision)",
    re.IGNORECASE,
)
_LOG_KEYED_HASH_RE = re.compile(
    r"(?P<key>commit|sha|revision|alembic[_-]?version)\s*[:=]\s*(?P<value>[0-9a-f]{7,40})",
    re.IGNORECASE,
)
_LOG_KEYED_VERSION_RE = re.compile(
    r"(?P<key>version|revision)\s*[:=]\s*(?P<value>[0-9A-Za-z._-]+)",
    re.IGNORECASE,
)
_HASH_RE = re.compile(r"^[0-9a-f]{7,40}$", re.IGNORECASE)
_HASH_EXTRACT_RE = re.compile(r"\b[0-9a-f]{7,40}\b", re.IGNORECASE)


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


def _git_is_ancestor(
    repo_root: Path,
    ancestor: str,
    descendant: str,
    *,
    run_command: Callable[..., subprocess.CompletedProcess[str]],
    errors: list[str] | None = None,
) -> bool | None:
    command = ["git", "merge-base", "--is-ancestor", ancestor, descendant]
    try:
        run_command(
            command,
            cwd=repo_root,
            timeout=30,
            capture_output=True,
            text=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError as exc:
        if exc.returncode == 1:
            return False
        if errors is not None:
            errors.append(
                f"{' '.join(command)} failed: CalledProcessError: {exc}"
            )
        return None
    except Exception as exc:  # pragma: no cover - defensive fallback
        if errors is not None:
            errors.append(
                f"{' '.join(command)} failed: {type(exc).__name__}: {exc}"
            )
        return None


def _combined_runtime_commit_source(services: list[dict[str, Any]]) -> str:
    best_source = RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    best_priority = _RUNTIME_SOURCE_PRIORITY[best_source]
    for service in services:
        source = str(service.get("runtime_commit_source") or "")
        priority = _RUNTIME_SOURCE_PRIORITY.get(
            source, _RUNTIME_SOURCE_PRIORITY[RUNTIME_COMMIT_SOURCE_UNAVAILABLE]
        )
        if priority > best_priority:
            best_priority = priority
            best_source = source
    return best_source


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
            "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
            "runtime_commit": None,
            "runtime_version": None,
            "runtime_commit_candidates": [],
            "runtime_version_candidates": [],
            "build_metadata_commit": None,
            "build_metadata_version": None,
            "build_metadata_candidates": [],
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
            "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
            "runtime_commit": None,
            "runtime_version": None,
            "runtime_commit_candidates": [],
            "runtime_version_candidates": [],
            "build_metadata_commit": None,
            "build_metadata_version": None,
            "build_metadata_candidates": [],
            "container_rebuilt_after_expected_commit_timestamp": None,
        }
    container = inspect_payload[0]
    image_id = str(container.get("Image") or "")
    created_at = str(container.get("Created") or "")
    labels = container.get("Config", {}).get("Labels", {}) or {}
    build_metadata_candidates: list[dict[str, str]] = []
    for key, value in labels.items():
        value_text = str(value)
        key_text = str(key)
        lower_key = key_text.lower()
        marker_path = f"container.labels.{key_text}"
        if _MARKER_KEY_RE.search(lower_key):
            build_metadata_candidates.append(
                {"path": marker_path, "key": key_text, "value": value_text}
            )

    build_metadata_commit = None
    build_metadata_version = None
    for marker in build_metadata_candidates:
        key = marker.get("key", "").lower()
        value = marker.get("value", "")
        if ("commit" in key or "sha" in key) and _HASH_RE.match(value):
            build_metadata_commit = value
            break
    if build_metadata_commit is None:
        for marker in build_metadata_candidates:
            key = marker.get("key", "").lower()
            value = marker.get("value", "")
            if "version" in key or "revision" in key:
                build_metadata_version = value
                break

    return {
        "service": service,
        "container_id": str(container.get("Id") or container_id),
        "container_image_id": image_id or None,
        "container_created_at": created_at or None,
        "runtime_commit_source": RUNTIME_COMMIT_SOURCE_UNAVAILABLE,
        "runtime_commit": None,
        "runtime_version": None,
        "runtime_commit_candidates": [],
        "runtime_version_candidates": [],
        "build_metadata_commit": build_metadata_commit,
        "build_metadata_version": build_metadata_version,
        "build_metadata_candidates": build_metadata_candidates,
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


def _extract_log_markers(logs: str | None) -> list[dict[str, str]]:
    markers: list[dict[str, str]] = []
    if not logs:
        return markers

    for line in logs.splitlines():
        lowered = line.lower()
        if not _MARKER_KEY_RE.search(lowered):
            continue

        keyed_hash_matches = list(_LOG_KEYED_HASH_RE.finditer(line))
        if keyed_hash_matches:
            for match in keyed_hash_matches:
                key = match.group("key")
                value = match.group("value")
                source_class = (
                    RUNTIME_COMMIT_SOURCE_UNTRUSTED
                    if _UNTRUSTED_LOG_MARKER_RE.search(key)
                    else RUNTIME_COMMIT_SOURCE_LOG_HINT
                )
                markers.append(
                    {
                        "path": "logs",
                        "key": key,
                        "value": value,
                        "source_class": source_class,
                    }
                )
            continue

        keyed_version_matches = list(_LOG_KEYED_VERSION_RE.finditer(line))
        if keyed_version_matches:
            for match in keyed_version_matches:
                markers.append(
                    {
                        "path": "logs",
                        "key": match.group("key"),
                        "value": match.group("value"),
                        "source_class": RUNTIME_COMMIT_SOURCE_UNTRUSTED,
                    }
                )
            continue

        for hash_match in _HASH_EXTRACT_RE.findall(line):
            markers.append(
                {
                    "path": "logs",
                    "key": "hash_hint",
                    "value": hash_match,
                    "source_class": RUNTIME_COMMIT_SOURCE_UNTRUSTED,
                }
            )

    return markers


def _pick_authoritative_endpoint_commit(
    endpoint_markers: list[dict[str, str]],
) -> tuple[str | None, dict[str, str] | None]:
    for marker in endpoint_markers:
        value = marker.get("value", "")
        key = marker.get("key", "").lower()
        if ("commit" in key or "sha" in key) and _HASH_RE.match(value):
            return value, marker
    return None, None


def _pick_endpoint_build_metadata(
    endpoint_markers: list[dict[str, str]],
) -> tuple[str | None, str | None]:
    build_commit = None
    build_version = None
    for marker in endpoint_markers:
        value = marker.get("value", "")
        key = marker.get("key", "").lower()
        if build_commit is None and (
            ("revision" in key or "version" in key) and _HASH_RE.match(value)
        ):
            build_commit = value
        if build_version is None and (
            ("version" in key or "revision" in key)
            and ("build" in key or "runtime" in key or "image" in key)
        ):
            build_version = value
        if build_commit is not None and build_version is not None:
            break
    return build_commit, build_version


def _pick_log_runtime_hints(
    log_markers: list[dict[str, str]],
) -> tuple[str | None, str | None]:
    log_hint_commit = None
    untrusted_commit = None
    for marker in log_markers:
        value = marker.get("value", "")
        source_class = marker.get("source_class")
        if not _HASH_RE.match(value):
            continue
        if (
            log_hint_commit is None
            and source_class == RUNTIME_COMMIT_SOURCE_LOG_HINT
        ):
            log_hint_commit = value
        if (
            untrusted_commit is None
            and source_class == RUNTIME_COMMIT_SOURCE_UNTRUSTED
        ):
            untrusted_commit = value
        if log_hint_commit is not None and untrusted_commit is not None:
            break
    return log_hint_commit, untrusted_commit


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
    endpoint_markers: list[dict[str, str]] = []
    for payload in endpoint_payloads:
        endpoint_markers.extend(_walk_markers(payload))
    log_markers = _extract_log_markers(logs)
    build_metadata_candidates = list(
        service_info.get("build_metadata_candidates") or []
    )

    (
        authoritative_runtime_commit,
        authoritative_runtime_marker,
    ) = _pick_authoritative_endpoint_commit(endpoint_markers)
    (
        endpoint_build_metadata_commit,
        endpoint_build_metadata_version,
    ) = _pick_endpoint_build_metadata(endpoint_markers)
    build_metadata_commit = service_info.get("build_metadata_commit")
    if not build_metadata_commit:
        build_metadata_commit = endpoint_build_metadata_commit
    build_metadata_version = service_info.get("build_metadata_version")
    if not build_metadata_version:
        build_metadata_version = endpoint_build_metadata_version

    log_hint_commit, untrusted_log_commit = _pick_log_runtime_hints(log_markers)

    runtime_commit_source = RUNTIME_COMMIT_SOURCE_UNAVAILABLE
    runtime_commit = None
    runtime_version = None

    if authoritative_runtime_commit:
        runtime_commit_source = RUNTIME_COMMIT_SOURCE_AUTHORITATIVE
        runtime_commit = authoritative_runtime_commit
    elif build_metadata_commit:
        runtime_commit_source = RUNTIME_COMMIT_SOURCE_BUILD_METADATA
        runtime_commit = str(build_metadata_commit)
    elif log_hint_commit:
        runtime_commit_source = RUNTIME_COMMIT_SOURCE_LOG_HINT
        runtime_commit = log_hint_commit
    elif untrusted_log_commit:
        runtime_commit_source = RUNTIME_COMMIT_SOURCE_UNTRUSTED
        runtime_commit = untrusted_log_commit
    elif log_markers:
        runtime_commit_source = RUNTIME_COMMIT_SOURCE_UNTRUSTED

    if runtime_version is None:
        if build_metadata_version:
            runtime_version = str(build_metadata_version)
        else:
            for marker in endpoint_markers + log_markers:
                key = marker.get("key", "").lower()
                value = marker.get("value", "")
                if "version" in key or "revision" in key:
                    runtime_version = value
                    break

    runtime_identity = {
        "runtime_commit_source": runtime_commit_source,
        "runtime_commit": runtime_commit,
        "runtime_version": runtime_version,
        "runtime_commit_candidates": endpoint_markers
        + build_metadata_candidates
        + log_markers,
        "runtime_version_candidates": endpoint_markers
        + build_metadata_candidates
        + log_markers,
        "authoritative_runtime_commit": authoritative_runtime_commit,
        "authoritative_runtime_commit_marker": authoritative_runtime_marker,
        "build_metadata_commit": build_metadata_commit,
        "build_metadata_version": build_metadata_version,
        "log_hint_commit": log_hint_commit,
        "untrusted_log_hint_commit": untrusted_log_commit,
    }
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
    service_info[
        "container_rebuilt_after_expected_commit_timestamp"
    ] = container_rebuilt_after_expected_commit_timestamp
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
        return (
            False,
            f"{name} status {body.get('status')!r} != {required_status!r}",
        )
    return True, f"{name} healthy"


def collect_runtime_provenance(
    expected_commit: str,
    *,
    base_url: str = "http://127.0.0.1:8888",
    backend_service: str = "backend",
    worker_service: str = "worker-chat",
    compose_file: str | None = None,
    compose_project: str | None = None,
    required_lineage_commit: str | None = REQUIRED_IMAGE_ROUTING_FIX_COMMIT,
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
    warnings: list[str] = []
    health_paths = [
        "/health",
        "/health/chat",
        "/api/health/llm",
        "/api/llm/catalog",
    ]
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
    required_lineage_commit_resolved = None
    local_head_contains_required_lineage_commit: bool | None = None
    if required_lineage_commit:
        required_lineage_commit_resolved = _git_rev_parse(
            repo_root,
            required_lineage_commit,
            run_command=run_command,
            errors=errors,
        )
        if required_lineage_commit_resolved:
            local_head_contains_required_lineage_commit = _git_is_ancestor(
                repo_root,
                required_lineage_commit_resolved,
                local_head,
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
        [
            *compose_prefix,
            "logs",
            "--no-color",
            "--tail",
            "200",
            backend_service,
        ],
        cwd=repo_root,
        run_command=run_command,
        errors=errors,
    )
    worker_logs = _run_command_stdout(
        [
            *compose_prefix,
            "logs",
            "--no-color",
            "--tail",
            "200",
            worker_service,
        ],
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

    runtime_commit_source = _combined_runtime_commit_source([backend, worker])

    backend_health_ok, backend_health_reason = _health_ok(
        "GET /health", health_payloads["/health"], required_status="ok"
    )
    worker_health_ok, worker_health_reason = _health_ok(
        "GET /health/chat",
        health_payloads["/health/chat"],
        required_status="healthy",
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
    if required_lineage_commit and required_lineage_commit_resolved:
        if local_head_contains_required_lineage_commit is False:
            errors.append(
                "local HEAD "
                f"{local_head} does not contain required lineage commit "
                f"{required_lineage_commit_resolved}"
            )
        elif local_head_contains_required_lineage_commit is None:
            errors.append(
                "unable to verify required lineage commit containment: "
                f"{required_lineage_commit_resolved}"
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
        runtime_commit_source_class = service_info.get("runtime_commit_source")
        runtime_commit = service_info.get("runtime_commit")
        if (
            runtime_commit_source_class == RUNTIME_COMMIT_SOURCE_AUTHORITATIVE
            and isinstance(runtime_commit, str)
            and _HASH_RE.match(runtime_commit)
            and runtime_commit != expected_commit_resolved
        ):
            errors.append(
                f"{service_name} authoritative runtime commit {runtime_commit} does not match expected {expected_commit_resolved}"
            )
        elif (
            isinstance(runtime_commit, str)
            and _HASH_RE.match(runtime_commit)
            and runtime_commit != expected_commit_resolved
            and runtime_commit_source_class
            in (
                RUNTIME_COMMIT_SOURCE_BUILD_METADATA,
                RUNTIME_COMMIT_SOURCE_LOG_HINT,
                RUNTIME_COMMIT_SOURCE_UNTRUSTED,
            )
        ):
            warnings.append(
                f"{service_name} runtime commit hint {runtime_commit} "
                f"({runtime_commit_source_class}) does not match expected {expected_commit_resolved}"
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
                "name": "local_head_contains_required_lineage_commit",
                "ok": (
                    local_head_contains_required_lineage_commit is True
                    if required_lineage_commit_resolved
                    else True
                ),
                "detail": (
                    "required lineage check disabled"
                    if not required_lineage_commit
                    else (
                        "required fix commit present in local HEAD"
                        if local_head_contains_required_lineage_commit is True
                        else (
                            f"local HEAD {local_head} does not contain {required_lineage_commit_resolved}"
                            if local_head_contains_required_lineage_commit
                            is False
                            else "required lineage check unavailable"
                        )
                    )
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
                    backend.get(
                        "container_rebuilt_after_expected_commit_timestamp"
                    )
                ),
            },
            {
                "name": "worker_container_rebuilt_after_expected_commit",
                "ok": worker.get(
                    "container_rebuilt_after_expected_commit_timestamp"
                )
                is True,
                "detail": str(
                    worker.get(
                        "container_rebuilt_after_expected_commit_timestamp"
                    )
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
        "required_lineage_commit": required_lineage_commit,
        "required_lineage_commit_resolved": required_lineage_commit_resolved,
        "local_head_contains_required_lineage_commit": (
            local_head_contains_required_lineage_commit
        ),
        "runtime_commit_source": runtime_commit_source,
        "backend": backend,
        "worker": worker,
        "health": health_payloads,
        "checks": checks,
        "warnings": warnings,
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
        "  required_lineage_commit: "
        f"{report.get('required_lineage_commit') or 'disabled'}"
    )
    lines.append(
        "  local_head_contains_required_lineage_commit: "
        f"{report.get('local_head_contains_required_lineage_commit')}"
    )
    lines.append(
        "  expected_commit_timestamp: "
        f"{report.get('expected_commit_timestamp') or 'unavailable'}"
    )
    lines.append(
        "  runtime_commit_source: " f"{report.get('runtime_commit_source')}"
    )
    for service_name in ("backend", "worker"):
        service = report.get(service_name) or {}
        lines.append(f"  {service_name}:")
        lines.append(f"    container_id: {service.get('container_id')}")
        lines.append(
            f"    container_image_id: {service.get('container_image_id')}"
        )
        lines.append(
            "    container_created_at: "
            f"{service.get('container_created_at')}"
        )
        lines.append(
            "    runtime_commit_source: "
            f"{service.get('runtime_commit_source')}"
        )
        lines.append(f"    runtime_commit: {service.get('runtime_commit')}")
        lines.append(
            "    authoritative_runtime_commit: "
            f"{service.get('authoritative_runtime_commit')}"
        )
        lines.append(
            "    build_metadata_commit: "
            f"{service.get('build_metadata_commit')}"
        )
        lines.append(
            "    log_hint_commit: " f"{service.get('log_hint_commit')}"
        )
        lines.append(
            "    untrusted_log_hint_commit: "
            f"{service.get('untrusted_log_hint_commit')}"
        )
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
    if report.get("warnings"):
        lines.append("  warnings:")
        for warning in report["warnings"]:
            lines.append(f"    - {warning}")
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
    parser.add_argument(
        "--required-lineage-commit",
        default=REQUIRED_IMAGE_ROUTING_FIX_COMMIT,
        help=(
            "Commit that local HEAD must contain before proof-ready can be true. "
            "Set empty string to disable."
        ),
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
        required_lineage_commit=args.required_lineage_commit or None,
    )
    emit_report(report)
    return 0 if report.get("proof_ready") else 1


if __name__ == "__main__":
    raise SystemExit(main())
