"""Fence unresolved chat attempts after their original terminal deadline.

Revision ID: f1a6d83b9024
Revises: e8a9b03d6712
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "f1a6d83b9024"
down_revision = "e8a9b03d6712"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_completion_attempts",
        sa.Column("terminal_outcome", postgresql.JSONB(), nullable=True),
    )
    op.create_check_constraint(
        "ck_chat_attempt_orphan_outcome",
        "chat_completion_attempts",
        "terminal_outcome IS NULL OR COALESCE(("
        "jsonb_typeof(terminal_outcome) = 'object' "
        "AND terminal_outcome->>'failure_code' = 'CHAT_ACCEPTED_TASK_ORPHANED' "
        "AND terminal_event_type = 'task.failed' "
        "AND completed_message_id IS NULL AND accepted_at IS NOT NULL "
        "AND deadline_snapshot IS NOT NULL "
        "AND (terminal_outcome->>'reconciled_at')::timestamptz >= "
        "(deadline_snapshot->>'terminal_deadline_at')::timestamptz), false)",
    )
    op.execute("""
        CREATE FUNCTION chat_attempt_orphan_fence() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF OLD.terminal_outcome IS NOT NULL THEN
                IF NEW.terminal_outcome IS DISTINCT FROM OLD.terminal_outcome
                    OR NEW.terminal_event_type IS DISTINCT FROM OLD.terminal_event_type
                    OR NEW.completed_message_id IS DISTINCT FROM OLD.completed_message_id
                THEN
                    RAISE EXCEPTION 'Chat orphan outcome is immutable'
                        USING ERRCODE = '23514';
                END IF;
            ELSIF NEW.terminal_outcome IS NOT NULL AND (
                OLD.completed_message_id IS NOT NULL
                OR OLD.terminal_event_type IS NOT NULL
            ) THEN
                RAISE EXCEPTION 'Durable chat terminal truth precedes reconciliation'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END; $$
    """)
    op.execute("""
        CREATE TRIGGER chat_attempt_orphan_fence
        BEFORE UPDATE ON chat_completion_attempts
        FOR EACH ROW EXECUTE FUNCTION chat_attempt_orphan_fence()
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER chat_attempt_orphan_fence ON chat_completion_attempts")
    op.execute("DROP FUNCTION chat_attempt_orphan_fence()")
    op.drop_constraint(
        "ck_chat_attempt_orphan_outcome", "chat_completion_attempts", type_="check"
    )
    # Keep task.failed as historical durable truth when removing its detail column.
    op.drop_column("chat_completion_attempts", "terminal_outcome")
