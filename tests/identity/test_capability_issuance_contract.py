from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from typing import Literal

import pytest
from click.testing import CliRunner

from guardian.cli.capability_grants_cli import capability_grants_cli
from guardian.core.capability_issuance import (
    CapabilityIssuanceError,
    CapabilityIssuanceRequest,
    issue_capability_grant,
)
from guardian.core.capability_tokens import (
    CapabilityFamily,
    CapabilityGrantKind,
    CapabilityGrantScope,
    CapabilityGrantStatus,
)
from guardian.db.models import CapabilityGrant


def _tier(
    *,
    tier_id: int = 101,
    tier_key: str = "gold-release",
    family: CapabilityFamily = CapabilityFamily.RELEASE_FAMILY,
    capabilities: list[str] | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        id=tier_id,
        tier_key=tier_key,
        capability_family=family.value,
        capabilities_json=capabilities
        if capabilities is not None
        else [family.value, CapabilityFamily.PLUGIN.value],
        limits_json={"persona_profile": 3, "plugin": 5},
        priority=100,
        is_active=True,
    )


def test_successful_permanent_grant_issuance_for_known_tier() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    tier = _tier()
    request = CapabilityIssuanceRequest(
        account_id="account-1",
        tier=tier,
        grant_kind=CapabilityGrantKind.PERMANENT.value,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
        provenance_source="manual",
        provenance_ref="seed-001",
        provenance_reason="manual unlock",
        issued_at=now,
    )

    result = issue_capability_grant(request, now=now)

    assert isinstance(result.grant, CapabilityGrant)
    assert result.account_id == "account-1"
    assert result.tier_id == tier.id
    assert result.tier_key == tier.tier_key
    assert result.tier_family == tier.capability_family
    assert result.capability_identifiers == (
        CapabilityFamily.RELEASE_FAMILY.value,
        CapabilityFamily.PLUGIN.value,
    )
    assert result.grant_scope == CapabilityGrantScope.ACCOUNT.value
    assert result.grant_kind == CapabilityGrantKind.PERMANENT.value
    assert result.grant_status == CapabilityGrantStatus.ACTIVE.value
    assert result.issued_at == now
    assert result.starts_at == now
    assert result.ends_at is None
    assert result.grant.account_id == "account-1"
    assert result.grant.tier_id == tier.id
    assert result.grant.ends_at is None


def test_successful_time_boxed_grant_issuance_with_normalized_fields() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    ends_at = now + timedelta(days=30)
    tier = _tier(
        family=CapabilityFamily.PERSONA_PROFILE,
        capabilities=[CapabilityFamily.PERSONA_PROFILE.value],
    )
    request = CapabilityIssuanceRequest(
        account_id="account-2",
        tier=tier,
        grant_kind=CapabilityGrantKind.TRIAL.value,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
        ends_at=ends_at,
    )

    result = issue_capability_grant(request, now=now)

    assert result.grant_kind == CapabilityGrantKind.TRIAL.value
    assert result.grant_status == CapabilityGrantStatus.ACTIVE.value
    assert result.starts_at == now
    assert result.ends_at == ends_at
    assert result.grant.starts_at == now
    assert result.grant.ends_at == ends_at
    payload = result.to_dict()
    assert payload["grant_id"] is None
    assert payload["starts_at"] == now.isoformat()
    assert payload["ends_at"] == ends_at.isoformat()


def test_unknown_tier_fails_closed() -> None:
    request = CapabilityIssuanceRequest(
        account_id="account-3",
        tier=None,
        grant_kind=CapabilityGrantKind.PERMANENT.value,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
    )

    with pytest.raises(CapabilityIssuanceError, match="tier"):
        issue_capability_grant(request)


def test_invalid_time_window_fails_closed() -> None:
    now = datetime(2026, 4, 13, 12, 0, tzinfo=timezone.utc)
    tier = _tier()
    request = CapabilityIssuanceRequest(
        account_id="account-4",
        tier=tier,
        grant_kind=CapabilityGrantKind.PROMO.value,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
        starts_at=now + timedelta(days=2),
        ends_at=now + timedelta(days=1),
    )

    with pytest.raises(CapabilityIssuanceError, match="ends_at"):
        issue_capability_grant(request, now=now)


def test_non_canonical_capability_identifiers_discovered_through_tier_fail_closed() -> (
    None
):
    tier = _tier(capabilities=["not-a-canonical-token"])
    request = CapabilityIssuanceRequest(
        account_id="account-5",
        tier=tier,
        grant_kind=CapabilityGrantKind.PERMANENT.value,
        grant_scope=CapabilityGrantScope.ACCOUNT.value,
    )

    with pytest.raises(CapabilityIssuanceError, match="capability identifier"):
        issue_capability_grant(request)


class _FakeQuery:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self._filters: dict[str, object] = {}

    def filter_by(self, **kwargs: object) -> _FakeQuery:
        self._filters.update(kwargs)
        return self

    def first(self) -> SimpleNamespace | None:
        for row in self._rows:
            if all(
                getattr(row, key, None) == value
                for key, value in self._filters.items()
            ):
                return row
        return None


class _FakeSession:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows
        self.added: list[CapabilityGrant] = []
        self.committed = False
        self.flushed = False

    def __enter__(self) -> _FakeSession:
        return self

    def __exit__(self, exc_type, exc, tb) -> Literal[False]:
        return False

    def query(self, model: object) -> _FakeQuery:
        return _FakeQuery(self._rows)

    def add(self, obj: CapabilityGrant) -> None:
        self.added.append(obj)

    def flush(self) -> None:
        self.flushed = True
        for index, obj in enumerate(self.added, start=1):
            if obj.id is None:
                obj.id = index

    def commit(self) -> None:
        self.committed = True


class _FakeDB:
    def __init__(self, rows: list[SimpleNamespace]) -> None:
        self._rows = rows

    def get_session(self) -> _FakeSession:
        return _FakeSession(self._rows)


def test_cli_returns_machine_readable_json_for_successful_issuance_flow(
    monkeypatch,
) -> None:
    tier = _tier(
        tier_id=404,
        tier_key="trial-persona",
        family=CapabilityFamily.PERSONA_PROFILE,
        capabilities=[CapabilityFamily.PERSONA_PROFILE.value],
    )
    fake_db = _FakeDB([tier])
    monkeypatch.setattr(
        "guardian.cli.capability_grants_cli.get_capability_issuance_db",
        lambda: fake_db,
    )

    runner = CliRunner()
    result = runner.invoke(
        capability_grants_cli,
        [
            "--account-id",
            "account-cli",
            "--tier-identifier",
            "trial-persona",
            "--grant-kind",
            CapabilityGrantKind.TRIAL.value,
            "--grant-scope",
            CapabilityGrantScope.ACCOUNT.value,
            "--ends-at",
            "2026-05-13T12:00:00+00:00",
            "--reason",
            "manual unlock",
            "--campaign",
            "spring-2026",
            "--operator-note",
            "seeded by test",
        ],
    )

    assert result.exit_code == 0, result.output
    payload = json.loads(result.output.strip())
    assert payload["grant_id"] == 1
    assert payload["account_id"] == "account-cli"
    assert payload["tier_id"] == 404
    assert payload["tier_key"] == "trial-persona"
    assert payload["grant_kind"] == CapabilityGrantKind.TRIAL.value
    assert payload["grant_scope"] == CapabilityGrantScope.ACCOUNT.value
    assert payload["grant_status"] == CapabilityGrantStatus.ACTIVE.value
    assert payload["provenance_source"] == "cli"
    assert payload["provenance_ref"] == "spring-2026"
    assert payload["provenance_reason"] == "manual unlock"
    assert payload["provenance_json"] == {
        "campaign": "spring-2026",
        "operator_note": "seeded by test",
    }
    assert payload["capability_identifiers"] == [
        CapabilityFamily.PERSONA_PROFILE.value,
    ]
