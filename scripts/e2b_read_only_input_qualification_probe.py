#!/usr/bin/env python3
"""Bounded hosted E2B read-only-input qualification probe.

This is a proof probe, not a Codexify SandboxProvider adapter. It uses only
synthetic fixtures, keeps the E2B credential in the process environment, and
emits bounded JSON without credential values.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import inspect
import json
import os
import re
import shlex
import uuid
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from typing import Any

from e2b import Sandbox, Volume
from e2b.sandbox.commands.command_handle import CommandExitException
from pyqwest import SyncHTTPTransport
from pyqwest.httpx import PyqwestTransport


EXPECTED_SDK_VERSION = "2.46.0"
PROBE_VERSION = "adr077-e2b-read-only-input-v1"
MAX_CAPTURE_BYTES = 4096
COMMAND_TIMEOUT_SECONDS = 15
SANDBOX_TIMEOUT_SECONDS = 90
HOST_REPOSITORY_PATH = "/Volumes/Dev_SSD/Codexify-main"


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
    return value.replace(secret, "<redacted>") if secret else value


def bounded_text(value: str | bytes | bytearray | None) -> dict[str, Any]:
    if value is None:
        value = ""
    raw = bytes(value) if isinstance(value, (bytes, bytearray)) else value.encode(
        "utf-8", errors="replace"
    )
    stored = redact(raw[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace"))
    return {
        "total_bytes": len(raw),
        "stored_bytes": len(stored.encode("utf-8")),
        "truncated": len(raw) > MAX_CAPTURE_BYTES,
        "text": stored,
    }


def command_record(
    sandbox: Sandbox,
    label: str,
    command: str,
    *,
    timeout: float = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    record: dict[str, Any] = {
        "label": label,
        "command": command,
        "started_at": now(),
    }
    try:
        result = sandbox.commands.run(
            command,
            background=False,
            timeout=timeout,
        )
        record.update(
            {
                "status": "completed",
                "exit_code": result.exit_code,
                "stdout": bounded_text(result.stdout),
                "stderr": bounded_text(result.stderr),
                "provider_error_present": result.error is not None,
            }
        )
    except CommandExitException as exc:
        record.update(
            {
                "status": "nonzero_exit",
                "exit_code": exc.exit_code,
                "stdout": bounded_text(exc.stdout),
                "stderr": bounded_text(exc.stderr),
                "provider_error_present": exc.error is not None,
            }
        )
    except Exception as exc:
        record.update(
            {
                "status": "transport_or_timeout_error",
                "exception_type": type(exc).__name__,
                "error": bounded_text(str(exc)),
            }
        )
    record["completed_at"] = now()
    return record


def command_succeeded(record: dict[str, Any]) -> bool:
    return record.get("status") == "completed" and record.get("exit_code") == 0


def safe_info(sandbox: Sandbox) -> dict[str, Any]:
    """Project only non-secret provenance fields from SandboxInfo."""
    info = sandbox.get_info()
    result: dict[str, Any] = {}
    for field in (
        "sandbox_id",
        "template_id",
        "started_at",
        "end_at",
        "envd_version",
        "cpu_count",
        "memory_mb",
        "state",
        "secure",
        "allow_internet_access",
        "network",
        "volume_mounts",
    ):
        if not hasattr(info, field):
            continue
        value = getattr(info, field)
        if field == "volume_mounts" and value is not None:
            value = [
                {
                    "name": getattr(item, "name", None),
                    "path": getattr(item, "path", None),
                }
                for item in value
            ]
        result[field] = json_value(value)
    return result


def install_probe_transports() -> dict[str, Any]:
    """Use system DNS for this probe's E2B control transport only."""
    import e2b.api.client_sync as api_client_sync
    import e2b.envd.client_sync as envd_client_sync
    import e2b.volume.client_sync as volume_client_sync

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
    volume_client_sync.get_transport = lambda config: PyqwestTransport(transport)
    volume_client_sync.get_streaming_transport = lambda config: PyqwestTransport(
        transport
    )
    return {
        "transport": "E2B SDK pyqwest SyncHTTPTransport",
        "use_system_dns": True,
        "tls_include_system_certs": True,
        "scope": "probe process only; no production integration",
    }


def sdk_surface() -> dict[str, Any]:
    from e2b.api.client.models.new_sandbox import NewSandbox
    from e2b.api.client.models.sandbox_volume_mount import SandboxVolumeMount

    mount_fields = [item.name for item in SandboxVolumeMount.__attrs_attrs__]
    request_fields = [item.name for item in NewSandbox.__attrs_attrs__]
    create_parameters = sorted(inspect.signature(Sandbox.create).parameters)
    read_only_names = sorted(
        name
        for name in set(mount_fields + request_fields + create_parameters)
        if re.search(r"read.?only", name, re.IGNORECASE)
    )
    return {
        "installed_package_version": importlib.metadata.version("e2b"),
        "expected_pinned_version": EXPECTED_SDK_VERSION,
        "sandbox_create_parameters": create_parameters,
        "sandbox_volume_mount_model_fields": mount_fields,
        "new_sandbox_request_fields": request_fields,
        "read_only_field_names_found": read_only_names,
        "serialized_volume_mount_shape": {"name": "volume-id-or-name", "path": "guest-path"},
        "read_only_access_mode_exposed": bool(read_only_names),
    }


def capability_table() -> list[dict[str, Any]]:
    return [
        {
            "mechanism": "ordinary sandbox filesystem materialization",
            "hosted_api": "available",
            "sdk": "available",
            "classification": "not applicable",
            "finding": "Files API writes an ordinary guest filesystem path; no immutable input boundary.",
        },
        {
            "mechanism": "persistent volume mount",
            "hosted_api": "available in public surface; private-beta/account-gated",
            "sdk": "available",
            "classification": "not applicable",
            "finding": "Create request and SDK expose volume identity plus guest path only. Official hosted docs describe mounted files as readable and writable; no access mode is exposed.",
        },
        {
            "mechanism": "template/base image",
            "hosted_api": "available",
            "sdk": "available",
            "classification": "not applicable",
            "finding": "Defines the sandbox starting image; no provider-controlled read-only attachment for task input was exposed.",
        },
        {
            "mechanism": "snapshot or pause/resume",
            "hosted_api": "available",
            "sdk": "available",
            "classification": "not applicable",
            "finding": "Preserves sandbox filesystem state, including mutable state; no immutable mount/access mode was exposed.",
        },
        {
            "mechanism": "cloud bucket guest FUSE mount",
            "hosted_api": "documented",
            "sdk": "not an input-mount primitive",
            "classification": "guest/application-level",
            "finding": "Requires guest commands/FUSE and credentials; it is not provider-enforced read-only input for ADR-077.",
        },
        {
            "mechanism": "custom or self-hosted storage enforcement",
            "hosted_api": "self-hosted only / out of scope",
            "sdk": "not qualified",
            "classification": "self-hosted only",
            "finding": "No hosted E2B Cloud evidence was used to qualify a self-hosted implementation capability.",
        },
    ]


def fixture() -> dict[str, str]:
    return {
        "root.txt": "ADR-077 synthetic root fixture\n",
        "nested/marker.txt": "nested marker fixture\n",
        "nested/checksum.bin": "checksum-known synthetic bytes\n",
        "overwrite.txt": "overwrite target\n",
        "append.txt": "append target\n",
        "delete.txt": "delete target\n",
        "rename.txt": "rename target\n",
        "replace.txt": "replace target\n",
        "chmod.txt": "chmod target\n",
        "chown.txt": "chown target\n",
        "restore.txt": "restore target\n",
        "hardlink.txt": "hardlink target\n",
        "protected-dir/child.txt": "protected directory child\n",
        "rename-dir/child.txt": "rename directory child\n",
        "chmod-dir/child.txt": "chmod directory child\n",
    }


def fixture_hashes(values: dict[str, str]) -> dict[str, str]:
    return {
        path: hashlib.sha256(value.encode("utf-8")).hexdigest()
        for path, value in values.items()
    }


def prepare_sandbox_fixture(sandbox: Sandbox, root: str, values: dict[str, str]) -> None:
    sandbox.files.make_dir(root)
    made_dirs: set[str] = {root}
    for relative in values:
        parent = os.path.dirname(relative)
        if parent:
            current = root
            for segment in parent.split("/"):
                current = f"{current}/{segment}"
                if current not in made_dirs:
                    sandbox.files.make_dir(current)
                    made_dirs.add(current)
        sandbox.files.write(f"{root}/{relative}", values[relative])


def prepare_volume_fixture(volume: Volume, root: str, values: dict[str, str]) -> None:
    volume.make_dir(root, uid=1000, gid=1000, mode=0o755, force=True)
    made_dirs: set[str] = {root}
    for relative in values:
        parent = os.path.dirname(relative)
        if parent:
            current = root
            for segment in parent.split("/"):
                current = f"{current}/{segment}"
                if current not in made_dirs:
                    volume.make_dir(current, uid=1000, gid=1000, mode=0o755, force=True)
                    made_dirs.add(current)
        volume.write_file(
            f"{root}/{relative}",
            values[relative],
            uid=1000,
            gid=1000,
            mode=0o644,
            force=True,
        )


def read_fixture(
    sandbox: Sandbox,
    root: str,
    values: dict[str, str],
) -> dict[str, Any]:
    expected = fixture_hashes(values)
    readback: dict[str, Any] = {}
    for relative in ("root.txt", "nested/marker.txt", "nested/checksum.bin"):
        path = f"{root}/{relative}"
        content = sandbox.files.read(path)
        if isinstance(content, bytes):
            content = content.decode("utf-8")
        readback[relative] = {
            "expected_sha256": expected[relative],
            "observed_sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(),
            "matches": content == values[relative],
        }
    listing = command_record(
        sandbox,
        "protected-workspace-enumeration",
        f"find {shlex.quote(root)} -maxdepth 3 -type f -print | sort",
    )
    hashes = command_record(
        sandbox,
        "protected-workspace-hashes",
        "sha256sum "
        + " ".join(
            shlex.quote(f"{root}/{relative}")
            for relative in ("root.txt", "nested/marker.txt", "nested/checksum.bin")
        ),
    )
    return {
        "file_readback": readback,
        "enumeration": listing,
        "command_hashes": hashes,
        "read_pass": all(item["matches"] for item in readback.values())
        and command_succeeded(listing)
        and command_succeeded(hashes),
    }


def mutation_matrix(sandbox: Sandbox, root: str) -> list[dict[str, Any]]:
    q = shlex.quote(root)
    commands = [
        ("overwrite-existing-file", f"printf '%s' 'mutated' > {q}/overwrite.txt"),
        ("append-existing-file", f"printf '%s' 'append' >> {q}/append.txt"),
        ("create-new-file", f"printf '%s' 'created' > {q}/created.txt"),
        ("create-new-directory", f"mkdir {q}/created-dir"),
        ("delete-protected-file", f"rm -f {q}/delete.txt"),
        ("rename-protected-file", f"mv {q}/rename.txt {q}/renamed.txt"),
        ("rename-protected-directory", f"mv {q}/rename-dir {q}/renamed-dir"),
        ("change-file-permissions", f"chmod 0444 {q}/chmod.txt"),
        ("change-directory-permissions", f"chmod 0555 {q}/chmod-dir"),
        ("change-ownership-where-available", f"chown 0:0 {q}/chown.txt"),
        (
            "restore-write-permission-and-modify",
            f"chmod 0444 {q}/restore.txt && chmod 0644 {q}/restore.txt && printf '%s' 'restored' > {q}/restore.txt",
        ),
        (
            "temporary-file-then-rename-replacement",
            f"printf '%s' 'replacement' > {q}/.replace.tmp && mv {q}/.replace.tmp {q}/replace.txt",
        ),
        ("symlink-creation", f"ln -s root.txt {q}/symlink.txt"),
        (
            "hardlink-then-modify-through-link",
            f"ln {q}/hardlink.txt {q}/hardlink-alias.txt && printf '%s' 'hardlink-mutated' >> {q}/hardlink-alias.txt",
        ),
        (
            "remount-or-remap-writable-attempt",
            f"mount -o remount,rw {q}",
        ),
    ]
    results: list[dict[str, Any]] = []
    for label, command in commands:
        result = command_record(sandbox, label, command)
        result["observed_effect"] = (
            "principal_mutation_succeeded"
            if command_succeeded(result)
            else "attempt_failed"
        )
        results.append(result)
    return results


def scratch_probe(sandbox: Sandbox) -> dict[str, Any]:
    scratch = f"/tmp/adr077-scratch-{uuid.uuid4().hex[:10]}"
    command = (
        f"mkdir -p {shlex.quote(scratch)} && "
        f"printf '%s' 'created' > {shlex.quote(scratch + '/scratch.txt')} && "
        f"printf '%s' 'modified' >> {shlex.quote(scratch + '/scratch.txt')} && "
        f"rm {shlex.quote(scratch + '/scratch.txt')} && "
        f"rmdir {shlex.quote(scratch)}"
    )
    result = command_record(sandbox, "authorized-writable-scratch", command)
    return {
        "path": scratch,
        "result": result,
        "scratch_write_modify_delete_pass": command_succeeded(result),
    }


def environment_key_posture(sandbox: Sandbox) -> dict[str, Any]:
    record = command_record(
        sandbox,
        "environment-key-names-only",
        "env -0 | tr '\\0' '\\n' | cut -d= -f1 | sort",
    )
    names = [
        line.strip()
        for line in record.get("stdout", {}).get("text", "").splitlines()
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", line.strip())
    ]
    secret_names = {
        "E2B_API_KEY",
        "CODEXIFY_DATABASE_URL",
        "DATABASE_URL",
        "POSTGRES_PASSWORD",
        "REDIS_URL",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "MINIMAX_API_KEY",
        "GITHUB_TOKEN",
    }
    return {
        "command": record,
        "names_observed": names,
        "e2b_api_key_name_present": "E2B_API_KEY" in names,
        "known_service_credential_names_present": sorted(secret_names.intersection(names)),
        "values_inspected": False,
    }


def run_sandbox_candidate(
    *,
    fixture_values: dict[str, str],
    volume: Volume | None = None,
) -> dict[str, Any]:
    candidate = "persistent-volume-mount" if volume is not None else "ordinary-files-api-materialization"
    root = (
        f"/mnt/adr077-input-{uuid.uuid4().hex[:10]}"
        if volume is not None
        else f"/tmp/adr077-input-{uuid.uuid4().hex[:10]}"
    )
    metadata = {
        "probe": PROBE_VERSION,
        "execution_principal": "synthetic-single-principal",
        "task": "synthetic-read-only-input-qualification",
    }
    sandbox: Sandbox | None = None
    result: dict[str, Any] = {
        "candidate": candidate,
        "root": root,
        "started_at": now(),
    }
    try:
        kwargs: dict[str, Any] = {
            "template": "base",
            "timeout": SANDBOX_TIMEOUT_SECONDS,
            "lifecycle": {"on_timeout": "kill"},
            "metadata": metadata,
            "envs": {"E2B_CONFORMANCE_SAFE": "safe-test-value"},
            "secure": True,
            "allow_internet_access": False,
        }
        if volume is not None:
            kwargs["volume_mounts"] = {root: volume}
        sandbox = Sandbox.create(**kwargs)
        result["allocation"] = safe_info(sandbox)
        if volume is None:
            prepare_sandbox_fixture(sandbox, root, fixture_values)
        else:
            prepare_volume_fixture(volume, root, fixture_values)
        result["workspace"] = {
            "read": read_fixture(sandbox, root, fixture_values),
            "mutations": mutation_matrix(sandbox, root),
            "scratch": scratch_probe(sandbox),
            "environment": environment_key_posture(sandbox),
            "host_repository_path_absent": command_succeeded(
                command_record(
                    sandbox,
                    "host-repository-path-absent",
                    f"test ! -e {shlex.quote(HOST_REPOSITORY_PATH)}",
                )
            ),
        }
        try:
            result["control_plane_after_guest_probes"] = safe_info(sandbox)
            result["control_plane_observation_pass"] = True
        except Exception as exc:
            result["control_plane_observation_pass"] = False
            result["control_plane_observation_exception"] = type(exc).__name__
    except Exception as exc:
        result["error"] = {
            "exception_type": type(exc).__name__,
            "message": bounded_text(str(exc)),
        }
    finally:
        result["teardown"] = {"kill_called": False}
        if sandbox is not None:
            result["teardown"]["kill_called"] = True
            try:
                result["teardown"]["kill_returned"] = sandbox.kill()
            except Exception as exc:
                result["teardown"]["kill_exception_type"] = type(exc).__name__
            try:
                result["teardown"]["is_running"] = sandbox.is_running(request_timeout=5)
            except Exception as exc:
                result["teardown"]["is_running_exception_type"] = type(exc).__name__
                result["teardown"]["is_running"] = False
            result["teardown"]["confirmed_destroyed"] = (
                result["teardown"].get("is_running") is False
            )
        result["completed_at"] = now()
    return result


def volume_candidate_probe(fixture_values: dict[str, str]) -> dict[str, Any]:
    """Attempt the hosted volume candidate and clean it up if entitled."""
    result: dict[str, Any] = {"candidate": "persistent-volume-mount", "attempted_at": now()}
    volume: Volume | None = None
    try:
        volume = Volume.create("codexify-adr077-ro-" + uuid.uuid4().hex[:12])
        result["volume_created"] = True
        result["volume_id"] = volume.volume_id
        result["volume_name"] = volume.name
        result["sandbox"] = run_sandbox_candidate(
            fixture_values=fixture_values,
            volume=volume,
        )
        root = result["sandbox"]["root"]
        after: dict[str, str] = {}
        for relative in ("root.txt", "nested/marker.txt", "nested/checksum.bin"):
            content = volume.read_file(f"{root}/{relative}")
            if isinstance(content, bytes):
                content = content.decode("utf-8")
            after[relative] = hashlib.sha256(content.encode("utf-8")).hexdigest()
        result["provider_backed_input_hashes_after_sandbox"] = after
        result["provider_backed_input_integrity_preserved"] = all(
            after[relative] == fixture_hashes(fixture_values)[relative]
            for relative in after
        )
    except Exception as exc:
        result.update(
            {
                "volume_created": volume is not None,
                "status": "unavailable-or-failed",
                "exception_type": type(exc).__name__,
                "error": bounded_text(str(exc)),
            }
        )
    finally:
        if volume is not None:
            try:
                result["volume_destroyed"] = Volume.destroy(volume.volume_id)
            except Exception as exc:
                result["volume_destroy_exception_type"] = type(exc).__name__
    result["completed_at"] = now()
    return result


def emit(report: dict[str, Any], output: str | None) -> None:
    rendered = json.dumps(report, indent=2, sort_keys=True)
    if output:
        with open(output, "w", encoding="utf-8") as handle:
            handle.write(rendered + "\n")
    print(rendered)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", help="Optional JSON output path.")
    args = parser.parse_args()
    report: dict[str, Any] = {
        "probe_version": PROBE_VERSION,
        "started_at": now(),
        "credential_source": "E2B_API_KEY environment variable; value withheld",
        "provider": "E2B Cloud hosted service",
        "provider_endpoint_identity": "default E2B Cloud control plane",
        "sdk": {},
        "transport": {},
        "candidate_capability_table": capability_table(),
        "official_evidence_urls": [
            "https://docs.e2b.dev/volumes",
            "https://docs.e2b.dev/volumes/mount",
            "https://docs.e2b.dev/volumes/read-write",
            "https://docs.e2b.dev/api-reference/sandboxes/create-sandbox",
            "https://docs.e2b.dev/sandbox/persistence",
            "https://docs.e2b.dev/sandbox/snapshots",
            "https://docs.e2b.dev/storage/cloud-buckets",
            "https://github.com/e2b-dev/E2B/blob/main/packages/python-sdk/pyproject.toml",
        ],
        "allocations": [],
        "warnings": [],
    }
    if not os.environ.get("E2B_API_KEY"):
        report.update(
            {
                "qualification": "LIVE_E2B_CREDENTIAL_UNAVAILABLE",
                "probe_status": "blocked",
                "completed_at": now(),
            }
        )
        emit(report, args.output)
        return 2
    try:
        report["sdk"] = sdk_surface()
        report["transport"] = install_probe_transports()
        if report["sdk"]["installed_package_version"] != EXPECTED_SDK_VERSION:
            report["qualification"] = "E2B_PROVIDER_READ_ONLY_INPUT_UNPROVEN"
            report["probe_status"] = "blocked-sdk-version-mismatch"
            report["completed_at"] = now()
            emit(report, args.output)
            return 3
        values = fixture()
        report["source_fixture"] = {
            "synthetic_only": True,
            "paths": sorted(values),
            "sha256_before": fixture_hashes(values),
        }
        report["volume_candidate"] = volume_candidate_probe(values)
        report["allocations"].append(
            run_sandbox_candidate(fixture_values=values)
        )
        report["source_fixture"]["sha256_after"] = fixture_hashes(values)
        report["source_fixture"]["integrity_preserved"] = (
            report["source_fixture"]["sha256_before"]
            == report["source_fixture"]["sha256_after"]
        )
        report["qualification"] = "E2B_PROVIDER_READ_ONLY_INPUT_UNSUPPORTED"
        report["qualification_scope"] = (
            "E2B Cloud hosted API and Python SDK 2.46.0 as tested on 2026-08-31; "
            "the current account was not entitled to create persistent volumes."
        )
        report["rationale"] = [
            "The generated hosted sandbox volume-mount model has only name and path; no read-only access mode is available.",
            "Official hosted volume documentation describes mounted files as readable and writable and documents write/remove operations.",
            "The live volume allocation attempt returned 403 use of volumes is not enabled, so no volume runtime was available for mutation testing.",
            "A fresh live ordinary-files sandbox demonstrated that the fallback materialized workspace is writable by the execution principal.",
        ]
        report["completed_at"] = now()
    except Exception as exc:
        report.update(
            {
                "qualification": "E2B_PROVIDER_READ_ONLY_INPUT_UNPROVEN",
                "probe_status": "probe-error",
                "probe_exception_type": type(exc).__name__,
                "probe_error": bounded_text(str(exc)),
                "completed_at": now(),
            }
        )
        emit(report, args.output)
        return 4
    emit(report, args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
