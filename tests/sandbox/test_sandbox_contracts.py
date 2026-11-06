"""Sandbox contract and policy tests."""

from __future__ import annotations

import pytest

from guardian.sandbox import contracts as c
from guardian.sandbox.policy import (
    assert_postures_supported,
    unsupported_postures,
)


def _request(**overrides):
    payload = {
        "contract_version": c.SANDBOX_CONTRACT_VERSION,
        "request_id": "req-1",
        "idempotency_key": "idem-1",
        "attempt_id": "att-1",
        "deadline_epoch": 1000.0,
        "principal": "worker",
        "lineage": {},
        "workspace": c.WorkspaceMaterialization(
            identity="ws", source="https://example.invalid/ws.tar"
        ),
        "command": "echo hello",
        "resources": c.ResourcePosture(
            timeout_seconds=60,
            cpu_millis=1000,
            memory_mb=2048,
            storage_bytes=1024 * 1024 * 1024,
        ),
    }
    payload.update(overrides)
    return c.SandboxRequest(**payload)


def test_request_requires_the_contract_version():
    with pytest.raises(ValueError):
        _request(contract_version="sandbox.execution.v0")


def test_request_rejects_an_empty_command():
    with pytest.raises(ValueError):
        _request(command="   ")


def test_workspace_requires_an_integrity_bound_source():
    with pytest.raises(ValueError):
        c.WorkspaceMaterialization(identity="ws", source="   ")


def test_working_directory_cannot_escape_the_workspace():
    with pytest.raises(ValueError):
        c.WorkspaceMaterialization(
            identity="ws", source="s", working_directory="../../etc"
        )
    with pytest.raises(ValueError):
        c.WorkspaceMaterialization(
            identity="ws", source="s", working_directory="/abs"
        )


def test_artifact_policy_never_permits_auto_publication():
    with pytest.raises(ValueError):
        c.ArtifactPolicy(publish=True)


def test_required_postures_follow_the_request_shape():
    request = _request()
    required = request.required_postures()
    assert c.POSTURE_READ_ONLY_WORKSPACE in required
    assert c.POSTURE_CPU_LIMIT in required
    assert c.POSTURE_MEMORY_LIMIT in required
    assert c.POSTURE_STORAGE_CEILING in required
    assert c.POSTURE_TIMEOUT in required
    assert c.POSTURE_TEARDOWN in required
    assert c.POSTURE_EGRESS_DENY in required
    # No secret references were supplied, so no secret posture is required.
    assert c.POSTURE_SECRET_ISOLATION not in required


def test_secret_references_require_the_secret_posture():
    request = _request(secrets=c.SecretPosture(refs=("GITHUB_TOKEN",)))
    assert c.POSTURE_SECRET_ISOLATION in request.required_postures()


def test_allowlist_network_requires_the_allowlist_posture():
    request = _request(network=c.NetworkPosture(mode=c.NETWORK_MODE_ALLOWLIST, allowlist=("github.com:443",)))
    assert c.POSTURE_EGRESS_ALLOWLIST in request.required_postures()
    assert c.POSTURE_EGRESS_DENY not in request.required_postures()


def test_unsupported_postures_are_reported():
    assert unsupported_postures(["a", "b"], ["a"]) == ("b",)


def test_policy_denies_an_unsupported_posture_before_allocation():
    request = _request()
    with pytest.raises(c.SandboxPolicyDenied) as excinfo:
        assert_postures_supported(request, [c.POSTURE_READ_ONLY_WORKSPACE], provider="x")
    assert excinfo.value.provider == "x"
    assert c.POSTURE_STORAGE_CEILING in excinfo.value.unsupported


def test_policy_allows_a_fully_supported_request():
    request = _request()
    supported = request.required_postures()
    assert_postures_supported(request, supported, provider="x")


def test_attested_posture_reports_unestablished_postures():
    attested = c.AttestedPosture(
        requested=("read_only_workspace", "storage_ceiling"),
        established=("read_only_workspace",),
        unestablished=("storage_ceiling",),
    )
    assert attested.conformant is False
