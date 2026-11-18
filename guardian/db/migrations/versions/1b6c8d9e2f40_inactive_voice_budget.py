"""Add inactive typed voice budget core. No policies, funding or activation.

Revision ID: 1b6c8d9e2f40
Revises: e723ba9046cd
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "1b6c8d9e2f40"
down_revision = "e723ba9046cd"
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        "voice_budget_reservations",
        sa.Column("id", sa.String(128), primary_key=True),
        sa.Column("account_id", sa.String(255), nullable=False),
        sa.Column("thread_id", sa.Integer(), nullable=False),
        sa.Column("payer_scope", sa.String(128), nullable=False),
        sa.Column("provider", sa.String(128), nullable=False),
        sa.Column("binding_snapshot", JSONB(), nullable=False),
        sa.Column("budget_ids", JSONB(), nullable=False),
        sa.Column("unit_contract", sa.String(32), nullable=False),
        sa.Column("quantity_ceiling", sa.BigInteger(), nullable=False),
        sa.Column("reserved_units", sa.BigInteger(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        sa.Column("price_snapshot", JSONB(), nullable=False),
        sa.Column("payload_hash", sa.String(64), nullable=False),
        sa.Column("dispatch_digest", sa.String(64), nullable=False),
        sa.Column("settled_units", sa.BigInteger()),
        sa.Column("settlement_hash", sa.String(64)),
        sa.Column("settlement_usage", JSONB()),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("provider = 'deepgram'", name="ck_voice_budget_provider"),
        sa.CheckConstraint(
            "unit_contract IN ('connection_ms','synthesis_characters')",
            name="ck_voice_budget_unit",
        ),
        sa.CheckConstraint(
            "state IN ('reserved','dispatched','settled','released')",
            name="ck_voice_budget_state",
        ),
        sa.CheckConstraint(
            "reserved_units > 0 AND quantity_ceiling > 0", name="ck_voice_budget_bounds"
        ),
        sa.CheckConstraint(
            "(state = 'settled' AND settled_units IS NOT NULL AND settled_units >= 0 AND settlement_hash IS NOT NULL AND settlement_usage IS NOT NULL) OR (state != 'settled' AND settled_units IS NULL AND settlement_hash IS NULL AND settlement_usage IS NULL)",
            name="ck_voice_budget_settlement",
        ),
    )
    op.create_index(
        "ix_voice_budget_account",
        "voice_budget_reservations",
        ["account_id", "created_at"],
    )
    op.create_table(
        "voice_budget_allocations",
        sa.Column(
            "attempt_id",
            sa.String(128),
            sa.ForeignKey("voice_budget_reservations.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "window_id",
            sa.String(128),
            sa.ForeignKey("inference_budget_windows.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
    )
    op.create_table(
        "voice_budget_dispatches",
        sa.Column(
            "attempt_id",
            sa.String(128),
            sa.ForeignKey("voice_budget_reservations.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("dispatch_digest", sa.String(64), nullable=False),
        sa.Column(
            "claimed_at",
            sa.TIMESTAMP(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade():
    op.drop_table("voice_budget_dispatches")
    op.drop_table("voice_budget_allocations")
    op.drop_table("voice_budget_reservations")
