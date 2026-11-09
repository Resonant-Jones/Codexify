"""Add recipient grants for direct message document attachments."""

import sqlalchemy as sa
from alembic import op

revision = "ab71d5ce9604"
down_revision = "b3f8c2d1e907"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "direct_message_document_shares",
        sa.Column(
            "message_id",
            sa.String(36),
            sa.ForeignKey("direct_messages.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "document_id",
            sa.String(36),
            sa.ForeignKey("uploaded_documents.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "recipient_account_id",
            sa.String(255),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("revoked_at", sa.TIMESTAMP(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("direct_message_document_shares")
