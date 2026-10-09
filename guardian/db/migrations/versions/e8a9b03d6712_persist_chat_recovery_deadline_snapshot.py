"""Preserve original chat recovery envelopes without historical backfill.

Revision ID: e8a9b03d6712
Revises: d4c69e03a712
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "e8a9b03d6712"
down_revision = "d4c69e03a712"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_completion_attempts",
        sa.Column("deadline_snapshot", postgresql.JSONB(), nullable=True),
    )
    op.add_column(
        "chat_completion_attempts",
        sa.Column("turn_lock_token", sa.String(128), nullable=True),
    )
    op.create_check_constraint(
        "ck_chat_attempt_recovery_snapshot_pair",
        "chat_completion_attempts",
        "(deadline_snapshot IS NULL AND turn_lock_token IS NULL) OR "
        "(deadline_snapshot IS NOT NULL AND turn_lock_token IS NOT NULL "
        "AND length(trim(turn_lock_token)) > 0)",
    )
    # Freeze NULL legacy records too: updates cannot invent a historical envelope.
    op.execute("""
        CREATE FUNCTION chat_attempt_recovery_snapshot_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.deadline_snapshot IS DISTINCT FROM OLD.deadline_snapshot
                OR NEW.turn_lock_token IS DISTINCT FROM OLD.turn_lock_token THEN
                RAISE EXCEPTION 'Chat recovery snapshot is immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
    """)
    op.execute("""
        CREATE TRIGGER chat_attempt_recovery_snapshot_immutable
        BEFORE UPDATE ON chat_completion_attempts
        FOR EACH ROW EXECUTE FUNCTION chat_attempt_recovery_snapshot_immutable()
    """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER chat_attempt_recovery_snapshot_immutable ON chat_completion_attempts"
    )
    op.execute("DROP FUNCTION chat_attempt_recovery_snapshot_immutable()")
    op.drop_constraint(
        "ck_chat_attempt_recovery_snapshot_pair", "chat_completion_attempts", type_="check"
    )
    op.drop_column("chat_completion_attempts", "turn_lock_token")
    op.drop_column("chat_completion_attempts", "deadline_snapshot")
