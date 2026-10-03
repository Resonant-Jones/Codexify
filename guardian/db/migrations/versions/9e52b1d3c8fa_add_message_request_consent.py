"""Add message-request consent without fabricating historical requests.

Revision ID: 9e52b1d3c8fa
Revises: 8d41a0c2b7ef

Existing Conversation pairs receive honest historical consent. Neutral pairs
without Conversations receive none. No existing IDs, placement or messages
are rewritten. Schema literals are frozen migration vocabulary (ADR-097).
"""
from alembic import op
import sqlalchemy as sa

revision = "9e52b1d3c8fa"
down_revision = "8d41a0c2b7ef"
branch_labels = None
depends_on = None


def _profile(name, *, primary_key=False):
    return sa.Column(
        name,
        sa.String(36),
        sa.ForeignKey("user_profiles.profile_id", ondelete="RESTRICT"),
        nullable=False,
        primary_key=primary_key,
    )


def _time(name, *, nullable=False):
    return sa.Column(name, sa.TIMESTAMP(timezone=True), nullable=nullable)


def upgrade():
    op.create_table(
        "message_requests",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "relationship_id",
            sa.String(36),
            sa.ForeignKey("direct_message_relationships.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        _profile("sender_profile_id"),
        _profile("recipient_profile_id"),
        sa.Column("note", sa.Text(), nullable=False),
        sa.Column("state", sa.String(16), nullable=False),
        _time("created_at"),
        _time("expires_at"),
        _time("transitioned_at", nullable=True),
        sa.Column(
            "conversation_id",
            sa.String(36),
            sa.ForeignKey("direct_message_conversations.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.Column(
            "first_message_id",
            sa.String(36),
            sa.ForeignKey("direct_messages.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.CheckConstraint(
            "state IN ('accepted','declined','expired','pending','withdrawn')",
            name="ck_message_requests_state",
        ),
        sa.CheckConstraint(
            "sender_profile_id <> recipient_profile_id",
            name="ck_message_requests_distinct_profiles",
        ),
        sa.CheckConstraint(
            "length(trim(note)) > 0 AND length(note) <= 32000",
            name="ck_message_requests_note",
        ),
        sa.CheckConstraint(
            "expires_at > created_at", name="ck_message_requests_expiry"
        ),
        sa.CheckConstraint(
            "(state = 'pending' AND transitioned_at IS NULL) OR (state <> 'pending' AND transitioned_at IS NOT NULL)",
            name="ck_message_requests_transition",
        ),
        sa.CheckConstraint(
            "(state = 'accepted' AND conversation_id IS NOT NULL AND first_message_id IS NOT NULL) OR (state <> 'accepted' AND conversation_id IS NULL AND first_message_id IS NULL)",
            name="ck_message_requests_materialization",
        ),
    )
    op.create_index(
        "uq_message_requests_pending_direction",
        "message_requests",
        ["sender_profile_id", "recipient_profile_id"],
        unique=True,
        postgresql_where=sa.text("state = 'pending'"),
        sqlite_where=sa.text("state = 'pending'"),
    )
    op.create_index(
        "ix_message_requests_recipient_created",
        "message_requests",
        ["recipient_profile_id", "created_at", "id"],
    )
    op.create_index(
        "ix_message_requests_sender_created",
        "message_requests",
        ["sender_profile_id", "created_at", "id"],
    )
    op.create_index(
        "ix_message_requests_expiry", "message_requests", ["state", "expires_at"]
    )
    op.create_table(
        "message_request_attempts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("message_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        _profile("sender_profile_id"),
        _profile("recipient_profile_id"),
        sa.Column("client_request_key", sa.String(128), nullable=False),
        sa.Column("note", sa.Text(), nullable=False),
        _time("created_at"),
        sa.Column(
            "materialized_message_id",
            sa.String(36),
            sa.ForeignKey("direct_messages.id", ondelete="RESTRICT"),
            unique=True,
        ),
        sa.UniqueConstraint(
            "sender_profile_id",
            "client_request_key",
            name="uq_message_request_attempts_sender_key",
        ),
        sa.CheckConstraint(
            "length(trim(client_request_key)) > 0 AND length(client_request_key) <= 128",
            name="ck_message_request_attempts_key",
        ),
        sa.CheckConstraint(
            "length(trim(note)) > 0 AND length(note) <= 32000",
            name="ck_message_request_attempts_note",
        ),
    )
    op.create_index(
        "ix_message_request_attempts_rate",
        "message_request_attempts",
        ["sender_profile_id", "created_at"],
    )
    op.create_table(
        "direct_message_consents",
        sa.Column(
            "relationship_id",
            sa.String(36),
            sa.ForeignKey("direct_message_relationships.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("source", sa.String(32), nullable=False),
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("message_requests.id", ondelete="RESTRICT"),
            unique=True,
        ),
        _time("established_at"),
        sa.CheckConstraint(
            "source IN ('accepted_request','historical_conversation')",
            name="ck_direct_message_consents_source",
        ),
        sa.CheckConstraint(
            "(source = 'historical_conversation' AND request_id IS NULL) OR (source = 'accepted_request' AND request_id IS NOT NULL)",
            name="ck_direct_message_consents_provenance",
        ),
    )
    op.create_table(
        "message_request_suppressions",
        _profile("sender_profile_id", primary_key=True),
        _profile("recipient_profile_id", primary_key=True),
        sa.Column(
            "source_request_id",
            sa.String(36),
            sa.ForeignKey("message_requests.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        _time("created_at"),
        _time("cleared_at", nullable=True),
        sa.CheckConstraint(
            "sender_profile_id <> recipient_profile_id",
            name="ck_message_request_suppressions_distinct_profiles",
        ),
    )
    op.create_table(
        "message_request_preferences",
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "auto_hide_terminal",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
        _time("updated_at"),
    )
    op.create_table(
        "message_request_visibility",
        sa.Column(
            "request_id",
            sa.String(36),
            sa.ForeignKey("message_requests.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column(
            "profile_id",
            sa.String(36),
            sa.ForeignKey("user_profiles.profile_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        _time("hidden_at"),
    )
    op.execute(
        sa.text(
            "INSERT INTO direct_message_consents (relationship_id, source, established_at) "
            "SELECT relationship_id, 'historical_conversation', MIN(created_at) "
            "FROM direct_message_conversations GROUP BY relationship_id"
        )
    )


def downgrade():
    for name in (
        "message_request_visibility",
        "message_request_preferences",
        "message_request_suppressions",
        "message_request_attempts",
        "direct_message_consents",
        "message_requests",
    ):
        op.drop_table(name)
