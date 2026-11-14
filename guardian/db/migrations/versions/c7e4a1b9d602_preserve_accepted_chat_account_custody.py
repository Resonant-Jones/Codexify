"""Preserve original accepted-account custody without inventing legacy authority."""

from alembic import op
import sqlalchemy as sa

revision = "c7e4a1b9d602"
down_revision = "ab71d5ce9604"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "chat_completion_attempts",
        sa.Column("accepted_account_id", sa.String(255), nullable=True),
    )
    # Existing rows intentionally remain NULL. No current owner backfill can
    # establish what account originally authenticated an old accepted request.
    op.execute(
        """
        CREATE FUNCTION chat_attempt_account_custody_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.accepted_account_id IS DISTINCT FROM OLD.accepted_account_id
                OR (OLD.accepted_account_id IS NOT NULL AND (
                    NEW.request_id IS DISTINCT FROM OLD.request_id
                    OR NEW.backend_task_id IS DISTINCT FROM OLD.backend_task_id
                    OR NEW.thread_id IS DISTINCT FROM OLD.thread_id
                    OR NEW.turn_id IS DISTINCT FROM OLD.turn_id
                )) THEN
                RAISE EXCEPTION 'Accepted chat account custody is immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
    """
    )
    op.execute(
        """
        CREATE TRIGGER chat_attempt_account_custody_immutable
        BEFORE UPDATE ON chat_completion_attempts
        FOR EACH ROW EXECUTE FUNCTION chat_attempt_account_custody_immutable()
    """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER chat_attempt_account_custody_immutable ON chat_completion_attempts"
    )
    op.execute("DROP FUNCTION chat_attempt_account_custody_immutable()")
    op.drop_column("chat_completion_attempts", "accepted_account_id")
