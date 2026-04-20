"""assign user ownership to core entities

Revision ID: f2b3c4d5e6f8
Revises: f2b3c4d5e6f7
Create Date: 2026-04-19 00:00:01.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f2b3c4d5e6f8"
down_revision: Union[str, Sequence[str], None] = "f2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

DEFAULT_USER_ID = "local"


def _has_table(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return table_name in inspector.get_table_names()


def _has_column(table_name: str, column_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return column_name in {
        column["name"] for column in inspector.get_columns(table_name)
    }


def _has_foreign_key(table_name: str, constraint_name: str) -> bool:
    if not _has_table(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return constraint_name in {
        fk["name"] for fk in inspector.get_foreign_keys(table_name)
    }


def _ensure_default_user() -> None:
    op.execute(
        """
        INSERT INTO users (id, username, created_at)
        VALUES ('local', 'local', NOW())
        ON CONFLICT (id) DO NOTHING
        """
    )


def _backfill_user_id(table_name: str) -> None:
    op.execute(
        f"UPDATE {table_name} SET user_id = '{DEFAULT_USER_ID}' WHERE user_id IS NULL"
    )


def _ensure_user_fk(table_name: str) -> None:
    constraint_name = f"fk_{table_name}_user_id_users"
    if not _has_foreign_key(table_name, constraint_name):
        op.create_foreign_key(
            constraint_name,
            table_name,
            "users",
            ["user_id"],
            ["id"],
            ondelete="CASCADE",
        )


def _make_not_null(table_name: str) -> None:
    op.alter_column(
        table_name,
        "user_id",
        existing_type=sa.String(length=255),
        nullable=False,
    )


def upgrade() -> None:
    _ensure_default_user()

    if not _has_column("projects", "user_id"):
        op.add_column(
            "projects",
            sa.Column("user_id", sa.String(length=255), nullable=True),
        )
    _backfill_user_id("projects")
    _ensure_user_fk("projects")
    _make_not_null("projects")

    if not _has_column("chat_messages", "user_id"):
        op.add_column(
            "chat_messages",
            sa.Column("user_id", sa.String(length=255), nullable=True),
        )
    _backfill_user_id("chat_messages")
    _ensure_user_fk("chat_messages")
    _make_not_null("chat_messages")

    _backfill_user_id("chat_threads")
    _ensure_user_fk("chat_threads")
    _make_not_null("chat_threads")

    _backfill_user_id("uploaded_documents")
    _ensure_user_fk("uploaded_documents")
    _make_not_null("uploaded_documents")

    _backfill_user_id("memory_entries")
    _ensure_user_fk("memory_entries")
    _make_not_null("memory_entries")

    _backfill_user_id("personas")
    _ensure_user_fk("personas")
    _make_not_null("personas")


def downgrade() -> None:
    op.drop_constraint(
        "fk_personas_user_id_users", "personas", type_="foreignkey"
    )
    op.alter_column(
        "personas",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.drop_constraint(
        "fk_memory_entries_user_id_users",
        "memory_entries",
        type_="foreignkey",
    )
    op.alter_column(
        "memory_entries",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.drop_constraint(
        "fk_uploaded_documents_user_id_users",
        "uploaded_documents",
        type_="foreignkey",
    )
    op.alter_column(
        "uploaded_documents",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.drop_constraint(
        "fk_chat_threads_user_id_users", "chat_threads", type_="foreignkey"
    )
    op.alter_column(
        "chat_threads",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )

    op.drop_constraint(
        "fk_chat_messages_user_id_users",
        "chat_messages",
        type_="foreignkey",
    )
    op.alter_column(
        "chat_messages",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.drop_column("chat_messages", "user_id")

    op.drop_constraint(
        "fk_projects_user_id_users", "projects", type_="foreignkey"
    )
    op.alter_column(
        "projects",
        "user_id",
        existing_type=sa.String(length=255),
        nullable=True,
    )
    op.drop_column("projects", "user_id")
