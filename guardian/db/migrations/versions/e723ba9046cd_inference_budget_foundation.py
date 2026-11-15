"""Add inactive inference budget ledger foundation. No runtime activation.

Revision ID: e723ba9046cd
Revises: d8a90bf32107
"""

from alembic import op

revision = "e723ba9046cd"
down_revision = "d8a90bf32107"
branch_labels = None
depends_on = None


def upgrade():
    op.execute(
        """
CREATE TABLE inference_budget_windows (
	id VARCHAR(128) NOT NULL,
	payer_scope VARCHAR(128) NOT NULL,
	provider VARCHAR(128) NOT NULL,
	kind VARCHAR(16) NOT NULL,
	starts_at TIMESTAMP WITH TIME ZONE NOT NULL,
	ends_at TIMESTAMP WITH TIME ZONE NOT NULL,
	enabled BOOLEAN NOT NULL,
	limit_units BIGINT NOT NULL,
	held_units BIGINT NOT NULL,
	spent_units BIGINT NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_budget_window_kind CHECK (kind IN ('monthly', 'funding')),
	CONSTRAINT ck_budget_window_dates CHECK (ends_at > starts_at),
	CONSTRAINT ck_budget_window_amounts CHECK (limit_units >= 0 AND held_units >= 0 AND spent_units >= 0)
)

"""
    )
    op.execute(
        """
CREATE TABLE inference_budget_reservations (
	id VARCHAR(128) NOT NULL,
	account_id VARCHAR(255) NOT NULL,
	request_id VARCHAR(128) NOT NULL,
	thread_id INTEGER NOT NULL,
	payer_scope VARCHAR(128) NOT NULL,
	provider VARCHAR(128) NOT NULL,
	model VARCHAR(128) NOT NULL,
	reserved_units BIGINT NOT NULL,
	settled_units BIGINT,
	input_ceiling BIGINT NOT NULL,
	output_ceiling BIGINT NOT NULL,
	state VARCHAR(16) NOT NULL,
	price_snapshot JSONB NOT NULL,
	payload_hash VARCHAR(64) NOT NULL,
	settlement_hash VARCHAR(64),
	settlement_usage JSONB,
	created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT ck_budget_reservation_state CHECK (state IN ('reserved','dispatched','settled','released')),
	CONSTRAINT ck_budget_reservation_bounds CHECK (reserved_units > 0 AND input_ceiling >= 0 AND output_ceiling >= 0),
	CONSTRAINT ck_budget_settlement_presence CHECK ((state = 'settled' AND settled_units IS NOT NULL AND settled_units >= 0 AND settlement_hash IS NOT NULL AND settlement_usage IS NOT NULL) OR (state != 'settled' AND settled_units IS NULL AND settlement_hash IS NULL AND settlement_usage IS NULL))
)

"""
    )
    op.execute(
        """CREATE INDEX ix_budget_reservation_account ON inference_budget_reservations (account_id, created_at)"""
    )
    op.execute(
        """
CREATE TABLE inference_budget_allocations (
	attempt_id VARCHAR(128) NOT NULL,
	window_id VARCHAR(128) NOT NULL,
	PRIMARY KEY (attempt_id, window_id),
	FOREIGN KEY(attempt_id) REFERENCES inference_budget_reservations (id) ON DELETE RESTRICT,
	FOREIGN KEY(window_id) REFERENCES inference_budget_windows (id) ON DELETE RESTRICT
)

"""
    )


def downgrade():
    op.drop_table("inference_budget_allocations")
    op.drop_table("inference_budget_reservations")
    op.drop_table("inference_budget_windows")
