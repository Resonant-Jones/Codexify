"""add Campaign Continuation Authority provenance discriminator

Revision ID: b7e2c4a1d903
Revises: 3a91d7c4e8b2
Create Date: 2026-10-29 00:00:00.000000
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "b7e2c4a1d903"
down_revision: str | Sequence[str] | None = "3a91d7c4e8b2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


#: Revision-local snapshot of the canonical provenance vocabulary.
#:
#: The strings are repeated here on purpose: historical replay must never
#: depend on mutable application tokens. This snapshot must match
#: ``guardian.protocol_tokens.ContinuationAuthorityProvenance``.
_PROVENANCE_VALUES_SQL = "'legacy_unverified', 'operator_deployment', 'account_admin'"

#: The provenance class assigned to every pre-existing action.
#:
#: The authority table and its only writer were introduced together, and no
#: operator-session credential is ever written to the account session store,
#: so every pre-existing approval and revocation was a deployment-operator
#: action whose human provenance is unverified. Classifying it as legacy
#: records that fact without inferring any individual's identity.
_LEGACY_PROVENANCE = "legacy_unverified"


def upgrade() -> None:
    # The discriminator is added nullable first so the backfill can classify
    # existing rows before the column is made mandatory.
    op.add_column(
        "campaign_continuation_authorities",
        sa.Column("approval_provenance", sa.String(length=64), nullable=True),
    )
    op.add_column(
        "campaign_continuation_authorities",
        sa.Column("revocation_provenance", sa.String(length=64), nullable=True),
    )

    # Bounded backfill. This touches only the two new columns: no actor id,
    # no timestamp, and no other column is rewritten.
    op.execute(
        "UPDATE campaign_continuation_authorities "
        f"SET approval_provenance = '{_LEGACY_PROVENANCE}' "
        "WHERE approval_provenance IS NULL"
    )
    op.execute(
        "UPDATE campaign_continuation_authorities "
        f"SET revocation_provenance = '{_LEGACY_PROVENANCE}' "
        "WHERE revoked_at IS NOT NULL AND revocation_provenance IS NULL"
    )

    # A revoked row must carry its revocation provenance, and an unrevoked
    # row must not.
    op.alter_column(
        "campaign_continuation_authorities",
        "approval_provenance",
        existing_type=sa.String(length=64),
        nullable=False,
    )
    op.create_check_constraint(
        "campaign_continuation_authorities_approval_provenance_check",
        "campaign_continuation_authorities",
        f"approval_provenance IN ({_PROVENANCE_VALUES_SQL})",
    )
    op.create_check_constraint(
        "campaign_continuation_authorities_revocation_provenance_check",
        "campaign_continuation_authorities",
        # ``revocation_provenance IS NOT NULL`` is stated explicitly because a
        # CHECK constraint only rejects a FALSE result: a NULL provenance
        # would make the ``IN`` test NULL, and NULL passes.
        "(revoked_at IS NULL AND revocation_provenance IS NULL) OR "
        "(revoked_at IS NOT NULL AND revocation_provenance IS NOT NULL AND "
        f"revocation_provenance IN ({_PROVENANCE_VALUES_SQL}))",
    )


def downgrade() -> None:
    # The downgrade discards the recorded provenance. That is inherent to
    # removing the discriminator and is why the upgrade never derives
    # provenance from anything but the durable row itself.
    op.drop_constraint(
        "campaign_continuation_authorities_revocation_provenance_check",
        "campaign_continuation_authorities",
        type_="check",
    )
    op.drop_constraint(
        "campaign_continuation_authorities_approval_provenance_check",
        "campaign_continuation_authorities",
        type_="check",
    )
    op.drop_column(
        "campaign_continuation_authorities",
        "revocation_provenance",
    )
    op.drop_column(
        "campaign_continuation_authorities",
        "approval_provenance",
    )
