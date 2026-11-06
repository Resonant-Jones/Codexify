"""Docker Cloud Sandbox adapter tests.

The adapter is exercised through an injected command runner, so these tests
prove the contract behaviour (posture denial, boundary attestation, bounded
output, teardown) without a live Docker account. A live conformance proof is
still required before the provider may be claimed ADR-077 conformant.
"""

from __future__ import annotations

import pytest

from guardian.sandbox import contracts as c
from guardian.sandbox.adapters.docker_cloud import DockerCloudSandboxProvider


class FakeSbx:
    """A scripted `sbx` runner."""

    def __init__(self, *, boundary=(0, b"boundaries_established\n", b""), command=(0, b"out", b"")):
        self.calls: list[list[str]] = []
        self.boundary = boundary
        self.command = command
        self.create_result = (0, b"created", b"")

    def __call__(self, argv, timeout=120):
        argv = list(argv)
        self.calls.append(argv)
        joined = " ".join(argv)
        if "--cloud" in argv and "create" in argv:
            return self.create_result
        if "--cloud" in argv and "cp" in argv:
            return (0, b"", b"")
        if "--cloud" in argv and "rm" in argv:
            return (0, b"", b"")
        if "--cloud" in argv and "exec" in argv:
            command = argv[-1]
            if "mount -t tmpfs" in command:
                return self.boundary
            if "sha256sum" in command:
                return (0, b"digest\n", b"")
            if "tar -xf" in command:
                return (0, b"", b"")
            return self.command
        return (0, b"", b"")

    def exec_commands(self):
        return [c[-1] for c in self.calls if "exec" in c]


@pytest.fixture
def workspace_archive(tmp_path):
    archive = tmp_path / "workspace.tar"
    archive.write_bytes(b"workspace")
    return str(archive)


def _request(archive, **overrides):
    payload = {
        "contract_version": c.SANDBOX_CONTRACT_VERSION,
        "request_id": "req-1",
        "idempotency_key": "idem-1",
        "attempt_id": "att-1",
        "deadline_epoch": 1000.0,
        "principal": "worker",
        "lineage": {},
        "workspace": c.WorkspaceMaterialization(
            identity="ws", source=archive, digest="digest"
        ),
        "command": "echo hello",
        "resources": c.ResourcePosture(
            timeout_seconds=60,
            cpu_millis=1000,
            memory_mb=2048,
            storage_bytes=1024 * 1024 * 1024,
            output_max_bytes=1024,
        ),
    }
    payload.update(overrides)
    return c.SandboxRequest(**payload)


def _provider(runner, workspace_archive):
    return DockerCloudSandboxProvider(
        runner=runner,
        workspace_resolver=lambda workspace: (workspace_archive, "digest"),
    )


def test_supported_postures_exclude_secret_isolation():
    provider = DockerCloudSandboxProvider(runner=FakeSbx())
    assert c.POSTURE_SECRET_ISOLATION not in provider.supported_postures()
    assert c.POSTURE_STORAGE_CEILING in provider.supported_postures()


def test_a_request_with_secrets_is_denied_before_allocation(workspace_archive):
    runner = FakeSbx()
    provider = _provider(runner, workspace_archive)
    request = _request(
        workspace_archive, secrets=c.SecretPosture(refs=("GITHUB_TOKEN",))
    )
    with pytest.raises(c.SandboxPolicyDenied) as excinfo:
        provider.execute(request)
    assert c.POSTURE_SECRET_ISOLATION in excinfo.value.unsupported
    # Nothing was allocated: no sandbox was created.
    assert not any("create" in call for call in runner.calls)


def test_a_successful_execution_attests_every_requested_posture(workspace_archive):
    runner = FakeSbx()
    provider = _provider(runner, workspace_archive)
    result = provider.execute(_request(workspace_archive))

    assert result.status == c.STATUS_COMPLETED
    assert result.exit_code == 0
    assert result.stdout == b"out"
    assert result.failure_class is None
    assert result.attested_posture.conformant is True
    assert result.attested_posture.unestablished == ()
    assert result.teardown_status == "complete"


def test_the_workspace_is_materialized_before_the_command_runs(workspace_archive):
    runner = FakeSbx()
    provider = _provider(runner, workspace_archive)
    provider.execute(_request(workspace_archive))

    commands = runner.exec_commands()
    assert any("sha256sum" in command for command in commands)
    assert any("tar -xf" in command for command in commands)
    assert commands.index(next(c for c in commands if "tar -xf" in c)) < commands.index(
        "echo hello"
    )


def test_the_scratch_cap_is_kernel_enforced_and_attested(workspace_archive):
    runner = FakeSbx()
    provider = _provider(runner, workspace_archive)
    provider.execute(_request(workspace_archive))

    boundary = next(c for c in runner.exec_commands() if "mount -t tmpfs" in c)
    # The tmpfs is created with an explicit size, and the ceiling is read
    # back from the kernel's own mount table rather than assumed.
    assert "mount -t tmpfs -o size=1073741824" in boundary
    assert "/proc/mounts" in boundary
    assert "scratch_cap_exceeded" in boundary
    assert "workspace_not_read_only" in boundary


def test_a_boundary_failure_is_reported_as_a_boundary_failure(workspace_archive):
    runner = FakeSbx(boundary=(43, b"scratch_cap_exceeded:2147483648\n", b""))
    provider = _provider(runner, workspace_archive)
    result = provider.execute(_request(workspace_archive))

    assert result.status == c.STATUS_BOUNDARY_FAILED
    assert result.boundary_failed is True
    assert result.failure_class == c.FAILURE_CLASS_BOUNDARY
    assert "scratch_cap_exceeded" in (result.reason or "")
    # The command never ran.
    assert "echo hello" not in runner.exec_commands()


def test_output_is_bounded(workspace_archive):
    runner = FakeSbx(command=(0, b"x" * 5000, b"y" * 5000))
    provider = _provider(runner, workspace_archive)
    result = provider.execute(_request(workspace_archive))

    assert result.output_truncated is True
    assert len(result.stdout) <= 1024
    assert len(result.stderr) <= 1024


def test_the_sandbox_is_torn_down_after_a_failure(workspace_archive):
    runner = FakeSbx(boundary=(43, b"scratch_cap_exceeded\n", b""))
    provider = _provider(runner, workspace_archive)
    provider.execute(_request(workspace_archive))

    assert any("rm" in call for call in runner.calls)


def test_a_nonzero_exit_is_an_execution_failure_not_a_boundary_failure(workspace_archive):
    runner = FakeSbx(command=(2, b"", b"boom"))
    provider = _provider(runner, workspace_archive)
    result = provider.execute(_request(workspace_archive))

    assert result.status == c.STATUS_FAILED
    assert result.failure_class == c.FAILURE_CLASS_EXECUTION
    assert result.exit_code == 2


def test_a_declared_workspace_digest_mismatch_is_refused(workspace_archive):
    """A substituted archive must not reach the sandbox."""
    import hashlib

    real = hashlib.sha256(open(workspace_archive, "rb").read()).hexdigest()
    runner = FakeSbx()
    provider = DockerCloudSandboxProvider(runner=runner)
    request = _request(
        workspace_archive,
        workspace=c.WorkspaceMaterialization(
            identity="ws", source=workspace_archive, digest="deadbeef"
        ),
    )
    with pytest.raises(ValueError) as excinfo:
        DockerCloudSandboxProvider(runner=runner)._default_workspace_resolver(
            request.workspace
        )
    assert "digest mismatch" in str(excinfo.value)


def test_a_substituted_workspace_is_refused_before_allocation(workspace_archive):
    """A substituted archive must not cause a sandbox to be created."""
    runner = FakeSbx()
    provider = DockerCloudSandboxProvider(runner=runner)
    request = _request(
        workspace_archive,
        workspace=c.WorkspaceMaterialization(
            identity="ws", source=workspace_archive, digest="deadbeef"
        ),
    )
    result = provider.execute(request)
    assert result.status == c.STATUS_BOUNDARY_FAILED
    assert result.failure_class == c.FAILURE_CLASS_BOUNDARY
    assert "digest mismatch" in (result.reason or "")
    # Nothing was created or uploaded.
    assert not runner.calls


def test_the_working_directory_is_applied_inside_the_workspace(workspace_archive):
    runner = FakeSbx()
    provider = _provider(runner, workspace_archive)
    request = _request(workspace_archive)
    request = c.SandboxRequest(
        **{
            **request.__dict__,
            "workspace": c.WorkspaceMaterialization(
                identity="ws",
                source=workspace_archive,
                digest="digest",
                working_directory="src/pkg",
            ),
        }
    )
    provider.execute(request)

    assert any("cd /workspace/src/pkg && echo hello" in cmd for cmd in runner.exec_commands())
