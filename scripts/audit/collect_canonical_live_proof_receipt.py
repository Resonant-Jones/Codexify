#!/usr/bin/env python3
"""Collect one bounded, read-only supported-Compose live proof receipt.

The collector observes an explicitly selected, already-running Compose project.
It does not mutate Docker, execute inside containers, generate canonical evidence,
store proof, or promote a trusted pointer.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker

_SOURCE_ROOT = Path(__file__).resolve().parents[2]
if str(_SOURCE_ROOT) not in sys.path:
    sys.path.insert(0, str(_SOURCE_ROOT))

from scripts.audit.collect_canonical_evidence_identity import (  # noqa: E402
    CollectorError,
    collect_identity,
)
from scripts.audit.collect_canonical_runtime_identity import (  # noqa: E402
    RuntimeIdentityError,
    collect_runtime_identity,
)

RESULT_SCHEMA_VERSION = "canonical_live_proof_receipt_result.v1"
COLLECTOR_VERSION = "canonical_live_proof_receipt_collector.v1"
RECEIPT_SCHEMA_VERSION = "canonical_live_proof_receipt.v1"
SUITE_ID = "supported_compose_live_health.v1"
PROOF_CLASS = "CURRENT_LIVE_PROOF"
DEFAULT_PROFILE_NAME = "v1-local-core-web-mcp"
DEFAULT_SCHEMA_PATH = (
    _SOURCE_ROOT / "schemas/audit/canonical-live-proof-receipt.schema.json"
)
DEFAULT_COMMAND_TIMEOUT_SECONDS = 10.0
DEFAULT_HTTP_TIMEOUT_SECONDS = 5.0
MAX_DOCKER_OUTPUT_BYTES = 1024 * 1024
MAX_HTTP_BODY_BYTES = 1024 * 1024
PROJECT_NAME_RE = re.compile(r"^[a-z0-9][a-z0-9_-]*$")
SAFE_TEXT_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:@ /-]{0,239}$")
IMAGE_ID_RE = re.compile(r"^(?:sha256:)?[0-9a-f]{12,64}$")
DIGEST_RE = re.compile(r"^sha256:[0-9a-f]{64}$")
SECRET_RE = re.compile(
    r"(?i)(password|secret|token|api[_-]?key|private[_-]?key|credential|"
    r"database[_-]?url|postgres(?:ql)?://|mysql://|redis://|rediss://|"
    r"[a-z][a-z0-9+.-]*://[^\s/@]+:[^\s/@]+@)"
)
ONE_SHOT_SERVICES = frozenset({"migrator", "graph-init", "model-prep"})
HEALTHY_STATUSES = frozenset({"healthy", "ok", "online", "ready", "up"})
PROBE_DEFINITIONS = (
    ("api_ping", "/ping", "api"),
    ("api_health", "/health", "api"),
    ("api_health_chat", "/health/chat", "api"),
    ("api_health_llm", "/api/health/llm", "api"),
    ("frontend_root", "/", "frontend"),
)
MUTATING_DOCKER_SUBCOMMANDS = frozenset(
    {
        "up",
        "down",
        "start",
        "stop",
        "restart",
        "build",
        "pull",
        "run",
        "exec",
        "rm",
        "kill",
        "create",
    }
)


class LiveProofError(Exception):
    """A bounded, stable collector error."""

    def __init__(self, code: str, message: str = "") -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class DockerObservationError(LiveProofError):
    """Docker prerequisite or observation failure with outcome context."""

    def __init__(self, code: str, *, blocked: bool) -> None:
        super().__init__(code, "Docker observation did not complete.")
        self.blocked = blocked


@dataclass(frozen=True)
class HttpResponse:
    """Transport-neutral bounded HTTP response."""

    status_code: int
    body: bytes
    final_url: str
    location: str | None = None


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        return None


def _utc_now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _timestamp(value: dt.datetime) -> str:
    if value.tzinfo is None:
        raise LiveProofError(
            "clock_value_invalid", "Clock values must include a timezone."
        )
    normalized = value.astimezone(dt.timezone.utc)
    if normalized.microsecond:
        return normalized.isoformat(timespec="microseconds").replace(
            "+00:00", "Z"
        )
    return normalized.isoformat(timespec="seconds").replace("+00:00", "Z")


def _safe_error_text(value: Any) -> str:
    text = " ".join(str(value).split())
    text = re.sub(
        r"(?i)(https?://)([^/@\s]+):[^/@\s]+@", r"\1[redacted]@", text
    )
    text = re.sub(
        r"(?i)(token|password|secret|api[_-]?key|credential)\s*[=:]\s*\S+",
        r"\1=[redacted]",
        text,
    )
    return text[:240]


def _error_envelope(code: str, message: str) -> dict[str, Any]:
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "collector_version": COLLECTOR_VERSION,
        "result": "error",
        "receipt": None,
        "validation": None,
        "reason_codes": [code],
        "error": {"code": code, "message": _safe_error_text(message)},
    }


def _reject_secret(value: Any, *, code: str = "forbidden_secret_input") -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if SECRET_RE.search(str(key)):
                raise LiveProofError(
                    code, "Secret-bearing input is not accepted."
                )
            _reject_secret(item, code=code)
    elif isinstance(value, (list, tuple)):
        for item in value:
            _reject_secret(item, code=code)
    elif isinstance(value, str):
        if SECRET_RE.search(value):
            raise LiveProofError(code, "Secret-bearing input is not accepted.")
        if Path(value).is_absolute() or PureWindowsPath(value).is_absolute():
            raise LiveProofError(
                "forbidden_absolute_path_input",
                "Absolute host-path input is not accepted.",
            )


def _project_name(value: str, label: str) -> str:
    normalized = str(value or "").strip().lower()
    _reject_secret(normalized)
    if not PROJECT_NAME_RE.fullmatch(normalized):
        raise LiveProofError(
            "compose_project_identity_ambiguous", f"Invalid {label}."
        )
    return normalized


def _repository_relative_file(root: Path, value: str, label: str) -> str:
    raw = str(value or "").strip().replace("\\", "/")
    if not raw:
        raise LiveProofError("compose_file_missing", f"{label} is missing.")
    if Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute():
        raise LiveProofError(
            "compose_path_absolute", f"{label} must be repository-relative."
        )
    if ".." in PurePosixPath(raw).parts:
        raise LiveProofError(
            "compose_path_parent_traversal",
            f"{label} contains parent traversal.",
        )
    candidate = (root / raw).resolve()
    try:
        relative = candidate.relative_to(root.resolve()).as_posix()
    except ValueError as exc:
        raise LiveProofError(
            "compose_path_outside_repository",
            f"{label} is outside the repository.",
        ) from exc
    if not candidate.is_file():
        raise LiveProofError("compose_file_missing", f"{label} is unavailable.")
    return relative


def _loopback_base(value: str, label: str) -> str:
    raw = str(value or "").strip()
    _reject_secret(raw)
    try:
        parsed = urllib.parse.urlsplit(raw)
        port = parsed.port
    except ValueError as exc:
        raise LiveProofError(
            "probe_base_url_invalid", f"{label} is invalid."
        ) from exc
    if parsed.scheme not in {"http", "https"}:
        raise LiveProofError(
            "probe_base_url_invalid", f"{label} must use HTTP or HTTPS."
        )
    if parsed.username is not None or parsed.password is not None:
        raise LiveProofError(
            "probe_base_url_credentials_forbidden",
            f"{label} must not contain credentials.",
        )
    if parsed.query or parsed.fragment or parsed.path not in {"", "/"}:
        raise LiveProofError(
            "probe_base_url_invalid",
            f"{label} must be an origin without path, query, or fragment.",
        )
    if (parsed.hostname or "").lower() not in {"localhost", "127.0.0.1", "::1"}:
        raise LiveProofError(
            "probe_base_not_loopback", f"{label} must use a loopback host."
        )
    host = parsed.hostname or ""
    rendered_host = f"[{host}]" if ":" in host else host
    return f"{parsed.scheme}://{rendered_host}{f':{port}' if port is not None else ''}"


def _validate_docker_command(args: Sequence[str]) -> None:
    command = list(args)
    if any(item in MUTATING_DOCKER_SUBCOMMANDS for item in command[1:]):
        raise LiveProofError(
            "docker_command_not_allowed",
            "Mutating Docker commands are forbidden.",
        )
    if command == ["docker", "version", "--format", "json"]:
        return
    if len(command) < 8 or command[:2] != ["docker", "compose"]:
        raise LiveProofError(
            "docker_command_not_allowed", "Docker command is not allowlisted."
        )
    index = 2
    compose_files = 0
    project_seen = False
    env_seen = False
    while index < len(command):
        item = command[index]
        if item == "-f" and index + 1 < len(command):
            compose_files += 1
            index += 2
            continue
        if item == "--env-file" and index + 1 < len(command) and not env_seen:
            env_seen = True
            index += 2
            continue
        if item == "-p" and index + 1 < len(command) and not project_seen:
            project_seen = True
            index += 2
            continue
        break
    suffix = command[index:]
    allowed_suffix = suffix in (
        ["ps", "--all", "--format", "json"],
        ["images", "--format", "json"],
    )
    if compose_files < 1 or not project_seen or not allowed_suffix:
        raise LiveProofError(
            "docker_command_not_allowed", "Docker command is not allowlisted."
        )


def _bytes(value: Any) -> bytes:
    if value is None:
        return b""
    if isinstance(value, bytes):
        return value
    if isinstance(value, str):
        return value.encode("utf-8", errors="replace")
    return str(value).encode("utf-8", errors="replace")


def _run_docker_command(
    args: Sequence[str],
    *,
    runner: Callable[..., Any],
    root: Path,
    timeout: float,
    commands: list[list[str]],
    blocked_on_failure: bool,
) -> bytes:
    _validate_docker_command(args)
    command = list(args)
    commands.append(command)
    try:
        completed = runner(
            command,
            check=False,
            capture_output=True,
            text=False,
            timeout=timeout,
            shell=False,
            cwd=str(root),
        )
    except FileNotFoundError as exc:
        raise DockerObservationError(
            "docker_cli_unavailable", blocked=True
        ) from exc
    except subprocess.TimeoutExpired as exc:
        raise DockerObservationError(
            "docker_command_timeout", blocked=blocked_on_failure
        ) from exc
    except OSError as exc:
        raise DockerObservationError(
            "docker_cli_unavailable", blocked=True
        ) from exc
    stdout = _bytes(getattr(completed, "stdout", b""))
    stderr = _bytes(getattr(completed, "stderr", b""))
    if (
        len(stdout) > MAX_DOCKER_OUTPUT_BYTES
        or len(stderr) > MAX_DOCKER_OUTPUT_BYTES
    ):
        raise DockerObservationError(
            "docker_output_too_large", blocked=blocked_on_failure
        )
    if int(getattr(completed, "returncode", 1)) != 0:
        safe_detail = (
            (stderr or stdout).decode("utf-8", errors="replace").lower()
        )
        if command[:2] == ["docker", "compose"] and (
            "not a docker command" in safe_detail
            or "unknown command" in safe_detail
            or "compose is not" in safe_detail
        ):
            code = "docker_compose_unavailable"
        elif command[:2] == ["docker", "version"]:
            code = "docker_server_unavailable"
        else:
            code = "compose_status_unavailable"
        raise DockerObservationError(code, blocked=blocked_on_failure)
    return stdout


def _json_object(raw: bytes, code: str) -> dict[str, Any]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise LiveProofError(
            code, "Observed JSON could not be parsed."
        ) from exc
    if not isinstance(value, dict):
        raise LiveProofError(code, "Observed JSON root must be an object.")
    return value


def _json_records(raw: bytes, code: str) -> list[dict[str, Any]]:
    text = raw.decode("utf-8", errors="strict").strip()
    if not text:
        return []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        records: list[Any] = []
        try:
            records = [
                json.loads(line) for line in text.splitlines() if line.strip()
            ]
        except json.JSONDecodeError as exc:
            raise LiveProofError(
                code, "Observed Docker JSON could not be parsed."
            ) from exc
    else:
        records = parsed if isinstance(parsed, list) else [parsed]
    if any(not isinstance(record, dict) for record in records):
        raise LiveProofError(code, "Observed Docker JSON records are invalid.")
    return [dict(record) for record in records]


def _version_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    if (
        not text
        or len(text) > 128
        or SECRET_RE.search(text)
        or Path(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
        or not SAFE_TEXT_RE.fullmatch(text)
    ):
        return None
    return text


def _docker_versions(raw: bytes) -> dict[str, str | None]:
    payload = _json_object(raw, "docker_version_invalid")
    client = (
        payload.get("Client")
        if isinstance(payload.get("Client"), Mapping)
        else {}
    )
    server = (
        payload.get("Server")
        if isinstance(payload.get("Server"), Mapping)
        else {}
    )
    client_version = _version_identifier(
        client.get("Version") or payload.get("ClientVersion")
    )
    server_version = _version_identifier(
        server.get("Version") or payload.get("ServerVersion")
    )
    if client_version is None or server_version is None:
        raise DockerObservationError("docker_server_unavailable", blocked=True)
    return {"client_version": client_version, "server_version": server_version}


def _compose_args(
    compose_files: Sequence[str],
    project: str,
    env_file: str | None,
    suffix: Sequence[str],
) -> list[str]:
    args = ["docker", "compose"]
    for compose_file in compose_files:
        args.extend(["-f", compose_file])
    if env_file is not None:
        args.extend(["--env-file", env_file])
    args.extend(["-p", project, *suffix])
    _validate_docker_command(args)
    return args


def _record_value(record: Mapping[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in record and record[key] is not None:
            return record[key]
    return None


def _safe_identifier(value: Any) -> str | None:
    text = str(value or "").strip()
    if (
        not text
        or len(text) > 256
        or SECRET_RE.search(text)
        or Path(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
    ):
        return None
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:@/-]{0,255}", text):
        return None
    return text


def _image_id(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    return text if IMAGE_ID_RE.fullmatch(text) else None


def _image_digest(record: Mapping[str, Any]) -> str | None:
    values = (
        _record_value(record, "Digest", "digest"),
        _record_value(record, "Repository", "repository"),
    )
    for value in values:
        text = str(value or "").strip().lower()
        candidate = text.rsplit("@", 1)[-1]
        if DIGEST_RE.fullmatch(candidate):
            return candidate
    return None


def _exit_code(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _normalize_state(value: Any) -> str | None:
    text = str(value or "").strip().lower().replace(" ", "_")
    if not text or len(text) > 64 or not re.fullmatch(r"[a-z0-9_.-]+", text):
        return None
    return text


def _service_observations(
    ps_records: Sequence[Mapping[str, Any]],
    image_records: Sequence[Mapping[str, Any]],
    required_services: Sequence[str],
    optional_services: Sequence[str],
) -> tuple[list[dict[str, Any]], list[str]]:
    required = set(required_services)
    expected = required | set(optional_services)
    images_by_container: dict[str, Mapping[str, Any]] = {}
    for record in image_records:
        container = _safe_identifier(
            _record_value(record, "Container", "ContainerName", "Name")
        )
        if container:
            images_by_container[container] = record
    by_service: dict[str, list[Mapping[str, Any]]] = {
        name: [] for name in expected
    }
    for record in ps_records:
        service = (
            str(_record_value(record, "Service", "service") or "")
            .strip()
            .lower()
        )
        if service in expected:
            by_service[service].append(record)

    observations: list[dict[str, Any]] = []
    aggregate_reasons: set[str] = set()
    for service in sorted(expected):
        is_required = service in required
        lifecycle = (
            "one_shot" if service in ONE_SHOT_SERVICES else "long_running"
        )
        records = sorted(
            by_service[service],
            key=lambda item: str(
                _record_value(item, "ID", "Id", "Container", "Name") or ""
            ),
        )
        if not records:
            reasons = ["required_service_missing"] if is_required else []
            aggregate_reasons.update(reasons)
            observations.append(
                {
                    "service": service,
                    "required": is_required,
                    "lifecycle": lifecycle,
                    "container_identity": None,
                    "image_id": None,
                    "image_digest": None,
                    "state": None,
                    "health_status": None,
                    "exit_code": None,
                    "observation_result": "FAIL"
                    if is_required
                    else "OPTIONAL_ABSENT",
                    "reason_codes": reasons,
                }
            )
            continue
        for record in records:
            container = _safe_identifier(
                _record_value(record, "ID", "Id", "Container", "Name")
            )
            container_name = _safe_identifier(
                _record_value(record, "Name", "Container")
            )
            image_record = images_by_container.get(container_name or "", {})
            image_identity = _image_id(
                _record_value(image_record, "ID", "Id", "ImageID", "Image")
                or _record_value(record, "ImageID")
            )
            digest = _image_digest(image_record) or _image_digest(record)
            state = _normalize_state(_record_value(record, "State", "state"))
            health = _normalize_state(_record_value(record, "Health", "health"))
            exit_code = _exit_code(
                _record_value(record, "ExitCode", "ExitCode")
            )
            reasons: list[str] = []
            if container is None or state is None:
                reasons.append("service_status_invalid")
            if is_required and image_identity is None:
                reasons.append("required_image_identity_missing")
            if is_required and lifecycle == "long_running":
                if state != "running":
                    reasons.append("required_service_not_running")
                if health is not None and health != "healthy":
                    reasons.append("required_service_unhealthy")
            if is_required and lifecycle == "one_shot":
                if state not in {"exited", "completed"} or exit_code is None:
                    reasons.append("required_one_shot_incomplete")
                elif exit_code != 0:
                    reasons.append("required_one_shot_failed")
            aggregate_reasons.update(reasons)
            observations.append(
                {
                    "service": service,
                    "required": is_required,
                    "lifecycle": lifecycle,
                    "container_identity": container,
                    "image_id": image_identity,
                    "image_digest": digest,
                    "state": state,
                    "health_status": health,
                    "exit_code": exit_code,
                    "observation_result": "FAIL" if reasons else "PASS",
                    "reason_codes": sorted(set(reasons)),
                }
            )
    observations.sort(
        key=lambda item: (item["service"], item["container_identity"] or "")
    )
    return observations, sorted(aggregate_reasons)


def _default_http_transport(url: str, timeout: float) -> HttpResponse:
    opener = urllib.request.build_opener(_NoRedirect())
    request = urllib.request.Request(url, method="GET")
    try:
        with opener.open(request, timeout=timeout) as response:
            body = response.read(MAX_HTTP_BODY_BYTES + 1)
            return HttpResponse(
                int(response.status), body, response.geturl(), None
            )
    except urllib.error.HTTPError as exc:
        body = exc.read(MAX_HTTP_BODY_BYTES + 1)
        return HttpResponse(
            int(exc.code), body, exc.geturl(), exc.headers.get("Location")
        )
    except TimeoutError as exc:
        raise LiveProofError(
            "http_probe_timeout", "An HTTP probe timed out."
        ) from exc
    except urllib.error.URLError as exc:
        if isinstance(exc.reason, TimeoutError):
            raise LiveProofError(
                "http_probe_timeout", "An HTTP probe timed out."
            ) from exc
        raise LiveProofError(
            "http_transport_error", "An HTTP transport failed."
        ) from exc
    except OSError as exc:
        raise LiveProofError(
            "http_transport_error", "An HTTP transport failed."
        ) from exc


def _coerce_http_response(value: Any, requested_url: str) -> HttpResponse:
    if isinstance(value, HttpResponse):
        response = value
    elif isinstance(value, Mapping):
        response = HttpResponse(
            status_code=int(value.get("status_code", value.get("status", 0))),
            body=_bytes(value.get("body", value.get("content", b""))),
            final_url=str(
                value.get("final_url", value.get("url", requested_url))
            ),
            location=str(value["location"])
            if value.get("location") is not None
            else None,
        )
    else:
        response = HttpResponse(
            status_code=int(
                getattr(value, "status_code", getattr(value, "status", 0))
            ),
            body=_bytes(getattr(value, "body", getattr(value, "content", b""))),
            final_url=str(
                getattr(
                    value, "final_url", getattr(value, "url", requested_url)
                )
            ),
            location=getattr(value, "location", None),
        )
    if response.status_code < 100 or response.status_code > 599:
        raise LiveProofError(
            "http_response_invalid", "HTTP status code is invalid."
        )
    if len(response.body) > MAX_HTTP_BODY_BYTES:
        raise LiveProofError(
            "http_body_too_large",
            "HTTP response body exceeded the bounded limit.",
        )
    requested = urllib.parse.urlsplit(requested_url)
    final = urllib.parse.urlsplit(response.final_url)
    if final.netloc != requested.netloc:
        raise LiveProofError(
            "cross_host_redirect_forbidden",
            "Cross-host redirects are forbidden.",
        )
    if response.location:
        redirected = urllib.parse.urlsplit(
            urllib.parse.urljoin(requested_url, response.location)
        )
        if redirected.netloc != requested.netloc:
            raise LiveProofError(
                "cross_host_redirect_forbidden",
                "Cross-host redirects are forbidden.",
            )
    return response


def _safe_projection_text(value: Any) -> str | None:
    text = str(value or "").strip().lower()
    if (
        not text
        or len(text) > 128
        or SECRET_RE.search(text)
        or Path(text).is_absolute()
        or PureWindowsPath(text).is_absolute()
    ):
        return None
    if not re.fullmatch(r"[a-z0-9][a-z0-9_.:-]*", text):
        return None
    return text


def _profile_payload(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    profile = payload.get("supported_profile")
    if not isinstance(profile, Mapping):
        details = payload.get("details")
        profile = (
            details.get("supported_profile")
            if isinstance(details, Mapping)
            else None
        )
    return profile if isinstance(profile, Mapping) else {}


def _release_hold(
    payload: Mapping[str, Any], profile: Mapping[str, Any]
) -> bool | None:
    value = payload.get("release_hold")
    if value is None:
        details = payload.get("details")
        value = (
            details.get("release_hold")
            if isinstance(details, Mapping)
            else None
        )
    if value is None:
        value = profile.get("release_hold")
    return value if isinstance(value, bool) else None


def _safe_profile_projection(profile: Mapping[str, Any]) -> dict[str, Any]:
    raw_mismatches = profile.get("mismatches")
    mismatches: list[str] = []
    if isinstance(raw_mismatches, list):
        for mismatch in raw_mismatches[:64]:
            mismatches.append(
                _safe_projection_text(mismatch) or "redacted_mismatch"
            )
    return {
        "name": _safe_projection_text(profile.get("name")),
        "valid": profile.get("valid")
        if isinstance(profile.get("valid"), bool)
        else None,
        "mismatches": mismatches,
        "selected_provider_supported": (
            profile.get("selected_provider_supported")
            if isinstance(profile.get("selected_provider_supported"), bool)
            else None
        ),
    }


def _probe_projection_and_reasons(
    probe_id: str,
    status_code: int,
    payload: Mapping[str, Any] | None,
    supported_profile: str,
) -> tuple[dict[str, Any], list[str]]:
    projection: dict[str, Any] = {}
    reasons: set[str] = set()
    if probe_id == "frontend_root":
        if not 200 <= status_code < 400:
            reasons.add("frontend_probe_failed")
        return projection, sorted(reasons)
    if not 200 <= status_code < 300:
        reasons.add("probe_http_status_invalid")
    if probe_id == "api_ping":
        return projection, sorted(reasons)
    if payload is None:
        raise LiveProofError(
            "http_json_invalid", "Health response JSON is invalid."
        )

    status = _safe_projection_text(payload.get("status"))
    ok = payload.get("ok") if isinstance(payload.get("ok"), bool) else None
    projection.update({"status": status, "ok": ok})
    if probe_id == "api_health":
        profile = _profile_payload(payload)
        safe_profile = _safe_profile_projection(profile)
        release_hold = _release_hold(payload, profile)
        projection.update(
            {"release_hold": release_hold, "supported_profile": safe_profile}
        )
        if status not in HEALTHY_STATUSES:
            reasons.add("health_status_unhealthy")
        if safe_profile["name"] != supported_profile:
            reasons.add("supported_profile_mismatch")
        if safe_profile["valid"] is not True:
            reasons.add("supported_profile_invalid")
        if safe_profile["mismatches"]:
            reasons.add("supported_profile_mismatches")
        if release_hold is not False:
            reasons.add("release_hold_active")
        if safe_profile["selected_provider_supported"] is False:
            reasons.add("selected_provider_unsupported")
    elif probe_id == "api_health_chat":
        completion = payload.get("completion_service")
        completion = completion if isinstance(completion, Mapping) else {}
        safe_completion = {
            "ok": completion.get("ok")
            if isinstance(completion.get("ok"), bool)
            else None,
            "redis_reachable": (
                completion.get("redis_reachable")
                if isinstance(completion.get("redis_reachable"), bool)
                else None
            ),
            "enqueue_test_ok": (
                completion.get("enqueue_test_ok")
                if isinstance(completion.get("enqueue_test_ok"), bool)
                else None
            ),
            "worker_heartbeat_status": _safe_projection_text(
                completion.get("worker_heartbeat_status")
            ),
        }
        projection["completion_service"] = safe_completion
        if safe_completion["ok"] is not True:
            reasons.add("chat_completion_service_unhealthy")
        if safe_completion["redis_reachable"] is not True:
            reasons.add("chat_redis_unreachable")
        if safe_completion["enqueue_test_ok"] is not True:
            reasons.add("chat_enqueue_probe_failed")
        if safe_completion["worker_heartbeat_status"] != "fresh":
            reasons.add("chat_worker_heartbeat_not_fresh")
    elif probe_id == "api_health_llm":
        profile = _profile_payload(payload)
        safe_profile = _safe_profile_projection(profile)
        release_hold = _release_hold(payload, profile)
        provider_runtime = payload.get("provider_runtime")
        runtime_available = (
            provider_runtime.get("enabled")
            if isinstance(provider_runtime, Mapping)
            and isinstance(provider_runtime.get("enabled"), bool)
            else None
        )
        models_available = (
            payload.get("models_available")
            if isinstance(payload.get("models_available"), bool)
            else None
        )
        projection.update(
            {
                "release_hold": release_hold,
                "supported_profile": safe_profile,
                "models_available": models_available,
                "provider_runtime_available": runtime_available,
            }
        )
        if status not in HEALTHY_STATUSES:
            reasons.add("llm_status_unhealthy")
        if models_available is not True:
            reasons.add("llm_models_unavailable")
        if runtime_available is not True:
            reasons.add("provider_runtime_unavailable")
        if safe_profile["name"] != supported_profile:
            reasons.add("supported_profile_mismatch")
        if release_hold is not False:
            reasons.add("release_hold_active")
    return projection, sorted(reasons)


def _execute_probe(
    probe_id: str,
    path: str,
    base: str,
    supported_profile: str,
    *,
    clock: Callable[[], dt.datetime],
    transport: Callable[[str, float], Any],
    timeout: float,
) -> dict[str, Any]:
    started_value = clock()
    started_at = _timestamp(started_value)
    url = f"{base}{path}"
    try:
        response = _coerce_http_response(transport(url, timeout), url)
    except LiveProofError:
        raise
    except TimeoutError as exc:
        raise LiveProofError(
            "http_probe_timeout", "An HTTP probe timed out."
        ) from exc
    except Exception as exc:
        raise LiveProofError(
            "http_transport_error", "An HTTP transport failed."
        ) from exc
    completed_value = clock()
    completed_at = _timestamp(completed_value)
    duration_ms = max(
        0, int((completed_value - started_value).total_seconds() * 1000)
    )
    payload: Mapping[str, Any] | None = None
    if probe_id not in {"api_ping", "frontend_root"}:
        payload = _json_object(response.body, "http_json_invalid")
    projection, reasons = _probe_projection_and_reasons(
        probe_id, response.status_code, payload, supported_profile
    )
    return {
        "probe_id": probe_id,
        "method": "GET",
        "path": path,
        "status_code": response.status_code,
        "started_at": started_at,
        "completed_at": completed_at,
        "duration_ms": duration_ms,
        "outcome": "FAIL" if reasons else "PASS",
        "response_body_sha256": hashlib.sha256(response.body).hexdigest(),
        "projection": projection,
        "reason_codes": reasons,
    }


def _receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Canonical identity projection; list order is execution or documented stable order."""
    return {key: value for key, value in receipt.items() if key != "receipt_id"}


def _receipt_id(receipt: Mapping[str, Any]) -> str:
    payload = json.dumps(
        _receipt_projection(receipt),
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return f"live-proof-receipt-sha256-{hashlib.sha256(payload).hexdigest()}"


def _json_path(parts: Sequence[Any]) -> str:
    return "$" + "".join(
        f"[{part}]" if isinstance(part, int) else f".{part}" for part in parts
    )


def validate_receipt(
    receipt: Mapping[str, Any], schema_path: str | Path = DEFAULT_SCHEMA_PATH
) -> dict[str, Any]:
    issues: list[dict[str, str]] = []
    try:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        Draft202012Validator.check_schema(schema)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        issues.append({"code": "receipt_schema_unavailable", "path": "$"})
    except Exception:
        issues.append({"code": "receipt_schema_invalid", "path": "$"})
    else:
        validator = Draft202012Validator(schema, format_checker=FormatChecker())
        for error in sorted(
            validator.iter_errors(dict(receipt)),
            key=lambda item: (
                _json_path(list(item.absolute_path)),
                item.validator or "",
            ),
        ):
            issues.append(
                {
                    "code": "receipt_schema_validation_error",
                    "path": _json_path(list(error.absolute_path)),
                }
            )
    return {
        "result": "pass" if not issues else "fail",
        "schema_valid": not issues,
        "issue_count": len(issues),
        "issues": issues,
    }


def receipt_projection(receipt: Mapping[str, Any]) -> dict[str, Any]:
    """Public canonical receipt identity projection (excludes receipt_id)."""
    return _receipt_projection(receipt)


def receipt_id(receipt: Mapping[str, Any]) -> str:
    """Public deterministic receipt identity from the canonical projection."""
    return _receipt_id(receipt)


def _output_destination(root: Path, output_path: str) -> Path:
    raw = str(output_path or "").strip().replace("\\", "/")
    if not raw or Path(raw).is_absolute() or PureWindowsPath(raw).is_absolute():
        raise LiveProofError(
            "output_path_invalid", "Output path must be repository-relative."
        )
    if ".." in PurePosixPath(raw).parts:
        raise LiveProofError(
            "output_path_invalid",
            "Output path must not contain parent traversal.",
        )
    destination = (root / raw).resolve()
    try:
        destination.relative_to(root.resolve())
    except ValueError as exc:
        raise LiveProofError(
            "output_path_invalid",
            "Output path resolves outside the repository.",
        ) from exc
    return destination


def _write_output(
    receipt: Mapping[str, Any], output_path: str, root: Path, replace: bool
) -> None:
    destination = _output_destination(root, output_path)
    lexical_destination = root / Path(
        *PurePosixPath(output_path.replace("\\", "/")).parts
    )
    if lexical_destination.is_symlink():
        raise LiveProofError(
            "output_path_invalid", "Symlink output paths are not accepted."
        )
    if destination.exists() and not replace:
        raise LiveProofError(
            "output_exists", "Output exists; pass --replace to replace it."
        )
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            json.dump(
                receipt, handle, ensure_ascii=False, indent=2, sort_keys=True
            )
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    except OSError as exc:
        if temporary is not None:
            try:
                temporary.unlink()
            except OSError:
                pass
        raise LiveProofError(
            "output_write_failed",
            "Receipt output could not be written atomically.",
        ) from exc


def collect_live_proof_receipt(
    repo_path: str | Path = ".",
    *,
    machine_id: str,
    machine_role: str,
    authority_basis: str,
    assert_canonical_machine: bool = False,
    compose_files: Sequence[str],
    compose_project: str,
    project_role: str,
    profile_name: str,
    audit_project: str,
    serving_project: str | None = None,
    compose_environment_file: str | None = None,
    api_base_url: str,
    frontend_base_url: str,
    command_timeout: float = DEFAULT_COMMAND_TIMEOUT_SECONDS,
    http_timeout: float = DEFAULT_HTTP_TIMEOUT_SECONDS,
    receipt_id: str | None = None,
    output_path: str | None = None,
    replace: bool = False,
    schema_path: str | Path = DEFAULT_SCHEMA_PATH,
    clock: Callable[[], dt.datetime] = _utc_now,
    subprocess_runner: Callable[..., Any] = subprocess.run,
    http_transport: Callable[[str, float], Any] = _default_http_transport,
    identity_collector: Callable[..., dict[str, Any]] = collect_identity,
    runtime_collector: Callable[..., dict[str, Any]] = collect_runtime_identity,
) -> dict[str, Any]:
    """Return a versioned result envelope for one read-only live observation."""
    try:
        if receipt_id is not None:
            raise LiveProofError(
                "caller_receipt_id_forbidden",
                "receipt_id is collector-generated.",
            )
        if isinstance(command_timeout, bool) or command_timeout <= 0:
            raise LiveProofError(
                "command_timeout_invalid", "Command timeout must be positive."
            )
        if isinstance(http_timeout, bool) or http_timeout <= 0:
            raise LiveProofError(
                "http_timeout_invalid", "HTTP timeout must be positive."
            )
        if project_role not in {"serving", "audit"}:
            raise LiveProofError(
                "project_role_invalid", "Project role must be serving or audit."
            )
        root = Path(repo_path).expanduser().resolve()
        if not root.is_dir():
            raise LiveProofError(
                "repository_path_invalid", "Repository path is unavailable."
            )
        selected_project = _project_name(
            compose_project, "selected Compose project"
        )
        selected_audit = _project_name(audit_project, "audit project")
        selected_serving = (
            _project_name(serving_project, "serving project")
            if serving_project
            else None
        )
        if project_role == "audit" and selected_project != selected_audit:
            raise LiveProofError(
                "project_role_identity_mismatch",
                "Audit role must select the audit project.",
            )
        if project_role == "serving" and (
            selected_serving is None or selected_project != selected_serving
        ):
            raise LiveProofError(
                "project_role_identity_mismatch",
                "Serving role must select the serving project.",
            )
        _reject_secret([machine_id, authority_basis, profile_name])
        api_base = _loopback_base(api_base_url, "API base URL")
        frontend_base = _loopback_base(frontend_base_url, "frontend base URL")

        started_value = clock()
        started_at = _timestamp(started_value)
        machine_result = identity_collector(
            root,
            machine_id=machine_id,
            machine_role=machine_role,
            authority_basis=authority_basis,
            assert_canonical_machine=assert_canonical_machine,
            timeout=command_timeout,
        )
        machine = machine_result.get("machine")
        repository = machine_result.get("repository")
        identity_eligibility = machine_result.get("eligibility")
        if (
            not isinstance(machine, Mapping)
            or not isinstance(repository, Mapping)
            or not isinstance(identity_eligibility, Mapping)
        ):
            raise LiveProofError(
                "machine_identity_incomplete",
                "Machine/Git identity is incomplete.",
            )
        if not all(
            repository.get(field) is not None
            for field in (
                "repository_root_identity",
                "branch",
                "commit_sha",
                "dirty",
                "worktree_identity",
            )
        ):
            raise LiveProofError(
                "repository_identity_incomplete",
                "Repository identity is incomplete.",
            )

        runtime_result = runtime_collector(
            root,
            profile_name=profile_name,
            compose_files=compose_files,
            audit_project=selected_audit,
            serving_project=selected_serving,
        )
        runtime = runtime_result.get("runtime")
        runtime_eligibility = runtime_result.get("eligibility")
        if not isinstance(runtime, Mapping) or not isinstance(
            runtime_eligibility, Mapping
        ):
            raise LiveProofError(
                "runtime_identity_incomplete",
                "Static runtime identity is incomplete.",
            )
        if not runtime_eligibility.get("runtime_identity_complete"):
            codes = runtime_eligibility.get("reason_codes") or [
                "runtime_identity_incomplete"
            ]
            raise LiveProofError(
                str(codes[0]), "Static runtime identity is incomplete."
            )
        compose_identity = runtime.get("compose_identity")
        if not isinstance(compose_identity, Mapping):
            raise LiveProofError(
                "runtime_identity_incomplete",
                "Static Compose identity is incomplete.",
            )
        normalized_compose_files = list(runtime.get("compose_files") or [])
        if not normalized_compose_files:
            raise LiveProofError(
                "runtime_identity_incomplete",
                "Static Compose identity is incomplete.",
            )
        env_file = None
        if compose_environment_file is not None:
            env_file = _repository_relative_file(
                root, compose_environment_file, "Compose environment file"
            )

        authority_status = (
            "CANONICAL"
            if identity_eligibility.get("canonical_machine_candidate") is True
            and identity_eligibility.get("canonical_repository_candidate")
            is True
            else "PROVISIONAL"
        )
        base_reasons = set(identity_eligibility.get("reason_codes") or [])
        base_reasons.update(runtime_eligibility.get("reason_codes") or [])
        commands: list[list[str]] = []
        docker_identity: dict[str, str | None] = {
            "client_version": None,
            "server_version": None,
        }
        services: list[dict[str, Any]] = []
        probes: list[dict[str, Any]] = []

        def finalize(
            outcome: str, added_reasons: Sequence[str]
        ) -> dict[str, Any]:
            reasons = sorted(base_reasons | set(added_reasons))
            completed_value = clock()
            completed_at = _timestamp(completed_value)
            receipt: dict[str, Any] = {
                "schema_version": RECEIPT_SCHEMA_VERSION,
                "receipt_id": "",
                "suite_id": SUITE_ID,
                "proof_class": PROOF_CLASS,
                "authority_status": authority_status,
                "execution_outcome": outcome,
                "created_at": completed_at,
                "started_at": started_at,
                "completed_at": completed_at,
                "machine": {
                    field: machine[field]
                    for field in (
                        "machine_id",
                        "machine_role",
                        "hostname",
                        "authority_basis",
                    )
                },
                "repository": {
                    field: repository.get(field)
                    for field in (
                        "repository_root_identity",
                        "branch",
                        "commit_sha",
                        "upstream_sha",
                        "dirty",
                        "worktree_identity",
                    )
                },
                "runtime": {
                    "supported_profile": runtime.get("supported_profile"),
                    "effective_config_hash": runtime.get(
                        "effective_config_hash"
                    ),
                    "compose_project": runtime.get("compose_project"),
                    "compose_files": normalized_compose_files,
                    "migration_head": runtime.get("migration_head"),
                    "service_identities": list(
                        runtime.get("service_identities") or []
                    ),
                    "required_services": list(
                        compose_identity.get("required_services") or []
                    ),
                    "optional_services": list(
                        compose_identity.get("optional_services") or []
                    ),
                },
                "target": {
                    "compose_project": selected_project,
                    "project_role": project_role,
                    "audit_project": selected_audit,
                    "serving_project": selected_serving,
                    "compose_environment_file": env_file,
                },
                "docker": docker_identity,
                "services": services,
                "probes": probes,
                "commands": commands,
                "reason_codes": reasons,
            }
            receipt["receipt_id"] = _receipt_id(receipt)
            validation = validate_receipt(receipt, schema_path)
            if validation["result"] != "pass":
                receipt["execution_outcome"] = "ERROR"
                receipt["reason_codes"] = sorted(
                    set(receipt["reason_codes"])
                    | {"receipt_schema_validation_failed"}
                )
                receipt["receipt_id"] = _receipt_id(receipt)
                validation = validate_receipt(receipt, schema_path)
                return {
                    "schema_version": RESULT_SCHEMA_VERSION,
                    "collector_version": COLLECTOR_VERSION,
                    "result": "error",
                    "receipt": receipt,
                    "validation": validation,
                    "reason_codes": receipt["reason_codes"],
                    "error": {
                        "code": "receipt_schema_validation_failed",
                        "message": "Generated receipt did not satisfy its schema.",
                    },
                }
            if output_path is not None:
                _write_output(receipt, output_path, root, replace)
            envelope = {
                "schema_version": RESULT_SCHEMA_VERSION,
                "collector_version": COLLECTOR_VERSION,
                "result": outcome.lower(),
                "receipt": receipt,
                "validation": validation,
                "reason_codes": receipt["reason_codes"],
            }
            if outcome == "ERROR":
                code = next(iter(added_reasons), "collector_error")
                envelope["error"] = {
                    "code": code,
                    "message": "Live proof collection did not complete trustworthily.",
                }
            return envelope

        try:
            version_raw = _run_docker_command(
                ["docker", "version", "--format", "json"],
                runner=subprocess_runner,
                root=root,
                timeout=command_timeout,
                commands=commands,
                blocked_on_failure=True,
            )
            docker_identity.update(_docker_versions(version_raw))
            ps_command = _compose_args(
                normalized_compose_files,
                selected_project,
                env_file,
                ["ps", "--all", "--format", "json"],
            )
            ps_raw = _run_docker_command(
                ps_command,
                runner=subprocess_runner,
                root=root,
                timeout=command_timeout,
                commands=commands,
                blocked_on_failure=True,
            )
            ps_records = _json_records(ps_raw, "compose_status_invalid")
            if not ps_records:
                return finalize("BLOCKED", ["compose_project_missing"])
            images_command = _compose_args(
                normalized_compose_files,
                selected_project,
                env_file,
                ["images", "--format", "json"],
            )
            images_raw = _run_docker_command(
                images_command,
                runner=subprocess_runner,
                root=root,
                timeout=command_timeout,
                commands=commands,
                blocked_on_failure=False,
            )
            image_records = _json_records(images_raw, "compose_images_invalid")
        except DockerObservationError as exc:
            return finalize("BLOCKED" if exc.blocked else "ERROR", [exc.code])
        except (UnicodeDecodeError, LiveProofError) as exc:
            code = (
                exc.code
                if isinstance(exc, LiveProofError)
                else "compose_status_invalid"
            )
            return finalize("ERROR", [code])

        services[:], service_reasons = _service_observations(
            ps_records,
            image_records,
            list(compose_identity.get("required_services") or []),
            list(compose_identity.get("optional_services") or []),
        )
        observed_failure = bool(service_reasons)
        observation_reasons: set[str] = set(service_reasons)
        for probe_id, path, base_kind in PROBE_DEFINITIONS:
            try:
                probe = _execute_probe(
                    probe_id,
                    path,
                    api_base if base_kind == "api" else frontend_base,
                    str(runtime.get("supported_profile")),
                    clock=clock,
                    transport=http_transport,
                    timeout=http_timeout,
                )
            except LiveProofError as exc:
                observation_reasons.add(exc.code)
                return finalize("ERROR", sorted(observation_reasons))
            probes.append(probe)
            observation_reasons.update(probe["reason_codes"])
            observed_failure = observed_failure or probe["outcome"] == "FAIL"
        return finalize(
            "FAIL" if observed_failure else "PASS", sorted(observation_reasons)
        )
    except (CollectorError, RuntimeIdentityError) as exc:
        return _error_envelope(exc.code, exc.message)
    except LiveProofError as exc:
        return _error_envelope(exc.code, exc.message)


collect_canonical_live_proof_receipt = collect_live_proof_receipt


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Collect one bounded read-only supported-Compose live proof receipt."
    )
    parser.add_argument("--repo", required=True)
    parser.add_argument("--machine-id", required=True)
    parser.add_argument("--machine-role", required=True)
    parser.add_argument("--authority-basis", required=True)
    parser.add_argument("--assert-canonical-machine", action="store_true")
    parser.add_argument("--compose-file", action="append", required=True)
    parser.add_argument("--compose-project", required=True)
    parser.add_argument(
        "--project-role", choices=("serving", "audit"), required=True
    )
    parser.add_argument("--profile-name", default=DEFAULT_PROFILE_NAME)
    parser.add_argument("--audit-project", required=True)
    parser.add_argument("--serving-project")
    parser.add_argument("--compose-env-file")
    parser.add_argument("--api-base", required=True)
    parser.add_argument("--frontend-base", required=True)
    parser.add_argument(
        "--command-timeout", type=float, default=DEFAULT_COMMAND_TIMEOUT_SECONDS
    )
    parser.add_argument(
        "--http-timeout", type=float, default=DEFAULT_HTTP_TIMEOUT_SECONDS
    )
    parser.add_argument("--output")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args(argv)
    result = collect_live_proof_receipt(
        args.repo,
        machine_id=args.machine_id,
        machine_role=args.machine_role,
        authority_basis=args.authority_basis,
        assert_canonical_machine=args.assert_canonical_machine,
        compose_files=args.compose_file,
        compose_project=args.compose_project,
        project_role=args.project_role,
        profile_name=args.profile_name,
        audit_project=args.audit_project,
        serving_project=args.serving_project,
        compose_environment_file=args.compose_env_file,
        api_base_url=args.api_base,
        frontend_base_url=args.frontend_base,
        command_timeout=args.command_timeout,
        http_timeout=args.http_timeout,
        output_path=args.output,
        replace=args.replace,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    outcome = (result.get("receipt") or {}).get("execution_outcome")
    validation = result.get("validation") or {}
    if validation.get("result") == "pass" and outcome == "PASS":
        return 0
    if validation.get("result") == "pass" and outcome in {"FAIL", "BLOCKED"}:
        return 1
    return 2


if __name__ == "__main__":
    sys.exit(main())
