#!/usr/bin/env python3
"""Bounded live E2B probe for the ADR-077 immediate read/exec posture.

This is a proof probe, not a Codexify SandboxProvider adapter. It uses only
synthetic fixtures, records no credential values, and emits bounded JSON.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import re
import shlex
import sys
import time
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import PurePosixPath
from typing import Any

from e2b import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException
from pyqwest import SyncHTTPTransport
from pyqwest.httpx import PyqwestTransport


EXPECTED_SDK_VERSION = "2.46.0"
PROBE_VERSION = "adr077-e2b-read-exec-v1"
MAX_CAPTURE_BYTES = 4096
COMMAND_TIMEOUT_SECONDS = 20
SANDBOX_TIMEOUT_SECONDS = 180
LIFECYCLE_TIMEOUT_SECONDS = 7
POLL_SECONDS = 1
MAX_POLL_SECONDS = 18
SAFE_ENV_NAME = "E2B_CONFORMANCE_SAFE"
HOST_REPOSITORY_PATH = "/Volumes/Dev_SSD/Codexify-main"
ALL_TRAFFIC = "0.0.0.0/0"

SECRET_NAME_MARKERS = (
    "API_KEY",
    "TOKEN",
    "SECRET",
    "PASSWORD",
    "CREDENTIAL",
    "DATABASE",
    "POSTGRES",
    "REDIS",
    "OPENAI",
    "ANTHROPIC",
    "MINIMAX",
    "GITHUB",
    "AWS_",
    "GOOGLE_",
)
KNOWN_SECRET_NAMES = {
    "E2B_API_KEY",
    "CODEXIFY_DATABASE_URL",
    "DATABASE_URL",
    "POSTGRES_PASSWORD",
    "REDIS_URL",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "MINIMAX_API_KEY",
    "GITHUB_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
}
SAFE_BASELINE_ENV_NAMES = {
    "HOME",
    "HOSTNAME",
    "LANG",
    "LC_ALL",
    "LOGNAME",
    "OLDPWD",
    "PATH",
    "PWD",
    "SHELL",
    "SHLVL",
    "TERM",
    "TMPDIR",
    "USER",
    "_",
}


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def enum_value(value: Any) -> Any:
    return getattr(value, "value", value)


def json_value(value: Any) -> Any:
    if isinstance(value, datetime):
        return value.isoformat().replace("+00:00", "Z")
    if is_dataclass(value):
        return {key: json_value(item) for key, item in asdict(value).items()}
    if isinstance(value, dict):
        return {str(key): json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [json_value(item) for item in value]
    return enum_value(value)


def redact(value: str) -> str:
    secret = os.environ.get("E2B_API_KEY")
    if secret:
        value = value.replace(secret, "<redacted>")
    return value


def bounded_text(value: str | bytes | bytearray | None) -> dict[str, Any]:
    if value is None:
        value = ""
    if isinstance(value, (bytes, bytearray)):
        raw = bytes(value)
        decoded = raw[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
    else:
        raw = value.encode("utf-8", errors="replace")
        decoded = raw[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace")
    decoded = redact(decoded)
    return {
        "total_bytes": len(raw),
        "stored_bytes": len(decoded.encode("utf-8")),
        "truncated": len(raw) > MAX_CAPTURE_BYTES,
        "text": decoded,
    }


def command_record(
    sandbox: Sandbox,
    label: str,
    command: str,
    *,
    cwd: str | None = None,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    started = now()
    base: dict[str, Any] = {
        "label": label,
        "command": command,
        "cwd": cwd,
        "started_at": started,
    }
    try:
        result = sandbox.commands.run(
            command,
            background=False,
            cwd=cwd,
            timeout=timeout,
        )
        base.update(
            {
                "status": "completed",
                "exit_code": result.exit_code,
                "stdout": bounded_text(result.stdout),
                "stderr": bounded_text(result.stderr),
                "provider_error_present": result.error is not None,
            }
        )
    except CommandExitException as exc:
        base.update(
            {
                "status": "nonzero_exit",
                "exit_code": exc.exit_code,
                "stdout": bounded_text(exc.stdout),
                "stderr": bounded_text(exc.stderr),
                "provider_error_present": exc.error is not None,
            }
        )
    except Exception as exc:  # provider/transport/timeout classification only
        base.update(
            {
                "status": "transport_or_timeout_error",
                "exception_type": type(exc).__name__,
            }
        )
    base["completed_at"] = now()
    return base


def command_output(record: dict[str, Any]) -> str:
    return str(record.get("stdout", {}).get("text", ""))


def command_failed(record: dict[str, Any]) -> bool:
    return record.get("status") != "completed" or record.get("exit_code") != 0


def info_record(info: Any) -> dict[str, Any]:
    data = json_value(info)
    data.pop("metadata", None)
    return data


def safe_process_records(processes: list[Any]) -> list[dict[str, Any]]:
    records = []
    for process in processes:
        records.append(
            {
                "pid": process.pid,
                "tag": process.tag,
                "cmd": process.cmd,
                "args": list(process.args),
                "cwd": process.cwd,
            }
        )
    return records


def get_info_record(sandbox: Sandbox) -> dict[str, Any]:
    return json_value(sandbox.get_info())


def get_metrics_record(sandbox: Sandbox) -> list[dict[str, Any]]:
    return [json_value(item) for item in sandbox.get_metrics()]


def resource_posture(
    sandbox: Sandbox,
    info: dict[str, Any],
    metrics: list[dict[str, Any]],
) -> dict[str, Any]:
    resource_probe = command_record(
        sandbox,
        "bounded-storage-observation",
        "df -Pk /tmp | tail -n 1",
    )
    create_parameters = set(inspect.signature(Sandbox.create).parameters)
    latest_metrics = metrics[-1] if metrics else {}
    return {
        "cpu": {
            "classification": "PREDECLARED_RESOURCE_CLASS",
            "observed_cpu_count": info.get("cpu_count"),
            "selectable_create_parameter": next(
                (
                    name
                    for name in create_parameters
                    if "cpu" in name.lower()
                ),
                None,
            ),
            "hard_ceiling_proven": False,
        },
        "memory": {
            "classification": "PREDECLARED_RESOURCE_CLASS",
            "observed_memory_mb": info.get("memory_mb"),
            "observed_metrics_memory_total": latest_metrics.get("mem_total"),
            "selectable_create_parameter": next(
                (
                    name
                    for name in create_parameters
                    if "memory" in name.lower() or "mem" in name.lower()
                ),
                None,
            ),
            "hard_ceiling_proven": False,
        },
        "storage": {
            "classification": "MEASUREMENT_ONLY",
            "observed_metrics_disk_total": latest_metrics.get("disk_total"),
            "observed_metrics_disk_used": latest_metrics.get("disk_used"),
            "selectable_create_parameter": next(
                (
                    name
                    for name in create_parameters
                    if "disk" in name.lower() or "storage" in name.lower()
                ),
                None,
            ),
            "hard_ceiling_proven": False,
        },
        "provider_class_metadata": {
            "cpu_count": info.get("cpu_count"),
            "memory_mb": info.get("memory_mb"),
            "metrics": metrics,
        },
        "bounded_guest_storage_observation": resource_probe,
        "resource_selection_surface": sorted(
            name
            for name in create_parameters
            if any(token in name.lower() for token in ("cpu", "memory", "mem", "disk", "storage"))
        ),
        "interpretation": (
            "The base template exposes a provider resource class and metrics, "
            "but this SDK create surface exposes no per-allocation CPU, memory, "
            "or storage ceiling selector. Metrics are not enforcement proof."
        ),
    }


def filesystem_entry_record(entry: Any) -> dict[str, Any]:
    return {
        "name": entry.name,
        "type": enum_value(entry.type),
        "path": entry.path,
        "size": entry.size,
        "mode": entry.mode,
        "permissions": entry.permissions,
        "owner": entry.owner,
        "group": entry.group,
    }


def credential_like_name(name: str) -> bool:
    upper = name.upper()
    return name in KNOWN_SECRET_NAMES or any(
        marker in upper for marker in SECRET_NAME_MARKERS
    )


def environment_posture(sandbox: Sandbox) -> dict[str, Any]:
    names_record = command_record(
        sandbox,
        "environment-key-names",
        "env -0 | tr '\\0' '\\n' | cut -d= -f1 | sort",
    )
    raw_names = [
        line.strip()
        for line in command_output(names_record).splitlines()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", line.strip())
    ]
    sandbox_names = set(raw_names)
    host_names = set(os.environ)
    credential_names = sorted(name for name in sandbox_names if credential_like_name(name))
    copied_parent_names = sorted(
        name
        for name in sandbox_names & host_names
        if name not in SAFE_BASELINE_ENV_NAMES and name != SAFE_ENV_NAME
    )
    nonsecret_sandbox_names = sorted(
        name for name in sandbox_names if not credential_like_name(name)
    )
    return {
        "probe": names_record,
        "sandbox_key_names_nonsecret": nonsecret_sandbox_names,
        "sandbox_key_count": len(sandbox_names),
        "host_key_count": len(host_names),
        "credential_like_key_names": credential_names,
        "parent_keys_copied_beyond_safe_baseline": copied_parent_names,
        "safe_variable_present": SAFE_ENV_NAME in sandbox_names,
        "e2b_api_key_name_present": "E2B_API_KEY" in sandbox_names,
        "known_codexify_or_provider_credential_names_present": bool(credential_names),
        "minimal_allowlist_observation": (
            names_record.get("status") == "completed"
            and not copied_parent_names
            and SAFE_ENV_NAME in sandbox_names
        ),
    }


def safe_kill_and_confirm(sandbox: Sandbox | None) -> dict[str, Any]:
    if sandbox is None:
        return {"kill_called": False, "kill_returned": None, "is_running": None}
    result: dict[str, Any] = {"kill_called": True}
    try:
        result["kill_returned"] = sandbox.kill()
    except Exception as exc:
        result["kill_exception_type"] = type(exc).__name__
    try:
        result["is_running"] = sandbox.is_running(request_timeout=5)
    except Exception as exc:
        result["is_running_exception_type"] = type(exc).__name__
        result["is_running"] = False
    result["confirmed_destroyed"] = result.get("is_running") is False
    return result


def create_sandbox(metadata: dict[str, str], timeout: int) -> Sandbox:
    return Sandbox.create(
        template="base",
        timeout=timeout,
        lifecycle={"on_timeout": "kill"},
        metadata=metadata,
        envs={SAFE_ENV_NAME: "safe-test-value"},
        secure=True,
        allow_internet_access=False,
        network={"deny_out": lambda context: [context.all_traffic]},
    )


def install_probe_transport() -> dict[str, Any]:
    """Use the host resolver for this probe's E2B control transport only.

    The maintained SDK's pyqwest resolver incorrectly appends this host's
    Tailscale search suffix to api.e2b.app. The SDK exposes a system-DNS
    transport option, so use that option without changing provider behavior or
    the production application. The same transport is used for control-plane
    REST and sandbox envd calls so the probe does not create a second authority
    path.
    """
    import e2b.api.client_sync as api_client_sync
    import e2b.envd.client_sync as envd_client_sync

    transport = SyncHTTPTransport(
        tls_include_system_certs=True,
        use_system_dns=True,
        follow_redirects=False,
    )

    def get_transport(
        config: Any,
        http2: bool = True,
        *,
        for_streaming: bool = False,
    ) -> PyqwestTransport:
        del config, http2, for_streaming
        return PyqwestTransport(transport)

    def get_pyqwest_transport(
        proxy: Any,
        read_timeout: float | None = None,
        http2: bool = True,
    ) -> SyncHTTPTransport:
        del proxy, read_timeout, http2
        return transport

    api_client_sync.get_transport = get_transport
    api_client_sync.get_pyqwest_transport = get_pyqwest_transport
    envd_client_sync.get_pyqwest_transport = get_pyqwest_transport
    return {
        "transport": "E2B SDK pyqwest SyncHTTPTransport",
        "use_system_dns": True,
        "tls_include_system_certs": True,
        "scope": "probe process only; no production integration",
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        help="Optional repository-relative or absolute JSON output path.",
    )
    args = parser.parse_args()

    started_at = now()
    report: dict[str, Any] = {
        "probe_version": PROBE_VERSION,
        "started_at": started_at,
        "sdk_version": EXPECTED_SDK_VERSION,
        "credential_source": "E2B_API_KEY environment variable; value withheld",
        "provider": "E2B Cloud hosted service",
        "provider_endpoint_identity": "default E2B Cloud control plane",
        "allocations": [],
        "warnings": [],
    }

    if not os.environ.get("E2B_API_KEY"):
        report.update(
            {
                "probe_status": "blocked",
                "blocker": "LIVE_E2B_CREDENTIAL_UNAVAILABLE",
                "completed_at": now(),
            }
        )
        emit(report, args.output)
        return 2

    try:
        installed_sdk_version = __import__("importlib.metadata", fromlist=["version"]).version(
            "e2b"
        )
    except Exception as exc:
        report.update(
            {
                "probe_status": "error",
                "fatal_exception_type": type(exc).__name__,
                "completed_at": now(),
            }
        )
        emit(report, args.output)
        return 2
    report["installed_sdk_version"] = installed_sdk_version
    if installed_sdk_version != EXPECTED_SDK_VERSION:
        report.update(
            {
                "probe_status": "error",
                "blocker": "PINNED_E2B_SDK_VERSION_NOT_INSTALLED",
                "completed_at": now(),
            }
        )
        emit(report, args.output)
        return 2

    report["control_plane_probe_transport"] = install_probe_transport()

    sandboxes: list[Sandbox] = []
    primary: Sandbox | None = None
    peer: Sandbox | None = None
    timeout_sandbox: Sandbox | None = None
    try:
        principal_id = "proof-principal-20260831"
        task_id = "proof-task-20260831"
        workspace_id = "synthetic-workspace-20260831"
        grant_id = "proof-grant-read-exec-20260831"
        primary_metadata = {
            "codexify_probe": PROBE_VERSION,
            "execution_principal": principal_id,
            "source_task": task_id,
            "workspace": workspace_id,
            "grant": grant_id,
        }
        primary_created_at = now()
        primary = create_sandbox(primary_metadata, SANDBOX_TIMEOUT_SECONDS)
        sandboxes.append(primary)
        primary_info = get_info_record(primary)
        primary_alloc: dict[str, Any] = {
            "role": "primary-read-exec",
            "created_at": primary_created_at,
            "sandbox_id": primary.sandbox_id,
            "metadata": primary_info.get("metadata", {}),
            "provenance": {
                "sandbox_id": primary.sandbox_id,
                "sandbox_domain": primary_info.get("sandbox_domain"),
                "template_id": primary_info.get("template_id"),
                "template_name": primary_info.get("name"),
                "started_at": primary_info.get("started_at"),
                "end_at": primary_info.get("end_at"),
                "state": primary_info.get("state"),
                "cpu_count": primary_info.get("cpu_count"),
                "memory_mb": primary_info.get("memory_mb"),
                "envd_version": primary_info.get("envd_version"),
                "allow_internet_access": primary_info.get("allow_internet_access"),
                "network": primary_info.get("network"),
                "lifecycle": primary_info.get("lifecycle"),
                "volume_mounts": primary_info.get("volume_mounts"),
                "provider_endpoint_identity": report["provider_endpoint_identity"],
                "region": "not exposed by the inspected hosted API",
            },
            "commands": [],
        }
        report["principal_task_workspace_grant"] = {
            "execution_principal": principal_id,
            "source_task": task_id,
            "workspace": workspace_id,
            "grant": grant_id,
            "provider_binding": "metadata observation only; not Codexify authority",
        }

        identity = command_record(
            primary,
            "basic-isolated-foreground-execution",
            "printf 'cwd='; pwd; printf 'kernel='; uname -srm; printf 'uid='; id -u; printf 'user='; id -un",
        )
        primary_alloc["commands"].append(identity)
        identity_text = command_output(identity)
        host_path_probe = command_record(
            primary,
            "host-repository-path-not-visible",
            f"if test -e {shlex.quote(HOST_REPOSITORY_PATH)}; then exit 17; else exit 0; fi",
        )
        primary_alloc["commands"].append(host_path_probe)
        primary_alloc["isolated_allocation"] = {
            "command_completed": not command_failed(identity),
            "foreground_exit_observable": identity.get("exit_code") == 0,
            "cwd_is_not_host_repository": host_path_probe.get("exit_code") == 0,
            "identity_observation": identity_text,
        }

        nonce = uuid.uuid4().hex[:12]
        workspace = f"/tmp/codexify-adr077-workspace-{nonce}"
        scratch = f"/tmp/codexify-adr077-scratch-{nonce}"
        fixture = {
            "readme.txt": b"codexify-e2b-synthetic-read-fixture-v1\n",
            "nested/marker.txt": b"nested-fixture-marker-v1\n",
            "nested/checksum.bin": bytes(range(32)),
        }
        expected_fixture = {
            path: {
                "size": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
            for path, data in fixture.items()
        }
        primary.files.make_dir(workspace)
        primary.files.make_dir(f"{workspace}/nested")
        primary.files.make_dir(scratch)
        for relative_path, data in fixture.items():
            primary.files.write(f"{workspace}/{relative_path}", data)
        primary.files.write(f"{workspace}/delete-target.txt", b"delete target\n")
        primary.files.write(f"{workspace}/rename-target.txt", b"rename target\n")

        entries = primary.files.list(workspace, depth=3)
        materialized: dict[str, Any] = {}
        for relative_path, expected in expected_fixture.items():
            absolute_path = f"{workspace}/{relative_path}"
            raw = primary.files.read(absolute_path, format="bytes")
            materialized[relative_path] = {
                "exists": True,
                "size": len(raw),
                "sha256": hashlib.sha256(bytes(raw)).hexdigest(),
                "matches_expected": bytes(raw) == fixture[relative_path],
            }
        cat_probe = command_record(
            primary,
            "workspace-command-read",
            f"cat {shlex.quote(workspace + '/readme.txt')}",
        )
        primary_alloc["commands"].append(cat_probe)
        primary_alloc["workspace_materialization"] = {
            "workspace_path": workspace,
            "fixture_expected": expected_fixture,
            "materialized_readback": materialized,
            "listed_entries": [filesystem_entry_record(entry) for entry in entries],
            "command_read_matches": command_output(cat_probe) == fixture["readme.txt"].decode(),
            "unrelated_host_path_probe": host_path_probe.get("exit_code") == 0,
        }

        primary_alloc["environment"] = environment_posture(primary)

        api_signature = inspect.signature(Sandbox.create)
        create_parameter_names = set(api_signature.parameters)
        primary_alloc["filesystem_api_surface"] = {
            "sandbox_create_has_volume_mounts": "volume_mounts" in create_parameter_names,
            "sandbox_create_has_read_only_parameter": any(
                "read_only" in name.lower() or "readonly" in name.lower()
                for name in create_parameter_names
            ),
            "read_only_provider_mount_surface": "unsupported",
            "evidence_class": "installed SDK surface inspection; not documentation-only",
        }

        chmod_prepare = command_record(
            primary,
            "prepare-guest-permission-only-readonly-attempt",
            f"chmod 0555 {shlex.quote(workspace)}; chmod 0444 {shlex.quote(workspace + '/readme.txt')}; chmod 0444 {shlex.quote(workspace + '/delete-target.txt')}; chmod 0444 {shlex.quote(workspace + '/rename-target.txt')}",
        )
        primary_alloc["commands"].append(chmod_prepare)
        mutation_commands = {
            "create": f"touch {shlex.quote(workspace + '/unauthorized-create.txt')}",
            "modify": f"printf unauthorized > {shlex.quote(workspace + '/readme.txt')}",
            "delete": f"rm {shlex.quote(workspace + '/delete-target.txt')}",
            "rename": f"mv {shlex.quote(workspace + '/rename-target.txt')} {shlex.quote(workspace + '/renamed-target.txt')}",
        }
        mutation_attempts = {}
        for mutation, command in mutation_commands.items():
            result = command_record(primary, f"protected-workspace-{mutation}", command)
            primary_alloc["commands"].append(result)
            mutation_attempts[mutation] = {
                "exit_code": result.get("exit_code"),
                "blocked_by_command_result": command_failed(result),
                "record": result,
            }
        mode_bypass = command_record(
            primary,
            "prove-guest-mode-is-not-provider-readonly",
            f"chmod u+w {shlex.quote(workspace)} {shlex.quote(workspace + '/readme.txt')}; printf bypassed > {shlex.quote(workspace + '/readme.txt')}",
        )
        primary_alloc["commands"].append(mode_bypass)
        scratch_probe = command_record(
            primary,
            "authorized-writable-scratch",
            f"printf scratch-ok > {shlex.quote(scratch + '/allowed.txt')}",
        )
        primary_alloc["commands"].append(scratch_probe)
        primary_alloc["read_only_workspace"] = {
            "result": "READ_ONLY_WORKSPACE_UNSUPPORTED",
            "provider_mount_option": "not present in Sandbox.create or inspected volume-mount surface",
            "guest_permission_setup_exit_code": chmod_prepare.get("exit_code"),
            "mutation_attempts": mutation_attempts,
            "guest_mode_bypass_exit_code": mode_bypass.get("exit_code"),
            "guest_mode_bypass_succeeded": mode_bypass.get("exit_code") == 0,
            "actual_provider_enforced_readonly": False,
            "authorized_scratch": {
                "path": scratch,
                "write_exit_code": scratch_probe.get("exit_code"),
                "write_succeeded": scratch_probe.get("exit_code") == 0,
            },
        }

        dns_probe = command_record(
            primary,
            "network-dns-behavior",
            "if command -v getent >/dev/null 2>&1; then getent hosts example.com; else exit 127; fi",
        )
        primary_alloc["commands"].append(dns_probe)
        http_probe = command_record(
            primary,
            "network-application-request",
            "if command -v curl >/dev/null 2>&1; then curl -fsS --max-time 3 https://example.com/ >/dev/null; else exit 127; fi",
        )
        primary_alloc["commands"].append(http_probe)
        direct_ip_probe = command_record(
            primary,
            "network-direct-ip-application-request",
            "if command -v curl >/dev/null 2>&1; then curl -fsSk --max-time 3 https://1.1.1.1/ >/dev/null; else exit 127; fi",
        )
        primary_alloc["commands"].append(direct_ip_probe)
        network_info = primary_info.get("network") or {}
        network_tools_available = http_probe.get("exit_code") != 127 and direct_ip_probe.get("exit_code") != 127
        primary_alloc["network"] = {
            "requested": {
                "allow_internet_access": False,
                "deny_out": [ALL_TRAFFIC],
                "guest_firewall_commands_used": False,
            },
            "provider_returned": {
                "allow_internet_access": primary_info.get("allow_internet_access"),
                "deny_out": network_info.get("deny_out"),
            },
            "dns_probe": {
                "available": dns_probe.get("exit_code") != 127,
                "denied": (
                    dns_probe.get("status") != "completed"
                    or dns_probe.get("exit_code") not in (0, 127)
                ),
                "exit_code": dns_probe.get("exit_code"),
                "observation": (
                    "timeout while resolving under deny-all egress"
                    if dns_probe.get("exception_type") == "TimeoutException"
                    else dns_probe.get("status")
                ),
            },
            "application_probe": {
                "tools_available": network_tools_available,
                "hostname_request_denied": http_probe.get("exit_code") not in (None, 0, 127),
                "direct_ip_request_denied": direct_ip_probe.get("exit_code") not in (None, 0, 127),
                "hostname_exit_code": http_probe.get("exit_code"),
                "direct_ip_exit_code": direct_ip_probe.get("exit_code"),
            },
            "classification": "provider-enforced configuration plus live application-level observation",
        }
        control_plane_info = None
        control_plane_metrics = None
        try:
            control_plane_info = get_info_record(primary)
            control_plane_metrics = get_metrics_record(primary)
            control_plane_ok = True
        except Exception as exc:
            control_plane_ok = False
            primary_alloc["control_plane_exception_type"] = type(exc).__name__
        primary_alloc["provider_control_transport"] = {
            "get_info_succeeded": control_plane_info is not None,
            "get_metrics_succeeded": control_plane_metrics is not None,
            "control_plane_usable_while_command_egress_denied": control_plane_ok,
        }
        if control_plane_metrics is not None:
            primary_alloc["metrics"] = control_plane_metrics
            primary_alloc["resource_posture"] = resource_posture(
                primary,
                primary_info,
                control_plane_metrics,
            )

        output_probe = command_record(
            primary,
            "bounded-output-source",
            "head -c 65536 /dev/zero | tr '\\0' X",
        )
        primary_alloc["commands"].append(output_probe)
        primary_alloc["bounded_output"] = {
            "provider_returned_total_bytes": output_probe.get("stdout", {}).get("total_bytes"),
            "codexify_collection_limit_bytes": MAX_CAPTURE_BYTES,
            "codexify_stored_bytes": output_probe.get("stdout", {}).get("stored_bytes"),
            "codexify_truncated": output_probe.get("stdout", {}).get("truncated"),
            "provider_result_status": output_probe.get("status"),
            "adapter_side_bound_demonstrated": output_probe.get("stdout", {}).get("stored_bytes", 0) <= MAX_CAPTURE_BYTES,
        }

        timeout_metadata = {
            "codexify_probe": PROBE_VERSION,
            "execution_principal": principal_id,
            "source_task": task_id,
            "workspace": "synthetic-timeout-workspace-20260831",
            "grant": grant_id,
        }
        timeout_created_at = now()
        timeout_sandbox = create_sandbox(timeout_metadata, LIFECYCLE_TIMEOUT_SECONDS)
        sandboxes.append(timeout_sandbox)
        timeout_info = get_info_record(timeout_sandbox)
        timeout_command: dict[str, Any]
        timeout_started = time.monotonic()
        timeout_command = command_record(
            timeout_sandbox,
            "sandbox-lifecycle-timeout",
            "sleep 30",
            timeout=12,
        )
        timeout_elapsed = time.monotonic() - timeout_started
        timeout_running = True
        poll_count = 0
        while timeout_running and poll_count * POLL_SECONDS < MAX_POLL_SECONDS:
            try:
                timeout_running = timeout_sandbox.is_running(request_timeout=5)
            except Exception:
                timeout_running = False
            if timeout_running:
                time.sleep(POLL_SECONDS)
                poll_count += 1
        timeout_alloc = {
            "role": "lifecycle-timeout",
            "created_at": timeout_created_at,
            "sandbox_id": timeout_sandbox.sandbox_id,
            "provenance": {
                "sandbox_id": timeout_sandbox.sandbox_id,
                "template_id": timeout_info.get("template_id"),
                "started_at": timeout_info.get("started_at"),
                "end_at": timeout_info.get("end_at"),
                "state": timeout_info.get("state"),
                "cpu_count": timeout_info.get("cpu_count"),
                "memory_mb": timeout_info.get("memory_mb"),
                "envd_version": timeout_info.get("envd_version"),
                "allow_internet_access": timeout_info.get("allow_internet_access"),
                "network": timeout_info.get("network"),
                "lifecycle": timeout_info.get("lifecycle"),
            },
            "command": timeout_command,
            "elapsed_seconds": round(timeout_elapsed, 3),
            "running_after_expiry_poll": timeout_running,
            "poll_count": poll_count,
            "timeout_distinguishable_from_normal_exit": (
                timeout_command.get("status") != "completed"
                and not timeout_running
            ),
            "descendants_unreachable_after_timeout": not timeout_running,
        }
        report["allocations"].append(timeout_alloc)

        peer_metadata = {
            "codexify_probe": PROBE_VERSION,
            "execution_principal": "proof-principal-peer-20260831",
            "source_task": "proof-task-peer-20260831",
            "workspace": "synthetic-peer-workspace-20260831",
            "grant": "proof-grant-peer-read-20260831",
        }
        peer_created_at = now()
        peer = create_sandbox(peer_metadata, SANDBOX_TIMEOUT_SECONDS)
        sandboxes.append(peer)
        peer_info = get_info_record(peer)
        peer_marker_path = "/tmp/codexify-adr077-peer-sentinel.txt"
        peer.files.write(peer_marker_path, b"peer-only-sentinel-v1\n")
        peer_marker = peer.files.read(peer_marker_path, format="bytes")
        peer_visibility_probe = command_record(
            primary,
            "cross-allocation-filesystem-isolation",
            f"if test -e {shlex.quote(peer_marker_path)}; then exit 19; else exit 0; fi",
        )
        primary_alloc["commands"].append(peer_visibility_probe)
        peer_alloc = {
            "role": "peer-isolation-check",
            "created_at": peer_created_at,
            "sandbox_id": peer.sandbox_id,
            "metadata": peer_info.get("metadata", {}),
            "provenance": {
                "sandbox_id": peer.sandbox_id,
                "template_id": peer_info.get("template_id"),
                "started_at": peer_info.get("started_at"),
                "end_at": peer_info.get("end_at"),
                "state": peer_info.get("state"),
            },
            "peer_marker_sha256": hashlib.sha256(bytes(peer_marker)).hexdigest(),
        }
        primary_alloc["peer_isolation"] = {
            "peer_sandbox_id": peer.sandbox_id,
            "same_path_marker_created_in_peer": True,
            "primary_cannot_see_peer_path_exit_code": peer_visibility_probe.get("exit_code"),
            "primary_same_path_absent": peer_visibility_probe.get("exit_code") == 0,
            "separate_sandbox_ids": primary.sandbox_id != peer.sandbox_id,
            "cross_tenant_isolation": "unproven; both allocations use one E2B credential/team",
        }
        report["allocations"].append(peer_alloc)

        descendant_pid_path = f"{scratch}/descendant.pid"
        descendant_parent = command_record(
            primary,
            "background-descendant-parent-exit",
            f"sh -c 'sleep 30 >/dev/null 2>&1 & child=$!; printf \"%s\" \"$child\" > {descendant_pid_path}; exit 0'",
        )
        primary_alloc["commands"].append(descendant_parent)
        descendant_pid_text = primary.files.read(descendant_pid_path).strip()
        descendant_pid_match = re.fullmatch(r"[0-9]+", descendant_pid_text)
        descendant_pid = int(descendant_pid_text) if descendant_pid_match else None
        descendant_alive = None
        descendant_check = None
        if descendant_pid is not None:
            descendant_check = command_record(
                primary,
                "background-descendant-after-parent",
                f"if kill -0 {descendant_pid} 2>/dev/null; then exit 0; else exit 1; fi",
            )
            primary_alloc["commands"].append(descendant_check)
            descendant_alive = descendant_check.get("exit_code") == 0
        try:
            process_list = safe_process_records(primary.commands.list())
        except Exception as exc:
            process_list = []
            primary_alloc["process_list_exception_type"] = type(exc).__name__
        primary_alloc["background_process"] = {
            "parent_exit_code": descendant_parent.get("exit_code"),
            "descendant_pid_observed": descendant_pid is not None,
            "descendant_alive_after_parent_exit": descendant_alive,
            "running_processes_before_teardown": process_list,
        }
        primary_alloc["teardown"] = safe_kill_and_confirm(primary)
        primary = None
        peer_teardown = safe_kill_and_confirm(peer)
        peer = None
        timeout_teardown = safe_kill_and_confirm(timeout_sandbox)
        timeout_sandbox = None
        report["teardown"] = {
            "primary": primary_alloc["teardown"],
            "peer": peer_teardown,
            "timeout_sandbox": timeout_teardown,
        }
        report["allocations"].insert(0, primary_alloc)
        report["probe_status"] = "completed"
    except Exception as exc:
        report.update(
            {
                "probe_status": "error",
                "fatal_exception_type": type(exc).__name__,
                "fatal_stage": "live-provider-probe",
            }
        )
    finally:
        for sandbox in reversed(sandboxes):
            try:
                sandbox.kill()
            except Exception:
                pass

    report["completed_at"] = now()
    emit(report, args.output)
    return 0 if report.get("probe_status") == "completed" else 2


def emit(report: dict[str, Any], output_path: str | None) -> None:
    payload = json.dumps(report, sort_keys=True, separators=(",", ":"))
    if output_path:
        path = PurePosixPath(output_path)
        if not path.is_absolute():
            path = PurePosixPath(os.getcwd()) / path
        with open(str(path), "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.write("\n")
    else:
        print(payload)


if __name__ == "__main__":
    sys.exit(main())
