"""ensure chatlog and connector tables exist for Postgres-only runtime

Revision ID: b5e6c55f0f0c
Revises: 9373693cc12e
Create Date: 2025-11-16 00:00:00.000000
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b5e6c55f0f0c"
down_revision: Union[str, Sequence[str], None] = "9373693cc12e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _has_table(inspector, table: str) -> bool:
    return table in inspector.get_table_names(schema="public")


def _has_column(inspector, table: str, column: str) -> bool:
    return column in {
        col["name"] for col in inspector.get_columns(table, schema="public")
    }


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    if not _has_table(inspector, "connector_configs"):
        op.create_table(
            "connector_configs",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column(
                "name", sa.String(length=255), nullable=False, unique=True
            ),
            sa.Column("type", sa.String(length=64), nullable=False),
            sa.Column(
                "config",
                postgresql.JSONB(astext_type=sa.Text()),
                server_default="{}",
                nullable=False,
            ),
            sa.Column("schedule", sa.String(length=255), nullable=True),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    elif not _has_column(inspector, "connector_configs", "schedule"):
        op.add_column(
            "connector_configs",
            sa.Column("schedule", sa.String(length=255), nullable=True),
        )

    if not _has_table(inspector, "connector_runs"):
        op.create_table(
            "connector_runs",
            sa.Column(
                "id", sa.BigInteger(), primary_key=True, autoincrement=True
            ),
            sa.Column(
                "config_id",
                sa.Integer(),
                sa.ForeignKey("connector_configs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("status", sa.String(length=32), nullable=False),
            sa.Column(
                "started_at", sa.TIMESTAMP(timezone=True), nullable=False
            ),
            sa.Column("finished_at", sa.TIMESTAMP(timezone=True)),
            sa.Column("error", sa.Text()),
            sa.Column(
                "document_count",
                sa.Integer(),
                server_default="0",
                nullable=False,
            ),
        )
        op.create_index(
            "ix_connector_runs_config_started",
            "connector_runs",
            ["config_id", sa.literal_column("started_at DESC")],
        )

    if not _has_table(inspector, "raw_documents"):
        op.create_table(
            "raw_documents",
            sa.Column(
                "id", sa.BigInteger(), primary_key=True, autoincrement=True
            ),
            sa.Column(
                "config_id",
                sa.Integer(),
                sa.ForeignKey("connector_configs.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("external_id", sa.String(length=512), nullable=False),
            sa.Column(
                "payload",
                postgresql.JSONB(astext_type=sa.Text()),
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_raw_documents_config_external",
            "raw_documents",
            ["config_id", "external_id"],
            unique=True,
        )

    if not _has_table(inspector, "events_outbox"):
        op.create_table(
            "events_outbox",
            sa.Column(
                "id", sa.BigInteger(), primary_key=True, autoincrement=True
            ),
            sa.Column("topic", sa.String(length=128)),
            sa.Column("payload", postgresql.JSONB(astext_type=sa.Text())),
            sa.Column(
                "status",
                sa.String(length=32),
                server_default="pending",
                nullable=False,
            ),
            sa.Column(
                "tenant_id",
                sa.String(length=64),
                server_default="default",
                nullable=False,
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_events_outbox_status_created",
            "events_outbox",
            ["status", "created_at"],
        )
        op.create_index(
            "ix_events_outbox_tenant_id", "events_outbox", ["tenant_id"]
        )

    if not _has_table(inspector, "memory_entries"):
        op.create_table(
            "memory_entries",
            sa.Column(
                "id", sa.BigInteger(), primary_key=True, autoincrement=True
            ),
            sa.Column("user_id", sa.String(length=255)),
            sa.Column("silo", sa.String(length=64), nullable=False),
            sa.Column("content", sa.Text()),
            sa.Column("tags", sa.Text()),
            sa.Column(
                "pinned", sa.Boolean(), server_default="false", nullable=False
            ),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.CheckConstraint(
                "silo IN ('ephemeral', 'midterm', 'longterm')",
                name="memory_entries_silo_check",
            ),
        )
        op.create_index("ix_memory_entries_silo", "memory_entries", ["silo"])
        op.create_index(
            "ix_memory_entries_user_silo", "memory_entries", ["user_id", "silo"]
        )
        op.create_index(
            "ix_memory_entries_silo_updated",
            "memory_entries",
            ["silo", "updated_at"],
        )

    if not _has_table(inspector, "chat_threads"):
        op.create_table(
            "chat_threads",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.String(length=255), nullable=False),
            sa.Column("title", sa.String(length=512), nullable=False),
            sa.Column("summary", sa.Text(), server_default="", nullable=False),
            sa.Column("project_id", sa.Integer()),
            sa.Column("parent_id", sa.Integer()),
            sa.Column("archived_at", sa.TIMESTAMP(timezone=True)),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.Column(
                "updated_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
            sa.ForeignKeyConstraint(["parent_id"], ["chat_threads.id"]),
        )
        op.create_index("ix_chat_threads_user_id", "chat_threads", ["user_id"])
        op.create_index(
            "ix_chat_threads_project_id", "chat_threads", ["project_id"]
        )
        op.create_index(
            "ix_chat_threads_parent_id", "chat_threads", ["parent_id"]
        )
        op.create_index(
            "ix_chat_threads_updated",
            "chat_threads",
            [sa.literal_column("updated_at DESC")],
        )

    if not _has_table(inspector, "chat_messages"):
        op.create_table(
            "chat_messages",
            sa.Column(
                "id", sa.BigInteger(), primary_key=True, autoincrement=True
            ),
            sa.Column(
                "thread_id",
                sa.Integer(),
                sa.ForeignKey("chat_threads.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("role", sa.String(length=32), nullable=False),
            sa.Column("content", sa.Text(), nullable=False),
            sa.Column(
                "created_at",
                sa.TIMESTAMP(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
        op.create_index(
            "ix_chat_messages_thread_id", "chat_messages", ["thread_id"]
        )
        op.create_index(
            "ix_chat_messages_thread_created",
            "chat_messages",
            ["thread_id", "created_at"],
        )


def downgrade() -> None:
    # Avoid destructive downgrades; schedule column can be dropped safely if present.
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if _has_column(inspector, "connector_configs", "schedule"):
        op.drop_column("connector_configs", "schedule")
