"""Add canonical Saved Widget identity and immutable revision storage.

Revision ID: a6b9d2e4f701
Revises: f0d7c4b2a198

Two tables, co-authoritative with the ORM models in ``guardian/db/models.py``:

``saved_widgets``
    One canonical widget identity, one account owner, one forward-only
    current-revision pointer, and an explicit lifecycle state.

``saved_widget_revisions``
    Immutable revision snapshots keyed by ``(widget_id, revision)``. The
    artifact, the server-proven provenance, and the revision-creation context
    are denormalized into the row, because their referents cascade on source
    deletion: deleting the source thread must not delete, alter, or
    un-provenance a Saved Widget.

The two tables reference each other. ``saved_widget_revisions.widget_id`` points
at the owning widget and cascades with it, while ``saved_widgets`` points at the
revision named by its current-revision pointer through a *deferrable* composite
foreign key. The deferral is what lets the widget row and revision 1 be
written in one transaction: the pointer is checked at commit time, so the
database never observes a widget whose current revision does not exist, and
never has to observe a half-built widget in between.

Revision rows are protected from in-place update by a narrow database guard.
Historical revisions are never overwritten; a correction is a new revision.
"""

from __future__ import annotations

from typing import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "a6b9d2e4f701"
down_revision: str | Sequence[str] | None = "f0d7c4b2a198"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


WIDGETS_TABLE = "saved_widgets"
REVISIONS_TABLE = "saved_widget_revisions"

LIFECYCLE_VALUES_SQL = "','".join(("active", "archived", "deleted"))

# Narrow update guard: a stored revision is a snapshot, not a mutable record.
# DELETE is deliberately not guarded, because a revision is removed only by
# cascading with the widget it belongs to.
IMMUTABILITY_FUNCTION = "codexify_saved_widget_revisions_immutable"
IMMUTABILITY_TRIGGER = "trg_saved_widget_revisions_immutable"


def _jsonb_type() -> sa.types.TypeEngine:
    """JSONB on Postgres, portable JSON elsewhere.

    The repository is Postgres-only, but the ORM carries a portable variant
    for the same column, and the migration and the ORM must agree.
    """
    return sa.JSON().with_variant(postgresql.JSONB(), "postgresql")


def upgrade() -> None:
    op.create_table(
        WIDGETS_TABLE,
        sa.Column("widget_id", sa.String(length=64), nullable=False),
        sa.Column("owner_user_id", sa.String(length=255), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column(
            "lifecycle_state",
            sa.String(length=16),
            nullable=False,
            server_default="active",
        ),
        sa.Column("current_revision", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint("widget_id", name="pk_saved_widgets"),
        sa.ForeignKeyConstraint(
            ["owner_user_id"],
            ["users.id"],
            name="fk_saved_widgets_owner_user_id",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "lifecycle_state IN ('" + LIFECYCLE_VALUES_SQL + "')",
            name="saved_widgets_lifecycle_state_check",
        ),
        sa.CheckConstraint(
            "current_revision > 0",
            name="saved_widgets_current_revision_check",
        ),
    )

    op.create_table(
        REVISIONS_TABLE,
        sa.Column("widget_id", sa.String(length=64), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("artifact_snapshot", _jsonb_type(), nullable=False),
        sa.Column("provenance_snapshot", _jsonb_type(), nullable=False),
        sa.Column("creation_context", _jsonb_type(), nullable=False),
        sa.Column("edit_base_revision", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.PrimaryKeyConstraint(
            "widget_id",
            "revision",
            name="pk_saved_widget_revisions",
        ),
        sa.ForeignKeyConstraint(
            ["widget_id"],
            [f"{WIDGETS_TABLE}.widget_id"],
            name="fk_saved_widget_revisions_widget",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "revision > 0",
            name="saved_widget_revisions_revision_check",
        ),
        sa.CheckConstraint(
            "edit_base_revision IS NULL OR "
            "(edit_base_revision > 0 AND edit_base_revision < revision)",
            name="saved_widget_revisions_edit_base_check",
        ),
        # The edit base must name a revision of this same widget. Deferred so
        # that a revision and its base may be written in either order inside
        # one transaction, and checked at commit time.
        sa.ForeignKeyConstraint(
            ["widget_id", "edit_base_revision"],
            [f"{REVISIONS_TABLE}.widget_id", f"{REVISIONS_TABLE}.revision"],
            name="fk_saved_widget_revisions_edit_base",
            deferrable=True,
            initially="DEFERRED",
        ),
    )

    # Added after both tables exist, because the pointer and the revisions it
    # names are mutually referential.
    op.create_foreign_key(
        "fk_saved_widgets_current_revision",
        WIDGETS_TABLE,
        REVISIONS_TABLE,
        ["widget_id", "current_revision"],
        ["widget_id", "revision"],
        deferrable=True,
        initially="DEFERRED",
    )

    op.create_index(
        "ix_saved_widgets_owner_user_id",
        WIDGETS_TABLE,
        ["owner_user_id"],
    )
    op.create_index(
        "ix_saved_widget_revisions_widget_created_at",
        REVISIONS_TABLE,
        ["widget_id", "created_at"],
    )

    op.execute(
        f"""
        CREATE OR REPLACE FUNCTION {IMMUTABILITY_FUNCTION}() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION
                'saved_widget_revisions rows are immutable (widget_id=%, revision=%); '
                'create a new revision instead',
                OLD.widget_id, OLD.revision
                USING ERRCODE = 'integrity_constraint_violation';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        f"""
        CREATE TRIGGER {IMMUTABILITY_TRIGGER}
        BEFORE UPDATE ON {REVISIONS_TABLE}
        FOR EACH ROW EXECUTE FUNCTION {IMMUTABILITY_FUNCTION}();
        """
    )


def downgrade() -> None:
    op.execute(f"DROP TRIGGER IF EXISTS {IMMUTABILITY_TRIGGER} ON {REVISIONS_TABLE};")
    op.execute(f"DROP FUNCTION IF EXISTS {IMMUTABILITY_FUNCTION}();")
    op.drop_constraint(
        "fk_saved_widgets_current_revision",
        WIDGETS_TABLE,
        type_="foreignkey",
    )
    op.drop_table(REVISIONS_TABLE)
    op.drop_table(WIDGETS_TABLE)
