"""
Docker Cloud Sandbox provider.

Implements the provider-neutral contract in :mod:`guardian.sandbox.contracts`
against Docker Cloud Sandboxes, driven by the ``sbx`` CLI.

Storage posture (decision D2)
------------------------------
Docker Cloud Sandboxes expose **no** disk-size knob: the API surface takes
CPU and memory only, and the microVM root filesystem size is not a settable
parameter. ADR-077 nevertheless requires a hard storage ceiling and forbids a
provider silently allocating a wider class than policy allows.

This adapter therefore establishes the storage ceiling *inside* the sandbox
kernel rather than through a provider API parameter:

* the workspace is mounted read-only;
* the **only** writable path is a tmpfs created with an explicit ``size=``
  option;
* the ceiling is then **attested** from ``/proc/mounts`` -- the authoritative
  record of what the kernel actually mounted -- and compared against the
  requested ceiling.

If the tmpfs is missing, is not a tmpfs, has no discoverable size, or exceeds
the requested ceiling, the adapter reports a *boundary* failure and never
executes the command. It does not fall back to a wider posture.

Conformance status
-------------------
This adapter has **not** been proven against a live Docker account. It is
implemented against the documented ``sbx`` CLI surface and is unit-tested with
an injected command runner. A live conformance proof is required before this
provider may be claimed ADR-077 conformant in production.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shlex
import subprocess
import uuid
from dataclasses import dataclass, replace
from typing import Callable, Sequence

from ..contracts import (
    FAILURE_CLASS_BOUNDARY,
    FAILURE_CLASS_EXECUTION,
    POSTURE_CPU_LIMIT,
    POSTURE_EGRESS_ALLOWLIST,
    POSTURE_EGRESS_DENY,
    POSTURE_MEMORY_LIMIT,
    POSTURE_READ_ONLY_WORKSPACE,
    POSTURE_STORAGE_CEILING,
    POSTURE_TEARDOWN,
    POSTURE_TIMEOUT,
    SANDBOX_CONTRACT_VERSION,
    STATUS_BOUNDARY_FAILED,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_TIMEOUT,
    AttestedPosture,
    SandboxProvenance,
    SandboxRequest,
    SandboxResult,
)
from ..policy import assert_postures_supported

logger = logging.getLogger(__name__)

#: A command runner: argv in, ``(exit_code, stdout, stderr)`` out.
CommandRunner = Callable[[Sequence[str], int], "tuple[int, bytes, bytes]"]

WORKSPACE_PATH = "/workspace"
SCRATCH_PATH = "/scratch"
UPLOAD_PATH = "/tmp/workspace.tar"


def default_runner(argv: Sequence[str], timeout_seconds: int = 120) -> "tuple[int, bytes, bytes]":
    """Run ``argv`` and capture its output."""
    try:
        proc = subprocess.run(  # noqa: S603 - argv is built by this adapter
            list(argv),
            capture_output=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return 124, b"", b"sandbox cli timeout"
    except FileNotFoundError as exc:
        return 127, b"", str(exc).encode()
    return proc.returncode, proc.stdout or b"", proc.stderr or b""


@dataclass(frozen=True)
class _ExecOutcome:
    exit_code: int
    stdout: bytes
    stderr: bytes


class DockerCloudSandboxProvider:
    """Execute bounded requests inside a Docker Cloud Sandbox."""

    name = "docker_cloud"

    #: Postures this adapter can establish.
    #:
    #: ``secret_isolation`` is deliberately absent: this adapter does not yet
    #: establish a secret channel, so a request that carries secret references
    #: is denied before allocation instead of leaking values into argv.
    SUPPORTED_POSTURES = (
        POSTURE_READ_ONLY_WORKSPACE,
        POSTURE_EGRESS_DENY,
        POSTURE_EGRESS_ALLOWLIST,
        POSTURE_CPU_LIMIT,
        POSTURE_MEMORY_LIMIT,
        POSTURE_STORAGE_CEILING,
        POSTURE_TIMEOUT,
        POSTURE_TEARDOWN,
    )

    def __init__(
        self,
        *,
        runner: CommandRunner | None = None,
        sbx_binary: str | None = None,
        kit: str | None = None,
        region: str | None = None,
        name_prefix: str | None = None,
        workspace_resolver: Callable[[object], "tuple[str, str]"] | None = None,
    ):
        self._runner = runner or default_runner
        self._sbx_binary = sbx_binary or os.getenv("CODEXIFY_SANDBOX_SBX_BINARY", "sbx")
        self._kit = kit or os.getenv("CODEXIFY_SANDBOX_DOCKER_KIT", "codexify-sandbox")
        self._region = region or os.getenv("CODEXIFY_SANDBOX_DOCKER_REGION")
        self._name_prefix = name_prefix or os.getenv(
            "CODEXIFY_SANDBOX_DOCKER_NAME_PREFIX", "codexify-sbx"
        )
        self._workspace_resolver = workspace_resolver or self._default_workspace_resolver

    # --- registry surface --------------------------------------------------

    def supported_postures(self) -> tuple[str, ...]:
        return self.SUPPORTED_POSTURES

    # --- execution ---------------------------------------------------------

    def execute(self, request: SandboxRequest) -> SandboxResult:
        # Fail closed *before* allocation when the adapter cannot establish a
        # requested posture.
        assert_postures_supported(
            request, self.supported_postures(), provider=self.name
        )

        sandbox_name = f"{self._name_prefix}-{uuid.uuid4().hex[:12]}"
        provenance = SandboxProvenance(
            provider=self.name,
            adapter=self.name,
            template=self._kit,
            region=self._region,
            sandbox_id=sandbox_name,
        )

        # Resolve and integrity-check the workspace BEFORE anything is
        # allocated. A substituted archive must be refused without a sandbox
        # ever being created.
        try:
            local_source, digest = self._workspace_resolver(request.workspace)
        except Exception as exc:
            return self._result(
                request=request,
                provenance=provenance,
                status=STATUS_BOUNDARY_FAILED,
                failure_class=FAILURE_CLASS_BOUNDARY,
                reason=f"workspace_materialization_failed:{exc}",
                established=(),
                teardown_status="not_required",
            )

        return self._run_request(
            request, sandbox_name, provenance, local_source, digest
        )

    def _run_request(
        self,
        request: SandboxRequest,
        sandbox_name: str,
        provenance: SandboxProvenance,
        local_source: str,
        digest: str,
    ) -> SandboxResult:
        """
        Run the request and always tear the sandbox down.

        The teardown status is applied to the result *after* teardown runs, so
        a caller always learns whether the sandbox was released.
        """
        created = False
        outcome: SandboxResult | None = None
        try:
            create = self._create_sandbox(request, sandbox_name)
            if create.exit_code != 0:
                outcome = self._result(
                    request=request,
                    provenance=provenance,
                    status=STATUS_FAILED,
                    failure_class=FAILURE_CLASS_EXECUTION,
                    reason=f"sandbox_allocation_failed:{_first_line(create.stderr)}",
                    established=(),
                    teardown_status="not_required",
                )
            else:
                created = True
                outcome = self._execute_in_sandbox(
                    request, sandbox_name, provenance, local_source, digest
                )
        finally:
            if created:
                teardown = self._teardown(sandbox_name)
                teardown_status = (
                    "complete" if teardown.exit_code == 0 else "failed"
                )
                teardown_warning = None
                if teardown.exit_code != 0:
                    teardown_warning = (
                        f"sandbox_teardown_failed:{_first_line(teardown.stderr)}"
                    )
                    logger.error(
                        "sandbox teardown failed for %s: %s",
                        sandbox_name,
                        teardown_warning,
                    )
                if outcome is not None:
                    outcome = replace(
                        outcome,
                        teardown_status=teardown_status,
                        teardown_warning=teardown_warning,
                    )
        return outcome

    def _execute_in_sandbox(
        self,
        request: SandboxRequest,
        sandbox_name: str,
        provenance: SandboxProvenance,
        local_source: str,
        digest: str,
    ) -> SandboxResult:
        materialize = self._materialize_workspace(
            request, sandbox_name, local_source, digest
        )
        if materialize.exit_code != 0:
            return self._result(
                request=request,
                provenance=provenance,
                status=STATUS_BOUNDARY_FAILED,
                failure_class=FAILURE_CLASS_BOUNDARY,
                reason=(
                    "workspace_materialization_failed:"
                    f"{_first_line(materialize.stderr)}"
                ),
                established=(),
            )

        boundary = self._establish_boundaries(request, sandbox_name)
        if boundary.exit_code != 0:
            return self._result(
                request=request,
                provenance=provenance,
                status=STATUS_BOUNDARY_FAILED,
                failure_class=FAILURE_CLASS_BOUNDARY,
                reason=(
                    "boundary_not_established:"
                    f"{_first_line(boundary.stdout or boundary.stderr)}"
                ),
                established=(),
            )

        established = self._established_postures(request)
        run = self._run_command(request, sandbox_name)
        truncated = self._truncate(request, run)

        if run.exit_code == 124:
            return self._result(
                request=request,
                provenance=provenance,
                status=STATUS_TIMEOUT,
                failure_class=FAILURE_CLASS_EXECUTION,
                reason="command_timeout",
                established=established,
                stdout=truncated[0],
                stderr=truncated[1],
                output_truncated=truncated[2],
            )

        status = STATUS_COMPLETED if run.exit_code == 0 else STATUS_FAILED
        failure_class = None if run.exit_code == 0 else FAILURE_CLASS_EXECUTION
        reason = None if run.exit_code == 0 else f"command_exit_{run.exit_code}"

        return self._result(
            request=request,
            provenance=provenance,
            status=status,
            failure_class=failure_class,
            reason=reason,
            established=established,
            stdout=truncated[0],
            stderr=truncated[1],
            output_truncated=truncated[2],
            exit_code=run.exit_code,
        )

    # --- provider operations ------------------------------------------------

    def _create_sandbox(self, request: SandboxRequest, name: str) -> _ExecOutcome:
        argv = [
            self._sbx_binary,
            "--cloud",
            "create",
            "--name",
            name,
            "--ttl",
            f"{request.resources.timeout_seconds}s",
            "--on-timeout",
            "delete",
        ]
        if request.resources.cpu_millis is not None:
            argv += ["--cpus", str(max(1, round(request.resources.cpu_millis / 1000)))]
        if request.resources.memory_mb is not None:
            argv += ["--memory", f"{request.resources.memory_mb}m"]
        if request.network.mode == "allowlist":
            for host in request.network.allowlist:
                argv += ["--allow-network", host]
        argv.append(self._kit)
        return self._run(argv)

    def _materialize_workspace(
        self,
        request: SandboxRequest,
        name: str,
        local_source: str,
        digest: str,
    ) -> _ExecOutcome:
        upload = self._run(
            [self._sbx_binary, "--cloud", "cp", local_source, f"{name}:{UPLOAD_PATH}"]
        )
        if upload.exit_code != 0:
            return upload
        expected = (digest or "").strip()
        if expected:
            verify = self._exec(
                name,
                f"sha256sum {shlex.quote(UPLOAD_PATH)} | awk '{{print $1}}'",
            )
            actual = verify.stdout.decode("utf-8", "replace").strip()
            if actual != expected:
                return _ExecOutcome(
                    1,
                    b"",
                    f"workspace_digest_mismatch:{actual}".encode(),
                )
        return self._exec(
            name,
            f"mkdir -p {shlex.quote(WORKSPACE_PATH)} && "
            f"tar -xf {shlex.quote(UPLOAD_PATH)} -C {shlex.quote(WORKSPACE_PATH)}",
        )

    def _establish_boundaries(
        self, request: SandboxRequest, name: str
    ) -> _ExecOutcome:
        """
        Establish and attest the read-only workspace and the scratch cap.

        The scratch ceiling is enforced by the sandbox kernel through the
        tmpfs ``size=`` option and attested from ``/proc/mounts``.
        """
        storage_bytes = request.resources.storage_bytes or 0
        script = "\n".join(
            [
                "set -eu",
                f"WS={shlex.quote(WORKSPACE_PATH)}",
                f"SCRATCH={shlex.quote(SCRATCH_PATH)}",
                "mkdir -p \"$SCRATCH\"",
                # The tmpfs size option is the kernel-enforced ceiling: it caps
                # the only writable path the guest has.
                f"mount -t tmpfs -o size={storage_bytes} tmpfs \"$SCRATCH\"",
                # Attest the ceiling from the kernel's own mount table.
                "MOUNT_LINE=$(awk -v p=\"$SCRATCH\" '$2==p {print; exit}' /proc/mounts)",
                'case "$MOUNT_LINE" in *" tmpfs "*) ;; *) echo scratch_not_tmpfs; exit 41;; esac',
                'CAP=$(printf "%s" "$MOUNT_LINE" | sed -n "s/.*size=\\([0-9]*\\).*/\\1/p")',
                '[ -n "$CAP" ] || { echo scratch_cap_unknown; exit 42; }',
                f'[ "$CAP" -le {storage_bytes} ] || {{ echo scratch_cap_exceeded:$CAP; exit 43; }}',
                # Make the workspace read-only.
                'mount -o remount,ro "$WS" 2>/dev/null || { echo workspace_remount_failed; exit 44; }',
                # Attest read-only from the mount table and by effect.
                'WS_OPTS=$(awk -v p="$WS" \'$2==p {print $4; exit}\' /proc/mounts)',
                'case ",$WS_OPTS," in *,ro,*) ;; *) echo workspace_not_read_only; exit 45;; esac',
                'if touch "$WS/.codexify-ro-probe" 2>/dev/null; then',
                '  rm -f "$WS/.codexify-ro-probe" 2>/dev/null || true',
                '  echo workspace_writable; exit 46',
                'fi',
                "echo boundaries_established",
            ]
        )
        return self._exec(name, script)

    def _run_command(self, request: SandboxRequest, name: str) -> _ExecOutcome:
        relative = (request.workspace.working_directory or "").strip()
        if relative:
            workdir = f"{WORKSPACE_PATH}/{relative}"
            command = f"cd {shlex.quote(workdir)} && {request.command}"
        else:
            command = request.command
        return self._exec(name, command, timeout=request.resources.timeout_seconds)

    def _teardown(self, name: str) -> _ExecOutcome:
        return self._run([self._sbx_binary, "--cloud", "rm", "--force", name])

    # --- helpers ------------------------------------------------------------

    def _run(self, argv: Sequence[str], timeout: int = 120) -> _ExecOutcome:
        code, stdout, stderr = self._runner(argv, timeout)
        return _ExecOutcome(code, stdout, stderr)

    def _exec(
        self, name: str, command: str, timeout: int = 120
    ) -> _ExecOutcome:
        argv = [
            self._sbx_binary,
            "--cloud",
            "exec",
            name,
            "--",
            "sh",
            "-c",
            command,
        ]
        return self._run(argv, timeout)

    @staticmethod
    def _default_workspace_resolver(workspace) -> "tuple[str, str]":
        """
        Resolve a workspace to a local archive plus its digest.

        The default resolver treats ``workspace.source`` as a path to a
        prepared archive and content-addresses it. When the request declares a
        digest, the computed digest must match it, so a substituted archive is
        refused before it reaches the sandbox.

        A production deployment substitutes a resolver that materializes the
        integrity-bound source (for example a repository URL plus digest) on
        the worker side.
        """
        source = str(getattr(workspace, "source", "") or "")
        if not source:
            raise ValueError("workspace source is required")
        digest = hashlib.sha256()
        with open(source, "rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
        computed = digest.hexdigest()
        declared = str(getattr(workspace, "digest", "") or "").strip()
        if declared and declared != computed:
            raise ValueError(
                f"workspace digest mismatch: declared {declared}, computed {computed}"
            )
        return source, computed

    @staticmethod
    def _established_postures(request: SandboxRequest) -> tuple[str, ...]:
        established = []
        for posture in request.required_postures():
            if posture in DockerCloudSandboxProvider.SUPPORTED_POSTURES:
                established.append(posture)
        return tuple(established)

    @staticmethod
    def _truncate(
        request: SandboxRequest, run: _ExecOutcome
    ) -> "tuple[bytes, bytes, bool]":
        limit = max(0, int(request.resources.output_max_bytes))
        stdout, stderr = run.stdout, run.stderr
        truncated = False
        if len(stdout) > limit:
            stdout = stdout[:limit]
            truncated = True
        if len(stderr) > limit:
            stderr = stderr[:limit]
            truncated = True
        return stdout, stderr, truncated

    @staticmethod
    def _result(
        *,
        request: SandboxRequest,
        provenance: SandboxProvenance,
        status: str,
        established: tuple[str, ...],
        failure_class: str | None = None,
        reason: str | None = None,
        stdout: bytes = b"",
        stderr: bytes = b"",
        output_truncated: bool = False,
        exit_code: int | None = None,
        teardown_status: str = "unknown",
    ) -> SandboxResult:
        requested = request.required_postures()
        unestablished = tuple(p for p in requested if p not in established)
        return SandboxResult(
            contract_version=SANDBOX_CONTRACT_VERSION,
            request_id=request.request_id,
            attempt_id=request.attempt_id,
            status=status,
            provenance=provenance,
            attested_posture=AttestedPosture(
                requested=requested,
                established=established,
                unestablished=unestablished,
            ),
            exit_code=exit_code,
            reason=reason,
            failure_class=failure_class,
            stdout=stdout,
            stderr=stderr,
            output_truncated=output_truncated,
            teardown_status=teardown_status,
        )


def _first_line(payload: bytes | str) -> str:
    if isinstance(payload, bytes):
        text = payload.decode("utf-8", "replace")
    else:
        text = payload or ""
    line = text.strip().splitlines()[0] if text.strip() else ""
    return line[:200]


__all__ = ["DockerCloudSandboxProvider", "default_runner"]
