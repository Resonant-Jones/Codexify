#!/usr/bin/env python3
"""Bounded live Modal probe for the ADR-077 immediate read/exec posture.

This proof-only script uses synthetic fixtures and the stable Modal Sandbox API.
It never forwards the caller environment or Modal credentials into a Sandbox.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import io
import json
import os
import re
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import modal


EXPECTED_SDK_VERSION = "1.5.5"
PROBE_VERSION = "adr077-modal-read-exec-v1"
MAX_CAPTURE_BYTES = 4096
COMMAND_TIMEOUT_SECONDS = 15
SANDBOX_TIMEOUT_SECONDS = 180
LIFECYCLE_TIMEOUT_SECONDS = 10
SAFE_ENV_NAME = "CODEXIFY_MODAL_PROBE_SAFE"
WORKSPACE_MOUNT = "/workspace"
SCRATCH_PATH = "/tmp/codexify-scratch"
HOST_REPOSITORY_PATH = "/Volumes/Dev_SSD/Codexify-main"
CPU_REQUEST = 0.125
CPU_LIMIT = 0.25
MEMORY_REQUEST_MIB = 256
MEMORY_LIMIT_MIB = 384

KNOWN_SECRET_NAMES = {
    "MODAL_TOKEN_ID",
    "MODAL_TOKEN_SECRET",
    "E2B_API_KEY",
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "MINIMAX_API_KEY",
    "DATABASE_URL",
    "CODEXIFY_DATABASE_URL",
    "POSTGRES_PASSWORD",
    "REDIS_URL",
    "GITHUB_TOKEN",
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "GOOGLE_APPLICATION_CREDENTIALS",
}
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


def now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def credential_values() -> list[str]:
    values: list[str] = []
    for name in ("MODAL_TOKEN_ID", "MODAL_TOKEN_SECRET"):
        value = os.environ.get(name)
        if value:
            values.append(value)
    profile = Path.home() / ".modal.toml"
    if profile.is_file():
        try:
            import tomllib

            data = tomllib.loads(profile.read_text(encoding="utf-8"))
            for config in data.values():
                if isinstance(config, dict):
                    for name in ("token_id", "token_secret"):
                        value = config.get(name)
                        if isinstance(value, str) and value:
                            values.append(value)
        except Exception:
            pass
    return values


def redact(value: str) -> str:
    for secret in credential_values():
        value = value.replace(secret, "<redacted>")
    return value


def bounded_text(value: str | bytes | None) -> dict[str, Any]:
    if value is None:
        value = ""
    raw = value if isinstance(value, bytes) else value.encode("utf-8", errors="replace")
    stored = redact(raw[:MAX_CAPTURE_BYTES].decode("utf-8", errors="replace"))
    return {
        "total_bytes": len(raw),
        "stored_bytes": len(stored.encode("utf-8")),
        "truncated": len(raw) > MAX_CAPTURE_BYTES,
        "text": stored,
    }


def exception_record(exc: BaseException) -> dict[str, Any]:
    return {
        "exception_type": type(exc).__name__,
        "message": bounded_text(str(exc)),
    }


def run_command(
    sandbox: modal.Sandbox,
    label: str,
    *args: str,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    record: dict[str, Any] = {"label": label, "started_at": now()}
    try:
        process = sandbox.exec(*args, timeout=timeout)
        stdout = process.stdout.read()
        stderr = process.stderr.read()
        returncode = process.wait()
        record.update(
            {
                "status": "completed",
                "returncode": returncode,
                "stdout": bounded_text(stdout),
                "stderr": bounded_text(stderr),
            }
        )
    except Exception as exc:
        record.update({"status": "exception", **exception_record(exc)})
    record["completed_at"] = now()
    return record


def run_shell(
    sandbox: modal.Sandbox,
    label: str,
    command: str,
    *,
    timeout: int = COMMAND_TIMEOUT_SECONDS,
) -> dict[str, Any]:
    return run_command(sandbox, label, "bash", "-lc", command, timeout=timeout)


def succeeded(record: dict[str, Any]) -> bool:
    return record.get("status") == "completed" and record.get("returncode") == 0


def stdout_text(record: dict[str, Any]) -> str:
    return str(record.get("stdout", {}).get("text", ""))


def fixture() -> dict[str, bytes]:
    values = {
        "root.txt": b"Codexify Modal ADR-077 root fixture\n",
        "nested/marker.txt": b"nested synthetic marker\n",
        "nested/checksum.bin": bytes(range(32)),
    }
    for name in (
        "overwrite.txt",
        "append.txt",
        "delete.txt",
        "rename.txt",
        "chmod.txt",
        "restore.txt",
        "replace.txt",
        "hardlink.txt",
        "chown.txt",
    ):
        values[name] = ("fixture-" + name + "\n").encode()
    values["rename-dir/marker.txt"] = b"rename directory marker\n"
    values["chmod-dir/marker.txt"] = b"chmod directory marker\n"
    return values


def fixture_hashes(values: dict[str, bytes]) -> dict[str, str]:
    return {name: hashlib.sha256(value).hexdigest() for name, value in values.items()}


def upload_fixture(volume: modal.Volume, values: dict[str, bytes]) -> None:
    with volume.batch_upload() as batch:
        for relative, content in values.items():
            batch.put_file(io.BytesIO(content), "/" + relative, mode=0o644)


def read_volume_file(volume: modal.Volume, path: str) -> bytes:
    return b"".join(volume.read_file("/" + path.lstrip("/")))


def mutation_matrix(sandbox: modal.Sandbox) -> list[dict[str, Any]]:
    q = WORKSPACE_MOUNT
    attacks = [
        ("overwrite-existing-file", "content", f"printf mutated > {q}/overwrite.txt"),
        ("append-existing-file", "content", f"printf append >> {q}/append.txt"),
        ("create-new-file", "namespace", f"printf created > {q}/created.txt"),
        ("create-new-directory", "namespace", f"mkdir {q}/created-dir"),
        ("delete-protected-file", "namespace", f"rm {q}/delete.txt"),
        ("rename-protected-file", "namespace", f"mv {q}/rename.txt {q}/renamed.txt"),
        ("rename-protected-directory", "namespace", f"mv {q}/rename-dir {q}/renamed-dir"),
        ("change-file-permissions", "metadata", f"chmod 0444 {q}/chmod.txt"),
        ("change-directory-permissions", "metadata", f"chmod 0555 {q}/chmod-dir"),
        ("change-ownership", "metadata", f"chown 1234:1234 {q}/chown.txt"),
        (
            "restore-write-permission-and-modify",
            "reversibility",
            f"chmod 0444 {q}/restore.txt && chmod 0644 {q}/restore.txt && printf restored > {q}/restore.txt",
        ),
        (
            "temporary-file-rename-replacement",
            "namespace",
            f"printf replacement > {q}/.replace.tmp && mv {q}/.replace.tmp {q}/replace.txt",
        ),
        ("symlink-creation-inside-workspace", "namespace", f"ln -s /tmp {q}/symlink-created"),
        (
            "symlink-write-through-from-scratch",
            "reversibility",
            f"ln -sf {q}/root.txt {SCRATCH_PATH}/workspace-link && printf bypass > {SCRATCH_PATH}/workspace-link",
        ),
        (
            "hardlink-and-modify",
            "reversibility",
            f"ln {q}/hardlink.txt {q}/hardlink-alias.txt && printf bypass >> {q}/hardlink-alias.txt",
        ),
        ("mount-remount-writable", "reversibility", f"mount -o remount,rw {q}"),
    ]
    results: list[dict[str, Any]] = []
    for label, mutation_class, command in attacks:
        result = run_shell(sandbox, label, command)
        result["mutation_class"] = mutation_class
        result["mutation_succeeded"] = succeeded(result)
        results.append(result)
    return results


def environment_posture(sandbox: modal.Sandbox) -> dict[str, Any]:
    result = run_shell(
        sandbox,
        "environment-key-names-only",
        "env -0 | tr '\\0' '\\n' | cut -d= -f1 | sort",
    )
    names = sorted(
        {
            line.strip()
            for line in stdout_text(result).splitlines()
            if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", line.strip())
        }
    )
    credential_like = sorted(
        name
        for name in names
        if name in KNOWN_SECRET_NAMES
        or any(marker in name.upper() for marker in SECRET_NAME_MARKERS)
    )
    return {
        "command": result,
        "names_observed": names,
        "credential_like_names": credential_like,
        "values_inspected": False,
        "credential_non_disclosure_pass": not credential_like,
    }


def network_posture(sandbox: modal.Sandbox) -> dict[str, Any]:
    programs = {
        "dns-resolution-denied": """import socket,sys
try: socket.getaddrinfo('example.com', 443); sys.exit(1)
except Exception as exc: print(type(exc).__name__); sys.exit(0)""",
        "hostname-https-denied": """import sys,urllib.request
try: urllib.request.urlopen('https://example.com/', timeout=3); sys.exit(1)
except Exception as exc: print(type(exc).__name__); sys.exit(0)""",
        "direct-ip-denied": """import socket,sys
s=socket.socket(); s.settimeout(3)
try: s.connect(('1.1.1.1',443)); sys.exit(1)
except Exception as exc: print(type(exc).__name__); sys.exit(0)""",
    }
    results = [
        run_command(sandbox, label, "python", "-c", program, timeout=8)
        for label, program in programs.items()
    ]
    return {"results": results, "all_external_egress_denied": all(succeeded(item) for item in results)}


def parse_int(text: str) -> int | None:
    try:
        return int(text.strip())
    except (TypeError, ValueError):
        return None


def resource_posture(sandbox: modal.Sandbox) -> dict[str, Any]:
    cpu = run_shell(
        sandbox,
        "cpu-cgroup-limit",
        "if test -f /sys/fs/cgroup/cpu.max; then cat /sys/fs/cgroup/cpu.max; "
        "elif test -f /sys/fs/cgroup/cpu/cpu.cfs_quota_us; then "
        "paste -d' ' /sys/fs/cgroup/cpu/cpu.cfs_quota_us /sys/fs/cgroup/cpu/cpu.cfs_period_us; "
        "elif test -f /sys/fs/cgroup/cpu,cpuacct/cpu.cfs_quota_us; then "
        "paste -d' ' /sys/fs/cgroup/cpu,cpuacct/cpu.cfs_quota_us /sys/fs/cgroup/cpu,cpuacct/cpu.cfs_period_us; "
        "else exit 1; fi",
    )
    memory = run_shell(
        sandbox,
        "memory-cgroup-limit",
        "if test -f /sys/fs/cgroup/memory.max; then cat /sys/fs/cgroup/memory.max; "
        "elif test -f /sys/fs/cgroup/memory/memory.limit_in_bytes; then cat /sys/fs/cgroup/memory/memory.limit_in_bytes; "
        "else exit 1; fi",
    )
    cgroup_layout = run_shell(
        sandbox,
        "cgroup-layout",
        "cat /proc/self/cgroup; grep -E 'cgroup|cgroup2' /proc/mounts | head -20",
    )
    storage = run_shell(sandbox, "storage-observation", "df -B1 /tmp | tail -1")
    cpu_parts = stdout_text(cpu).strip().split()
    observed_cpu = None
    if len(cpu_parts) == 2 and cpu_parts[0] != "max":
        quota, period = parse_int(cpu_parts[0]), parse_int(cpu_parts[1])
        if quota is not None and period:
            observed_cpu = quota / period
    observed_memory = parse_int(stdout_text(memory))
    return {
        "requested_cpu": CPU_REQUEST,
        "hard_cpu_limit": CPU_LIMIT,
        "cpu_cgroup": cpu,
        "observed_cpu_limit": observed_cpu,
        "cpu_hard_ceiling": "HARD_CEILING_PROVEN" if observed_cpu is not None and observed_cpu <= CPU_LIMIT else "UNPROVEN",
        "requested_memory_mib": MEMORY_REQUEST_MIB,
        "hard_memory_limit_mib": MEMORY_LIMIT_MIB,
        "memory_cgroup": memory,
        "observed_memory_limit_bytes": observed_memory,
        "memory_hard_ceiling": "HARD_CEILING_PROVEN" if observed_memory == MEMORY_LIMIT_MIB * 1024 * 1024 else "UNPROVEN",
        "cgroup_layout": cgroup_layout,
        "storage_observation": storage,
        "storage_ceiling": "UNPROVEN",
        "storage_reason": "Stable Sandbox.create has no storage or disk ceiling parameter; df is measurement only.",
    }


def bounded_output_probe(sandbox: modal.Sandbox) -> dict[str, Any]:
    process = sandbox.exec(
        "python",
        "-c",
        "import sys; [sys.stdout.write('x'*79+'\\n') for _ in range(1024)]",
        timeout=10,
    )
    total = 0
    retained = bytearray()
    for chunk in process.stdout:
        raw = chunk.encode() if isinstance(chunk, str) else bytes(chunk)
        total += len(raw)
        remaining = MAX_CAPTURE_BYTES - len(retained)
        if remaining > 0:
            retained.extend(raw[:remaining])
    stderr = process.stderr.read()
    returncode = process.wait()
    return {
        "returncode": returncode,
        "provider_stdout_bytes_observed": total,
        "retained_stdout_bytes": len(retained),
        "retained_stderr": bounded_text(stderr),
        "limit_bytes": MAX_CAPTURE_BYTES,
        "truncated": total > len(retained),
        "pass": returncode == 0 and total > MAX_CAPTURE_BYTES and len(retained) == MAX_CAPTURE_BYTES,
    }


def terminate_and_confirm(sandbox: modal.Sandbox | None) -> dict[str, Any]:
    if sandbox is None:
        return {"attempted": False, "confirmed": False}
    result: dict[str, Any] = {"attempted": True, "sandbox_id": sandbox.object_id}
    try:
        result["terminate_returncode"] = sandbox.terminate(wait=True)
    except Exception as exc:
        result["terminate_error"] = exception_record(exc)
    try:
        result["poll_after_terminate"] = sandbox.poll()
        result["confirmed"] = result["poll_after_terminate"] is not None
    except Exception as exc:
        result["poll_error"] = exception_record(exc)
        result["confirmed"] = False
    return result


def lifecycle_timeout_probe(app: modal.App, image: modal.Image, tags: dict[str, str]) -> dict[str, Any]:
    sandbox: modal.Sandbox | None = None
    started = time.monotonic()
    result: dict[str, Any] = {"requested_timeout_seconds": LIFECYCLE_TIMEOUT_SECONDS}
    try:
        sandbox = modal.Sandbox.create(
            "bash",
            "-lc",
            "sleep 30",
            app=app,
            image=image,
            timeout=LIFECYCLE_TIMEOUT_SECONDS,
            block_network=True,
            cpu=(CPU_REQUEST, CPU_LIMIT),
            memory=(MEMORY_REQUEST_MIB, MEMORY_LIMIT_MIB),
            tags={**tags, "probe_role": "lifecycle-timeout"},
        )
        result["sandbox_id"] = sandbox.object_id
        try:
            result["wait_returncode"] = sandbox.wait(raise_on_termination=False)
        except Exception as exc:
            result["wait_error"] = exception_record(exc)
        result["elapsed_seconds"] = round(time.monotonic() - started, 3)
        result["poll_after_wait"] = sandbox.poll()
        result["timeout_distinguishable"] = (
            result["elapsed_seconds"] >= LIFECYCLE_TIMEOUT_SECONDS - 1
            and result["poll_after_wait"] is not None
        )
    except Exception as exc:
        result["probe_error"] = exception_record(exc)
    finally:
        result["teardown"] = terminate_and_confirm(sandbox)
    return result


def memory_limit_probe(app: modal.App, image: modal.Image, tags: dict[str, str]) -> dict[str, Any]:
    sandbox: modal.Sandbox | None = None
    result: dict[str, Any] = {"requested_mib": 128, "hard_limit_mib": 192}
    try:
        sandbox = modal.Sandbox.create(
            app=app,
            image=image,
            timeout=90,
            block_network=True,
            cpu=(CPU_REQUEST, CPU_LIMIT),
            memory=(128, 192),
            tags={**tags, "probe_role": "memory-limit"},
        )
        result["sandbox_id"] = sandbox.object_id
        result["cgroup_limit"] = run_shell(sandbox, "memory-limit-cgroup", "cat /sys/fs/cgroup/memory.max")
        result["normal_allocation"] = run_command(
            sandbox,
            "memory-normal-control",
            "python",
            "-c",
            "a=bytearray(16*1024*1024); print(len(a))",
        )
        result["events_before"] = run_shell(sandbox, "memory-events-before", "cat /sys/fs/cgroup/memory.events")
        result["over_limit_allocation"] = run_command(
            sandbox,
            "memory-over-limit",
            "python",
            "-c",
            "a=bytearray(384*1024*1024); print(len(a))",
            timeout=20,
        )
        result["events_after"] = run_shell(sandbox, "memory-events-after", "cat /sys/fs/cgroup/memory.events")
        result["normal_succeeded"] = succeeded(result["normal_allocation"])
        result["over_limit_terminated"] = not succeeded(result["over_limit_allocation"])
        result["hard_ceiling"] = (
            "HARD_CEILING_PROVEN"
            if result["normal_succeeded"] and result["over_limit_terminated"]
            else "UNPROVEN"
        )
    except Exception as exc:
        result["probe_error"] = exception_record(exc)
        result["hard_ceiling"] = "UNPROVEN"
    finally:
        result["teardown"] = terminate_and_confirm(sandbox)
    return result


def sdk_surface() -> dict[str, Any]:
    signature = inspect.signature(modal.Sandbox.create)
    parameters = list(signature.parameters)
    return {
        "modal_version": modal.__version__,
        "sandbox_api": "stable Sandbox API",
        "experimental_v2_used": False,
        "sandbox_create_parameters": parameters,
        "read_only_mount_parameter": "read_only" in inspect.signature(modal.Volume.with_mount_options).parameters,
        "storage_limit_parameter_present": any(name in parameters for name in ("storage", "disk", "disk_size")),
    }


def emit(report: dict[str, Any], output_path: str | None) -> None:
    payload = json.dumps(report, indent=2, sort_keys=True)
    payload = redact(payload)
    if output_path:
        Path(output_path).write_text(payload + "\n", encoding="utf-8")
    print(json.dumps({
        "probe_status": report.get("probe_status"),
        "conclusion": report.get("conclusion"),
        "report_sha256": hashlib.sha256(payload.encode()).hexdigest(),
    }, sort_keys=True))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output")
    args = parser.parse_args()

    if modal.__version__ != EXPECTED_SDK_VERSION:
        raise SystemExit(f"Expected Modal SDK {EXPECTED_SDK_VERSION}; found {modal.__version__}")

    attempt_id = "attempt-" + uuid.uuid4().hex
    lineage = {
        "execution_principal": "synthetic-principal-modal-proof",
        "task_id": "synthetic-task-adr077-modal",
        "workspace_id": "synthetic-workspace-modal-proof",
        "attempt_id": attempt_id,
        "grant_reference": "synthetic-read-exec-no-network-no-write",
    }
    tags = {
        "codexify_probe": PROBE_VERSION,
        "attempt_id": attempt_id[:40],
        "workspace_id": "synthetic-workspace-modal-proof",
    }
    values = fixture()
    expected_hashes = fixture_hashes(values)
    report: dict[str, Any] = {
        "probe_version": PROBE_VERSION,
        "started_at": now(),
        "credential_source": "local Modal profile; credential contents withheld and not forwarded",
        "sdk_surface": sdk_surface(),
        "lineage": lineage,
        "fixture_hashes_before": expected_hashes,
        "allocations": [],
    }
    app = modal.App("codexify-adr077-modal-conformance")
    image = modal.Image.debian_slim(python_version="3.12")
    primary: modal.Sandbox | None = None

    try:
        with app.run():
            report["app_id"] = app.app_id
            with modal.Volume.ephemeral(environment_name="main") as volume:
                report["volume"] = {
                    "kind": "ephemeral proof-only Volume",
                    "volume_id": volume.object_id,
                    "mount_primitive": "Volume.with_mount_options(read_only=True)",
                }
                upload_fixture(volume, values)
                primary = modal.Sandbox.create(
                    app=app,
                    image=image,
                    env={SAFE_ENV_NAME: "synthetic-safe-value"},
                    secrets=[],
                    timeout=SANDBOX_TIMEOUT_SECONDS,
                    block_network=True,
                    cpu=(CPU_REQUEST, CPU_LIMIT),
                    memory=(MEMORY_REQUEST_MIB, MEMORY_LIMIT_MIB),
                    volumes={WORKSPACE_MOUNT: volume.with_mount_options(read_only=True)},
                    tags={**tags, "probe_role": "primary-read-exec"},
                )
                report["allocations"].append({"role": "primary", "sandbox_id": primary.object_id})
                report["runtime_identity"] = run_shell(
                    primary,
                    "runtime-identity",
                    "printf 'uid=%s\\nuser=%s\\n' \"$(id -u)\" \"$(id -un)\"; uname -srm; pwd",
                )
                report["host_repository_path_absent"] = succeeded(
                    run_shell(primary, "host-repository-path-absent", f"test ! -e {HOST_REPOSITORY_PATH}")
                )
                read_hashes = run_shell(
                    primary,
                    "workspace-read-and-hash",
                    "find /workspace -maxdepth 3 -type f -print | sort; "
                    "sha256sum /workspace/root.txt /workspace/nested/marker.txt /workspace/nested/checksum.bin",
                )
                report["workspace_read"] = {
                    "command": read_hashes,
                    "pass": succeeded(read_hashes)
                    and all(expected_hashes[name] in stdout_text(read_hashes) for name in ("root.txt", "nested/marker.txt", "nested/checksum.bin")),
                }
                scratch = run_shell(
                    primary,
                    "writable-scratch",
                    f"mkdir -p {SCRATCH_PATH}; printf created > {SCRATCH_PATH}/a; "
                    f"printf modified >> {SCRATCH_PATH}/a; mv {SCRATCH_PATH}/a {SCRATCH_PATH}/b; "
                    f"rm {SCRATCH_PATH}/b",
                )
                report["writable_scratch"] = {"command": scratch, "pass": succeeded(scratch)}
                report["workspace_metadata_before"] = run_shell(
                    primary,
                    "workspace-metadata-before",
                    "stat -c '%n mode=%a uid=%u gid=%g' /workspace/chmod.txt /workspace/chmod-dir /workspace/chown.txt",
                )
                mutations = mutation_matrix(primary)
                report["workspace_mutations"] = mutations
                report["workspace_metadata_after"] = run_shell(
                    primary,
                    "workspace-metadata-after",
                    "stat -c '%n mode=%a uid=%u gid=%g' /workspace/chmod.txt /workspace/chmod-dir /workspace/chown.txt",
                )
                metadata_unchanged_in_session = (
                    succeeded(report["workspace_metadata_before"])
                    and succeeded(report["workspace_metadata_after"])
                    and stdout_text(report["workspace_metadata_before"])
                    == stdout_text(report["workspace_metadata_after"])
                )
                for item in mutations:
                    if item["mutation_class"] == "metadata":
                        item["command_returned_zero"] = item["mutation_succeeded"]
                        item["observed_metadata_effect"] = not metadata_unchanged_in_session
                        item["mutation_succeeded"] = not metadata_unchanged_in_session
                content_namespace_denied = all(
                    not item["mutation_succeeded"]
                    for item in mutations
                    if item["mutation_class"] in {"content", "namespace"}
                )
                reversal_denied = all(
                    not item["mutation_succeeded"]
                    for item in mutations
                    if item["mutation_class"] == "reversibility"
                )
                metadata_denied = all(
                    not item["mutation_succeeded"]
                    for item in mutations
                    if item["mutation_class"] == "metadata"
                )
                report["read_only_enforcement"] = {
                    "all_mutations_denied": all(not item["mutation_succeeded"] for item in mutations),
                    "content_and_namespace_mutations_denied": content_namespace_denied,
                    "metadata_mutations_denied": metadata_denied,
                    "metadata_unchanged_in_session": metadata_unchanged_in_session,
                    "enforcement_layer": "Modal stable read-only Volume mount; content, namespace, metadata, and reversal tested independently",
                    "guest_reversibility_denied": reversal_denied,
                }
                foreground = run_shell(primary, "foreground-execution", "printf foreground-ok")
                report["foreground_execution"] = {"command": foreground, "pass": succeeded(foreground)}
                report["network"] = network_posture(primary)
                listed = list(modal.Sandbox.list(tags={"attempt_id": attempt_id[:40]}))
                report["control_plane"] = {
                    "poll_while_network_blocked": primary.poll(),
                    "listed_sandbox_ids": [item.object_id for item in listed],
                    "preserved": primary.object_id in {item.object_id for item in listed} and primary.poll() is None,
                }
                report["environment"] = environment_posture(primary)
                report["provider_runtime_provenance"] = run_command(
                    primary,
                    "provider-runtime-provenance",
                    "python",
                    "-c",
                    "import json,os; print(json.dumps({k:os.environ.get(k) for k in ('MODAL_CLOUD_PROVIDER','MODAL_REGION','MODAL_IMAGE_ID')},sort_keys=True))",
                )
                report["resources"] = resource_posture(primary)
                report["bounded_output"] = bounded_output_probe(primary)
                background = run_shell(
                    primary,
                    "background-descendant-start",
                    f"sleep 120 >/dev/null 2>&1 & echo $! > {SCRATCH_PATH}/child.pid; cat {SCRATCH_PATH}/child.pid",
                )
                child_pid = stdout_text(background).strip().splitlines()[-1] if succeeded(background) else ""
                alive = run_shell(primary, "background-descendant-alive", f"kill -0 {child_pid}") if child_pid.isdigit() else {}
                report["descendant"] = {
                    "start": background,
                    "alive_after_parent_exit": bool(alive) and succeeded(alive),
                    "child_pid_recorded": child_pid.isdigit(),
                }
                primary_teardown = terminate_and_confirm(primary)
                report["descendant"]["whole_sandbox_teardown"] = primary_teardown
                try:
                    modal.Sandbox.from_id(primary.object_id).exec("kill", "-0", child_pid, timeout=3)
                    report["descendant"]["reachable_after_teardown"] = True
                except Exception as exc:
                    report["descendant"]["reachable_after_teardown"] = False
                    report["descendant"]["post_teardown_error_type"] = type(exc).__name__
                report["descendant"]["pass"] = (
                    report["descendant"]["alive_after_parent_exit"]
                    and primary_teardown.get("confirmed") is True
                    and report["descendant"]["reachable_after_teardown"] is False
                )
                primary = None

                verification = modal.Sandbox.create(
                    app=app,
                    image=image,
                    env={SAFE_ENV_NAME: "synthetic-safe-value"},
                    secrets=[],
                    timeout=60,
                    block_network=True,
                    cpu=(CPU_REQUEST, CPU_LIMIT),
                    memory=(MEMORY_REQUEST_MIB, MEMORY_LIMIT_MIB),
                    volumes={WORKSPACE_MOUNT: volume.with_mount_options(read_only=True)},
                    tags={**tags, "probe_role": "metadata-reconnect"},
                )
                report["allocations"].append({"role": "metadata-reconnect", "sandbox_id": verification.object_id})
                report["workspace_metadata_fresh_mount"] = run_shell(
                    verification,
                    "workspace-metadata-fresh-mount",
                    "stat -c '%n mode=%a uid=%u gid=%g' /workspace/chmod.txt /workspace/chmod-dir /workspace/chown.txt",
                )
                report["metadata_verification_teardown"] = terminate_and_confirm(verification)

                after_hashes = {name: hashlib.sha256(read_volume_file(volume, name)).hexdigest() for name in values}
                report["fixture_hashes_after"] = after_hashes
                report["source_integrity_preserved"] = after_hashes == expected_hashes

                timeout_result = lifecycle_timeout_probe(app, image, tags)
                report["allocations"].append({"role": "lifecycle-timeout", "sandbox_id": timeout_result.get("sandbox_id")})
                report["timeout"] = timeout_result
                memory_result = memory_limit_probe(app, image, tags)
                report["allocations"].append({"role": "memory-limit", "sandbox_id": memory_result.get("sandbox_id")})
                report["memory_limit_probe"] = memory_result
                report["ephemeral_volume_cleanup"] = {"context_exited": False}
            report["ephemeral_volume_cleanup"]["context_exited"] = True
            volume_id = report["volume"]["volume_id"]
            try:
                modal.Volume.from_id(volume_id)._instance_delete()
                report["ephemeral_volume_cleanup"]["explicit_delete_requested"] = True
            except Exception as exc:
                report["ephemeral_volume_cleanup"]["explicit_delete_error"] = exception_record(exc)
            try:
                modal.Volume.from_id(volume_id).info()
                report["ephemeral_volume_cleanup"]["confirmed_deleted"] = False
            except Exception as exc:
                report["ephemeral_volume_cleanup"]["confirmed_deleted"] = type(exc).__name__ == "NotFoundError"
                report["ephemeral_volume_cleanup"]["verification_exception_type"] = type(exc).__name__

        mandatory = {
            "isolated_allocation": bool(report.get("allocations", [{}])[0].get("sandbox_id")) and report.get("host_repository_path_absent") is True,
            "workspace_read": report.get("workspace_read", {}).get("pass") is True,
            "read_only_workspace": report.get("read_only_enforcement", {}).get("all_mutations_denied") is True,
            "guest_cannot_reverse": report.get("read_only_enforcement", {}).get("guest_reversibility_denied") is True,
            "writable_scratch": report.get("writable_scratch", {}).get("pass") is True,
            "foreground_execution": report.get("foreground_execution", {}).get("pass") is True,
            "command_network_denied": report.get("network", {}).get("all_external_egress_denied") is True,
            "control_plane_preserved": report.get("control_plane", {}).get("preserved") is True,
            "credential_non_disclosure": report.get("environment", {}).get("credential_non_disclosure_pass") is True,
            "timeout": report.get("timeout", {}).get("timeout_distinguishable") is True,
            "descendant_teardown": report.get("descendant", {}).get("pass") is True,
            "cpu_hard_ceiling": report.get("resources", {}).get("cpu_hard_ceiling") == "HARD_CEILING_PROVEN",
            "memory_hard_ceiling": report.get("memory_limit_probe", {}).get("hard_ceiling") == "HARD_CEILING_PROVEN",
            "storage_ceiling": report.get("resources", {}).get("storage_ceiling") == "HARD_CEILING_PROVEN",
            "bounded_output": report.get("bounded_output", {}).get("pass") is True,
            "teardown_confirmed": report.get("descendant", {}).get("whole_sandbox_teardown", {}).get("confirmed") is True,
            "volume_cleanup_confirmed": report.get("ephemeral_volume_cleanup", {}).get("confirmed_deleted") is True,
            "source_integrity": report.get("source_integrity_preserved") is True,
            "lineage": all(lineage.values()),
            "provider_provenance": report.get("sdk_surface", {}).get("modal_version") == EXPECTED_SDK_VERSION,
        }
        report["mandatory_gates"] = mandatory
        report["probe_status"] = "completed"
        if all(mandatory.values()):
            report["conclusion"] = "MODAL_READ_EXEC_CONFORMANT"
        elif mandatory["read_only_workspace"] and mandatory["guest_cannot_reverse"]:
            report["conclusion"] = "MODAL_READ_EXEC_PARTIALLY_CONFORMANT"
        else:
            report["conclusion"] = "MODAL_READ_EXEC_NONCONFORMANT"
    except Exception as exc:
        report["probe_status"] = "error"
        report["fatal_error"] = exception_record(exc)
    finally:
        if primary is not None:
            report["emergency_primary_teardown"] = terminate_and_confirm(primary)
        report["completed_at"] = now()
        emit(report, args.output)

    return 0 if report.get("probe_status") == "completed" else 2


if __name__ == "__main__":
    sys.exit(main())
