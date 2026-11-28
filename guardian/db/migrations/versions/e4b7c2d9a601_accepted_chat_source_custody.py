"""Add creation-bound accepted chat source identity."""

import sqlalchemy as sa
from alembic import op

revision = "e4b7c2d9a601"
down_revision = "a64c358e2241"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # No foreign key or backfill. A deleted source leaves an unresolved snapshot.
    op.add_column(
        "chat_completion_attempts",
        sa.Column("accepted_user_message_id", sa.BigInteger(), nullable=True),
    )
    op.create_check_constraint(
        "ck_chat_attempt_source_requires_account",
        "chat_completion_attempts",
        "accepted_user_message_id IS NULL OR "
        "(accepted_user_message_id > 0 AND accepted_account_id IS NOT NULL "
        "AND length(trim(accepted_account_id)) > 0)",
    )
    op.execute("""
        CREATE FUNCTION chat_attempt_source_custody_immutable()
        RETURNS trigger LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.accepted_user_message_id IS DISTINCT FROM OLD.accepted_user_message_id THEN
                RAISE EXCEPTION 'Accepted chat source custody is immutable'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $$
        """)
    op.execute("""
        CREATE TRIGGER chat_attempt_source_custody_immutable
        BEFORE UPDATE ON chat_completion_attempts
        FOR EACH ROW EXECUTE FUNCTION chat_attempt_source_custody_immutable()
        """)


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER chat_attempt_source_custody_immutable ON chat_completion_attempts"
    )
    op.execute("DROP FUNCTION chat_attempt_source_custody_immutable()")
    op.drop_constraint(
        "ck_chat_attempt_source_requires_account",
        "chat_completion_attempts",
        type_="check",
    )
    op.drop_column("chat_completion_attempts", "accepted_user_message_id")
