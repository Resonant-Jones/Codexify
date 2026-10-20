"""Guardian permission posture contract (Slice 4).

The Guardian Delegation Loop must resolve an *enforceable* permission posture
before dispatch. These cases prove the posture is derived from trusted context,
that a caller proposal cannot widen it, and — the part that matters most — that
the posture never claims enforcement the runtime does not provide.

ADR-077 rule 6: "Denied filesystem mutation is enforced below the model/tool
layer." Rule 7: "Tool allowlists and prompt instructions are defense in depth,
not sufficient filesystem, network, or process isolation."

See ``guardian/core/guardian_permission_posture.py``.
"""

from __future__ import annotations

from typing import Any

import pytest

from guardian.core.guardian_permission_posture import (
    GUARDIAN_CODING_MAX_RUNTIME_SECONDS,
    GuardianPermissionPostureError,
    resolve_guardian_permission_posture,
    validate_guardian_permission_posture,
)


def _posture(**overrides: Any):  # noqa: ANN201
    kwargs: dict[str, Any] = {
        "account_id": "account-1",
        "provider_id": "openai",
        "model_id": "gpt-4o",
        "repo_root": "/workspace/project",
        "allowed_paths": ("",),
        "allow_write": True,
        "allow_shell": True,
        "allow_network": False,
    }
    kwargs.update(overrides)
    return resolve_guardian_permission_posture(**kwargs)


def test_posture_carries_the_resolved_policy() -> None:
    """The resolved policy is the request the worker and adapter consume."""
    posture = _posture()

    policy = posture.permission_policy
    assert policy["allow_write"] is True
    assert policy["allow_shell"] is True
    assert policy["allow_network"] is False
    assert policy["allowed_paths"] == [""]
    assert policy["max_runtime_seconds"] == GUARDIAN_CODING_MAX_RUNTIME_SECONDS


def test_posture_records_which_surfaces_enforce_it() -> None:
    """The posture states what actually backs each capability."""
    posture = _posture()

    assert "git_mutation_guard" in posture.enforced_surfaces
    assert "validation_shell_gate" in posture.enforced_surfaces
    assert "worktree_lease_isolation" in posture.enforced_surfaces


def test_posture_does_not_claim_network_enforcement() -> None:
    """Network egress is a request, not an enforced boundary here.

    No sandbox provider is wired into the coding worker, so the posture must
    not present `allow_network` as an enforcement guarantee.
    """
    posture = _posture(allow_network=True)

    assert "network_egress" in posture.advisory_surfaces
    assert "network_egress" not in posture.enforced_surfaces
    # The note must say plainly that the flag is a request only.
    notes = " ".join(posture.notes)
    assert "not enforced" in notes or "not an egress guarantee" in notes


def test_posture_does_not_claim_process_isolation() -> None:
    """There is no OS-level process isolation in this runtime."""
    posture = _posture()

    assert "process_isolation" in posture.advisory_surfaces
    notes = " ".join(posture.notes)
    assert "not an isolation guarantee" in notes


def test_posture_states_that_the_mutation_guard_detects_rather_than_prevents() -> None:
    """The guard is a detection boundary; it does not prevent the write."""
    posture = _posture()

    notes = " ".join(posture.notes)
    assert "detects the mutation" in notes
    assert "does not prevent" in notes


def test_posture_withholds_shell_when_not_requested() -> None:
    """With allow_shell false the capability is genuinely withheld."""
    posture = _posture(allow_shell=False)

    assert posture.permission_policy["allow_shell"] is False
    notes = " ".join(posture.notes)
    assert "not executed" in notes


def test_posture_fails_closed_without_account_identity() -> None:
    """A posture without an account identity is refused."""
    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(account_id="")

    assert excinfo.value.code == "guardian_posture_account_missing"


def test_posture_fails_closed_without_provider_or_model() -> None:
    """Provider and model must be present; they are part of the authorization."""
    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(provider_id="")

    assert excinfo.value.code == "guardian_posture_provider_missing"

    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(model_id="")

    assert excinfo.value.code == "guardian_posture_model_missing"


def test_posture_fails_closed_when_write_scope_is_unresolved() -> None:
    """A write request with no bound working tree is not authorizable."""
    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(repo_root=None)

    assert excinfo.value.code == "guardian_posture_write_scope_unresolved"


def test_posture_fails_closed_when_write_scope_is_missing() -> None:
    """A write request with no path scope would authorize the whole tree."""
    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(allowed_paths=())

    assert excinfo.value.code == "guardian_posture_write_scope_missing"


def test_posture_fails_closed_on_invalid_runtime_limit() -> None:
    """A non-positive runtime limit is refused."""
    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        _posture(max_runtime_seconds=0)

    assert excinfo.value.code == "guardian_posture_runtime_limit_invalid"


def test_read_only_posture_needs_no_working_tree() -> None:
    """A read-only task has no write scope to resolve."""
    posture = _posture(repo_root=None, allow_write=False, allowed_paths=())

    assert posture.permission_policy["allow_write"] is False
    assert "read_only_tool_surface" in posture.enforced_surfaces


def test_validation_refuses_a_widened_write_grant() -> None:
    """A posture that dropped an authorized capability is refused."""
    posture = _posture(allow_write=False, allowed_paths=())

    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        validate_guardian_permission_posture(
            posture,
            requested_allow_write=True,
            requested_allow_shell=True,
            requested_allow_network=False,
        )

    assert excinfo.value.code == "guardian_posture_write_grant_missing"


def test_validation_refuses_a_widened_shell_grant() -> None:
    """A posture that dropped shell authorization is refused."""
    posture = _posture(allow_shell=False)

    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        validate_guardian_permission_posture(
            posture,
            requested_allow_write=True,
            requested_allow_shell=True,
            requested_allow_network=False,
        )

    assert excinfo.value.code == "guardian_posture_shell_grant_missing"


def test_validation_refuses_a_widened_network_grant() -> None:
    """A posture that dropped network authorization is refused."""
    posture = _posture(allow_network=False)

    with pytest.raises(GuardianPermissionPostureError) as excinfo:
        validate_guardian_permission_posture(
            posture,
            requested_allow_write=True,
            requested_allow_shell=True,
            requested_allow_network=True,
        )

    assert excinfo.value.code == "guardian_posture_network_grant_missing"


def test_validation_accepts_a_posture_that_grants_what_was_requested() -> None:
    """The resolved posture satisfies the request it answers."""
    posture = _posture()

    validate_guardian_permission_posture(
        posture,
        requested_allow_write=True,
        requested_allow_shell=True,
        requested_allow_network=False,
    )


def test_posture_serializes_its_enforcement_provenance() -> None:
    """The posture carries its provenance so it can be recorded and audited."""
    posture = _posture()
    payload = posture.to_dict()

    assert payload["permission_policy"]["allow_write"] is True
    assert "git_mutation_guard" in payload["enforced_surfaces"]
    assert "process_isolation" in payload["advisory_surfaces"]
    assert payload["notes"]
