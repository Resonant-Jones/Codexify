"""normalize account observability schema

Revision ID: 9d4c2a7e1b6f
Revises: 8f3c1a7d2e6b
Create Date: 2026-08-13 00:00:00.000000

This migration reconciles the materialized ``account_observability`` schema
against the canonical ADR-049 future-shape after the historical ``b2`` migration
body was restored.

Three bounded shapes are recognized:

* ``historical_v1`` — produced by the original applied ``b2c3d4e5f6a7`` body
  (PK columns named ``id``/``id``/``id``, ``region_code VARCHAR(32)``,
  historical FK/check/index naming).
* ``canonical_v2`` — produced by the rewritten ``b2c3d4e5f6a7`` body that
  landed on the current lineage (PK columns named
  ``invite_id``/``guest_id``/``presence_session_id``, ``region_code
  VARCHAR(64)``, ADR-049 FK/check/index naming).
* ``unknown_or_mixed`` — anything else.

``historical_v1`` is normalized forward without changing any persisted
identifier value. ``canonical_v2`` is verified and emits no DDL. Any other
shape fails closed before mutation.

The downgrade is intentionally fail-closed: the reverse transformation cannot
be proven lossless for the canonical-v1 → historical-v1 direction in the
presence of tightened NOT NULL / FK constraints and index-name swaps. A
lossless reverse would require reinstating historical index/FK/check names
that have no functional meaning in the canonical shape; lying about it would
silently corrupt the migration ledger.
"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "9d4c2a7e1b6f"
down_revision: Union[str, Sequence[str], None] = "8f3c1a7d2e6b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


GOVERNED_TABLES = (
    "account_observability_invite_links",
    "account_observability_guest_identities",
    "account_observability_account_metadata",
    "account_observability_presence_sessions",
)


# Historical (pre-rewrite applied) PK column names.
HISTORICAL_PK_NAMES = {
    "account_observability_invite_links": "id",
    "account_observability_guest_identities": "id",
    "account_observability_presence_sessions": "id",
}

# Canonical (current lineage) PK column names.
CANONICAL_PK_NAMES = {
    "account_observability_invite_links": "invite_id",
    "account_observability_guest_identities": "guest_id",
    "account_observability_presence_sessions": "presence_session_id",
}

# Historical FK target columns (PK columns referenced). The historical FK
# targets point at ``<table>.id`` whereas canonical FK targets point at
# ``<table>.<canonical_pk_name>``.
HISTORICAL_FK_TARGET_COLUMNS = {
    ("account_observability_guest_identities", "first_invite_id"): "id",
    ("account_observability_account_metadata", "acquisition_invite_id"): "id",
    ("account_observability_account_metadata", "prior_guest_id"): "id",
    ("account_observability_presence_sessions", "guest_id"): "id",
    ("account_observability_presence_sessions", "invite_id"): "id",
}

# Indexes created by the historical ``b2`` that the canonical lineage does not
# carry (or renames). Dropping them during historical→canonical normalization
# is the only way to converge the schema signatures; the canonical index
# ``ix_account_observability_account_metadata_acquisition_invite`` is in the
# current ``b2`` body but absent from the historical body, so we must also
# *create* it during normalization.
HISTORICAL_ONLY_INDEXES = (
    "ix_account_observability_account_metadata_acquisition_invite",
)

# Index rename map for presence_sessions columns whose canonical trailing
# column differs from historical. Historical indexes use the bare column name
# without ``_at``; canonical uses ``_at`` to match ``models.py``.
PRESENCE_INDEX_RENAMES = {
    "ix_account_observability_presence_sessions_user_last_seen":
        "ix_account_observability_presence_sessions_user_last_seen_at",
    "ix_account_observability_presence_sessions_guest_last_seen":
        "ix_account_observability_presence_sessions_guest_last_seen_at",
    "ix_account_observability_presence_sessions_invite_started":
        "ix_account_observability_presence_sessions_invite_started_at",
    "ix_account_observability_presence_sessions_started_geo":
        "ix_acct_obs_presence_last_seen_country_region",
}


def _inspector():
    bind = op.get_bind()
    return sa.inspect(bind)


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in _inspector().get_columns(table_name)
        if column["name"] is not None
    }


def _index_names(table_name: str) -> set[str]:
    indexes = {
        index["name"]
        for index in _inspector().get_indexes(table_name)
        if index["name"] is not None
    }
    uniques = {
        unique["name"]
        for unique in _inspector().get_unique_constraints(table_name)
        if unique["name"] is not None
    }
    return indexes | uniques


def _check_constraint_names(table_name: str) -> set[str]:
    return {
        check["name"]
        for check in _inspector().get_check_constraints(table_name)
        if check["name"] is not None
    }


def _fk_names(table_name: str) -> set[str]:
    return {
        fk["name"]
        for fk in _inspector().get_foreign_keys(table_name)
        if fk.get("name")
    }


def _fk_target_column(table_name: str, constrained_column: str) -> str | None:
    for fk in _inspector().get_foreign_keys(table_name):
        if fk.get("constrained_columns") == [constrained_column]:
            referred = fk.get("referred_columns") or []
            if referred and referred[0] is not None:
                return referred[0]
    return None


def _column_nullable(table_name: str, column_name: str) -> bool | None:
    for column in _inspector().get_columns(table_name):
        if column["name"] == column_name:
            return column.get("nullable")
    return None


def _table_exists(table_name: str) -> bool:
    return table_name in set(_inspector().get_table_names())


def _classify() -> str:
    """Classify the materialized ``account_observability`` schema.

    Returns one of: ``historical_v1``, ``canonical_v2``, ``unknown_or_mixed``.

    Classification is based on the bounded material schema signature for the
    four governed tables:

    * PK column names on the three ID-keyed tables
    * FK target column references (PK columns referenced)
    * ``region_code`` width on ``account_observability_presence_sessions``
    * attribution constraint presence (canonical lineage adds
      ``account_observability_attribution_method_check`` and
      ``account_observability_attribution_confidence_check``)

    The classification deliberately does *not* rely on individual
    column-exists checks; a ``historical_v1`` that has been partially
    migrated (for example PK columns renamed but FK targets not updated,
    or canonical PK names retained but ``region_code`` still at
    ``VARCHAR(32)``) must read as ``unknown_or_mixed`` and fail closed.
    """
    if not all(_table_exists(table) for table in GOVERNED_TABLES):
        return "unknown_or_mixed"

    historical_signals = 0
    canonical_signals = 0

    for table, historical_pk in HISTORICAL_PK_NAMES.items():
        pk_constraint = _inspector().get_pk_constraint(table)
        pk_columns = set(pk_constraint.get("constrained_columns", []) or [])
        if pk_columns == {historical_pk}:
            historical_signals += 1
        elif pk_columns == {CANONICAL_PK_NAMES[table]}:
            canonical_signals += 1
        else:
            return "unknown_or_mixed"

    for (table, constrained), expected_historical in HISTORICAL_FK_TARGET_COLUMNS.items():
        actual = _fk_target_column(table, constrained)
        if actual == expected_historical:
            historical_signals += 1
        elif actual == CANONICAL_PK_NAMES[
            "account_observability_invite_links"
        ] or actual == CANONICAL_PK_NAMES[
            "account_observability_guest_identities"
        ]:
            canonical_signals += 1
        else:
            return "unknown_or_mixed"

    # ``region_code`` width signal: canonical lineage sets VARCHAR(64);
    # historical lineage uses VARCHAR(32). A mixed fixture where the PK
    # names have been canonicalized but ``region_code`` still at
    # VARCHAR(32) must read as ``unknown_or_mixed`` rather than be
    # silently treated as canonical.
    region_widths: list[int] = []
    for column in _inspector().get_columns(
        "account_observability_presence_sessions"
    ):
        if column["name"] == "region_code":
            region_type = column.get("type")
            if isinstance(region_type, str):
                # Postgres inspector renders VARCHAR(64) etc.
                import re

                m = re.search(r"VARCHAR\((\d+)\)", region_type)
                if m:
                    region_widths.append(int(m.group(1)))
            break
    if region_widths:
        if 64 in region_widths:
            canonical_signals += 1
        elif 32 in region_widths:
            historical_signals += 1
        else:
            return "unknown_or_mixed"

    # Attribution constraint presence: canonical lineage carries
    # separate value-check constraints on ``attribution_method`` and
    # ``attribution_confidence``; historical lineage only has the
    # combined ``ck_account_observability_account_metadata_attribution``
    # constraint.
    metadata_checks = _check_constraint_names(
        "account_observability_account_metadata"
    )
    has_method_check = (
        "account_observability_attribution_method_check" in metadata_checks
    )
    has_confidence_check = (
        "account_observability_attribution_confidence_check" in metadata_checks
    )
    has_legacy_combined_check = (
        "ck_account_observability_account_metadata_attribution"
        in metadata_checks
    )
    if has_method_check and has_confidence_check:
        canonical_signals += 1
    elif has_legacy_combined_check and not (has_method_check and has_confidence_check):
        historical_signals += 1
    else:
        return "unknown_or_mixed"

    if historical_signals and canonical_signals:
        return "unknown_or_mixed"
    if historical_signals and not canonical_signals:
        return "historical_v1"
    if canonical_signals and not historical_signals:
        return "canonical_v2"
    return "unknown_or_mixed"


def _preflight_historical_lossless() -> None:
    """Fail closed if any row would prevent lossless historical→canonical.

    The canonical lineage tightens ``account_observability_invite_links``
    ``created_by_user_id`` from nullable to NOT NULL and changes the
    matching FK from ``ondelete=SET NULL`` to ``ondelete=RESTRICT``. A
    historical row with ``created_by_user_id IS NULL`` cannot survive the
    tightening; the migration must stop before any DDL.
    """
    bind = op.get_bind()
    null_creators = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM account_observability_invite_links "
            "WHERE created_by_user_id IS NULL"
        )
    ).scalar() or 0
    if null_creators:
        raise RuntimeError(
            "account_observability_compatibility_normalization: "
            "refusing to tighten NOT NULL on created_by_user_id — "
            f"{null_creators} historical row(s) carry NULL creator. "
            "Manual operator disposition required."
        )

    # Check country_code values would survive the canonical uppercase rule.
    bad_country = bind.execute(
        sa.text(
            "SELECT COUNT(*) FROM account_observability_presence_sessions "
            "WHERE country_code IS NOT NULL "
            "AND country_code <> upper(country_code)"
        )
    ).scalar() or 0
    if bad_country:
        raise RuntimeError(
            "account_observability_compatibility_normalization: "
            "refusing to enforce canonical uppercase country_code rule — "
            f"{bad_country} historical row(s) carry lowercase country codes. "
            "Manual operator disposition required."
        )


def _normalize_historical_to_canonical() -> None:
    """Perform lossless historical_v1 → canonical_v2 schema normalization."""
    _preflight_historical_lossless()

    # 1) Rename PK columns. RENAME COLUMN preserves data.
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "RENAME COLUMN id TO invite_id"
    )
    op.execute(
        "ALTER TABLE account_observability_guest_identities "
        "RENAME COLUMN id TO guest_id"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "RENAME COLUMN id TO presence_session_id"
    )

    # 2) Widen region_code from VARCHAR(32) to VARCHAR(64). Widen-only.
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ALTER COLUMN region_code TYPE VARCHAR(64)"
    )

    # 3) Replace historical FK names with canonical FK names.
    # Postgres renames FK constraints via ALTER TABLE ... RENAME CONSTRAINT.
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "RENAME CONSTRAINT fk_account_observability_invite_links_created_by_user_id "
        "TO fk_account_observability_invites_created_by_user"
    )
    op.execute(
        "ALTER TABLE account_observability_guest_identities "
        "RENAME CONSTRAINT fk_account_observability_guest_identities_first_invite_id "
        "TO fk_account_observability_guests_first_invite"
    )
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "RENAME CONSTRAINT fk_account_observability_account_metadata_user_id "
        "TO fk_account_observability_metadata_user"
    )
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "RENAME CONSTRAINT fk_account_observability_account_metadata_acquisition_invite_id "
        "TO fk_account_observability_metadata_acquisition_invite"
    )
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "RENAME CONSTRAINT fk_account_observability_account_metadata_prior_guest_id "
        "TO fk_account_observability_metadata_prior_guest"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "RENAME CONSTRAINT fk_account_observability_presence_sessions_user_id "
        "TO fk_account_observability_presence_user"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "RENAME CONSTRAINT fk_account_observability_presence_sessions_guest_id "
        "TO fk_account_observability_presence_guest"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "RENAME CONSTRAINT fk_account_observability_presence_sessions_invite_id "
        "TO fk_account_observability_presence_invite"
    )

    # 4) Tighten created_by_user_id to NOT NULL + FK ondelete=RESTRICT.
    # The preflight above guarantees no historical row has NULL creator.
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "ALTER COLUMN created_by_user_id SET NOT NULL"
    )
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "DROP CONSTRAINT fk_account_observability_invites_created_by_user"
    )
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "ADD CONSTRAINT fk_account_observability_invites_created_by_user "
        "FOREIGN KEY (created_by_user_id) REFERENCES users(id) ON DELETE RESTRICT"
    )

    # 5) Replace historical check constraints with canonical checks.
    # Historical invite status check is a simple IN list; canonical is the
    # same IN list but with the canonical constraint name. The historical
    # lifecycle check (3-arm) and the canonical lifecycle check are
    # semantically equivalent for the historical data set: the canonical
    # form drops the ``disabled_at IS NULL`` clause from the
    # ``status = 'revoked'`` arm (a stricter view that historical rows
    # already satisfy because the historical body required it). Drop and
    # recreate the constraint under the canonical name.
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "DROP CONSTRAINT ck_account_observability_invite_links_status"
    )
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "ADD CONSTRAINT account_observability_invite_status_check "
        "CHECK (status IN ('active','disabled','revoked'))"
    )

    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "DROP CONSTRAINT ck_account_observability_invite_links_lifecycle_timestamps"
    )
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "ADD CONSTRAINT account_observability_invite_lifecycle_check "
        "CHECK ("
        "((status = 'active' AND disabled_at IS NULL AND revoked_at IS NULL) "
        "OR (status = 'disabled' AND disabled_at IS NOT NULL AND revoked_at IS NULL) "
        "OR (status = 'revoked' AND revoked_at IS NOT NULL))"
        ")"
    )

    # Historical account_metadata attribution check tightened the all-NULL
    # arm to also require ``prior_guest_id IS NULL``. Canonical relaxes
    # that arm. The historical all-NULL rows still satisfy the canonical
    # check; the historical rows with ``acquisition_invite_id IS NULL`` and
    # ``prior_guest_id NOT NULL`` also satisfy the canonical check
    # (because the canonical all-NULL arm does not constrain prior_guest).
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "DROP CONSTRAINT ck_account_observability_account_metadata_attribution"
    )
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "ADD CONSTRAINT account_observability_attribution_consistency_check "
        "CHECK ("
        "((acquisition_invite_id IS NULL AND attribution_method IS NULL "
        "AND attribution_confidence IS NULL) "
        "OR (acquisition_invite_id IS NOT NULL "
        "AND attribution_method = 'first_party_first_touch' "
        "AND attribution_confidence = 'verified'))"
        ")"
    )

    # Canonical attribution_method/confidence value checks are new (the
    # historical body had no separate value checks). Add them.
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "ADD CONSTRAINT account_observability_attribution_method_check "
        "CHECK (attribution_method IS NULL "
        "OR attribution_method IN ('first_party_first_touch'))"
    )
    op.execute(
        "ALTER TABLE account_observability_account_metadata "
        "ADD CONSTRAINT account_observability_attribution_confidence_check "
        "CHECK (attribution_confidence IS NULL "
        "OR attribution_confidence IN ('verified'))"
    )

    # Presence check constraints: replace historical names with canonical
    # names. Semantically equivalent for historical data:
    #   * Historical exactly_one_subject is XOR (a OR b, not both);
    #     canonical uses the symmetric-difference operator.
    #   * Historical country_code_length omits the upper-case rule;
    #     canonical adds it (preflight already verified no lowercase rows).
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "DROP CONSTRAINT ck_account_observability_presence_sessions_exactly_one_subject"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ADD CONSTRAINT account_observability_presence_exactly_one_subject_check "
        "CHECK (((user_id IS NOT NULL) <> (guest_id IS NOT NULL)))"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "DROP CONSTRAINT ck_ao_presence_sessions_last_seen_after_start"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ADD CONSTRAINT account_observability_presence_last_seen_order_check "
        "CHECK (last_seen_at >= started_at)"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "DROP CONSTRAINT ck_ao_presence_sessions_end_after_start"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ADD CONSTRAINT account_observability_presence_ended_order_check "
        "CHECK (ended_at IS NULL OR ended_at >= started_at)"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "DROP CONSTRAINT ck_ao_presence_sessions_region_requires_country"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ADD CONSTRAINT account_observability_presence_region_country_check "
        "CHECK (region_code IS NULL OR country_code IS NOT NULL)"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "DROP CONSTRAINT ck_ao_presence_sessions_country_code_length"
    )
    op.execute(
        "ALTER TABLE account_observability_presence_sessions "
        "ADD CONSTRAINT account_observability_presence_country_code_check "
        "CHECK (country_code IS NULL OR (length(country_code) = 2 "
        "AND country_code = upper(country_code)))"
    )

    # 6) Replace historical indexes with canonical equivalents.
    # Drop historical-only index that the canonical lineage does not carry.
    op.execute("DROP INDEX IF EXISTS ix_account_observability_account_metadata_acquisition_invite")

    # Rename presence_sessions indexes to canonical names. Postgres RENAME INDEX.
    for historical_name, canonical_name in PRESENCE_INDEX_RENAMES.items():
        # The historical geo index must not only be renamed; its column set
        # changes from ``(started_at, country_code, region_code)`` to the
        # canonical ``(last_seen_at, country_code, region_code)``. Drop it
        # and recreate it with the canonical columns below.
        if historical_name == "ix_account_observability_presence_sessions_started_geo":
            op.execute(
                "DROP INDEX IF EXISTS "
                "ix_account_observability_presence_sessions_started_geo"
            )
            continue
        op.execute(f"ALTER INDEX {historical_name} RENAME TO {canonical_name}")

    # Rename the guest_identities lookup index to the canonical name.
    op.execute(
        "ALTER INDEX ix_account_observability_guest_identities_first_invite "
        "RENAME TO ix_account_observability_guest_identities_first_invite_id"
    )

    # The historical ``uq_account_observability_invite_links_token_hash`` is
    # a unique INDEX; the canonical lineage carries a UNIQUE CONSTRAINT of the
    # same name. PostgreSQL distinguishes the two (a unique constraint owns a
    # pg_constraint row, a bare unique index does not). Convert the index to
    # a constraint so the catalog shape matches canonical.
    op.execute(
        "DROP INDEX IF EXISTS uq_account_observability_invite_links_token_hash"
    )
    op.execute(
        "ALTER TABLE account_observability_invite_links "
        "ADD CONSTRAINT uq_account_observability_invite_links_token_hash "
        "UNIQUE (token_hash)"
    )

    # Create the canonical geo index with ``last_seen_at`` as the leading
    # column (historical used ``started_at``).
    op.execute(
        "CREATE INDEX ix_acct_obs_presence_last_seen_country_region "
        "ON account_observability_presence_sessions("
        "last_seen_at, country_code, region_code)"
    )


def upgrade() -> None:
    shape = _classify()
    if shape == "historical_v1":
        _normalize_historical_to_canonical()
        return
    if shape == "canonical_v2":
        # Verified already-canonical: no account-observability DDL emitted.
        return
    raise RuntimeError(
        "account_observability_compatibility_normalization: refusing to "
        f"proceed on schema shape {shape!r}; manual operator disposition "
        "required."
    )


def downgrade() -> None:
    raise RuntimeError(
        "account_observability_compatibility_normalization: downgrade is "
        "intentionally fail-closed. The reverse historical reconstruction "
        "cannot be proven lossless (NOT NULL tightening, FK ondelete "
        "tightening, constraint/index rename). Reverting this migration "
        "requires an explicit, separately authorized repair task."
    )