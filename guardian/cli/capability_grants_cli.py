"""Backend-only CLI for issuing durable capability grants."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

import click

from guardian.core.capability_issuance import (
    CapabilityIssuanceError,
    CapabilityIssuanceRequest,
    issue_capability_grant,
)
from guardian.core.capability_tokens import (
    CAPABILITY_GRANT_KINDS,
    CAPABILITY_GRANT_SCOPES,
    CAPABILITY_GRANT_STATUSES,
)
from guardian.core.dependencies import get_capability_issuance_db
from guardian.db.models import CapabilityTier


def _choice(values: frozenset[str]) -> click.Choice:
    return click.Choice(sorted(values), case_sensitive=False)


def _parse_optional_datetime(value: str | None, label: str) -> datetime | None:
    if value is None:
        return None
    raw = value.strip()
    if not raw:
        return None
    normalized = raw[:-1] + "+00:00" if raw.endswith("Z") else raw
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError as exc:
        raise click.ClickException(f"Invalid {label}: {value}") from exc
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _resolve_tier(session: Any, tier_identifier: str) -> CapabilityTier:
    identifier = tier_identifier.strip()
    tier = session.query(CapabilityTier).filter_by(tier_key=identifier).first()
    if tier is None:
        try:
            tier_id = int(identifier)
        except ValueError:
            tier_id = None
        if tier_id is not None:
            tier = session.query(CapabilityTier).filter_by(id=tier_id).first()
    if tier is None:
        raise click.ClickException(
            f"Unknown capability tier: {tier_identifier}"
        )
    return tier


@click.command(name="capability-grants:issue")
@click.option("--account-id", required=True, help="Target account_id.")
@click.option(
    "--tier-identifier",
    "--tier-key",
    "tier_identifier",
    required=True,
    help="Target tier key or numeric identifier.",
)
@click.option(
    "--grant-kind",
    required=True,
    type=_choice(CAPABILITY_GRANT_KINDS),
    help="Canonical grant kind.",
)
@click.option(
    "--grant-scope",
    default="account",
    show_default=True,
    type=_choice(CAPABILITY_GRANT_SCOPES),
    help="Canonical grant scope.",
)
@click.option(
    "--grant-status",
    default="active",
    show_default=True,
    type=_choice(CAPABILITY_GRANT_STATUSES),
    help="Canonical grant status.",
)
@click.option(
    "--starts-at",
    default=None,
    help="Optional ISO-8601 start time.",
)
@click.option(
    "--ends-at",
    default=None,
    help="Optional ISO-8601 end time.",
)
@click.option(
    "--provenance-source",
    default="cli",
    show_default=True,
    help="Provenance source label.",
)
@click.option(
    "--reason",
    default=None,
    help="Optional human-readable reason.",
)
@click.option(
    "--campaign",
    default=None,
    help="Optional campaign or promotion identifier.",
)
@click.option(
    "--operator-note",
    default=None,
    help="Optional operator note.",
)
def capability_grants_cli(
    *,
    account_id: str,
    tier_identifier: str,
    grant_kind: str,
    grant_scope: str,
    grant_status: str,
    starts_at: str | None,
    ends_at: str | None,
    provenance_source: str,
    reason: str | None,
    campaign: str | None,
    operator_note: str | None,
) -> None:
    """Issue a capability grant and print a JSON summary."""

    db = get_capability_issuance_db()
    with db.get_session() as session:
        tier = _resolve_tier(session, tier_identifier)
        request = CapabilityIssuanceRequest(
            account_id=account_id,
            tier=tier,
            grant_kind=grant_kind,
            grant_scope=grant_scope,
            grant_status=grant_status,
            starts_at=_parse_optional_datetime(starts_at, "starts_at"),
            ends_at=_parse_optional_datetime(ends_at, "ends_at"),
            provenance_source=provenance_source,
            provenance_ref=campaign,
            provenance_reason=reason,
            provenance_json={
                key: value
                for key, value in {
                    "campaign": campaign,
                    "operator_note": operator_note,
                }.items()
                if value is not None
            },
        )
        try:
            result = issue_capability_grant(request)
        except CapabilityIssuanceError as exc:
            raise click.ClickException(str(exc)) from exc

        session.add(result.grant)
        session.flush()
        session.commit()
        click.echo(json.dumps(result.to_dict(), sort_keys=True))


__all__ = ["capability_grants_cli"]
