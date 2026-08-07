"""Add a normalized email login alias to canonical users.

Revision ID: c1a2b3c4d5e6
Revises: d0e1f2a3b4c6
Create Date: 2026-08-03 00:00:00.000000
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.engine import Inspector

revision: str = "c1a2b3c4d5e6"
down_revision: Union[str, Sequence[str], None] = "d0e1f2a3b4c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLE_SCHEMA = "public"
_UNIQUE_CONSTRAINT = "uq_users_email"


def _inspector() -> Inspector:
    return sa.inspect(op.get_bind())


def _fail(detail: str) -> None:
    raise RuntimeError(f"Migration {revision} cannot reconcile users.email: {detail}")


def _ensure_email_column() -> None:
    columns = {
        column["name"]: column
        for column in _inspector().get_columns("users", schema=_TABLE_SCHEMA)
    }
    existing = columns.get("email")
    if existing is None:
        op.add_column(
            "users",
            sa.Column("email", sa.String(length=255), nullable=True),
            schema=_TABLE_SCHEMA,
        )
        return

    column_type = existing["type"]
    if not (
        isinstance(column_type, sa.String)
        and column_type.length == 255
        and existing["nullable"] is True
    ):
        _fail(
            "expected nullable VARCHAR(255), observed "
            f"type={column_type!s}, nullable={existing['nullable']!r}"
        )


def _normalize_and_backfill_email() -> None:
    bind = op.get_bind()
    duplicate = bind.execute(
        sa.text(
            """
            WITH candidates AS (
                SELECT COALESCE(
                    NULLIF(LOWER(BTRIM(email)), ''),
                    CASE
                        WHEN POSITION('@' IN BTRIM(username)) > 1
                         AND POSITION('@' IN BTRIM(username))
                             < LENGTH(BTRIM(username))
                        THEN LOWER(BTRIM(username))
                        ELSE NULL
                    END
                ) AS candidate_email
                FROM users
            )
            SELECT 1
              FROM candidates
             WHERE candidate_email IS NOT NULL
             GROUP BY candidate_email
            HAVING COUNT(*) > 1
             LIMIT 1
            """
        )
    ).first()
    if duplicate is not None:
        _fail("normalization would create a duplicate login alias")

    bind.execute(
        sa.text(
            """
            UPDATE users
               SET email = NULLIF(LOWER(BTRIM(email)), '')
             WHERE email IS NOT NULL
            """
        )
    )
    bind.execute(
        sa.text(
            """
            UPDATE users
               SET email = LOWER(BTRIM(username))
             WHERE email IS NULL
               AND POSITION('@' IN BTRIM(username)) > 1
               AND POSITION('@' IN BTRIM(username))
                   < LENGTH(BTRIM(username))
            """
        )
    )


def _ensure_unique_constraint() -> None:
    constraints = {
        constraint["name"]: constraint
        for constraint in _inspector().get_unique_constraints(
            "users", schema=_TABLE_SCHEMA
        )
    }
    existing = constraints.get(_UNIQUE_CONSTRAINT)
    if existing is not None:
        if existing.get("column_names") != ["email"]:
            _fail(f"constraint {_UNIQUE_CONSTRAINT} does not cover only email")
        return

    op.create_unique_constraint(
        _UNIQUE_CONSTRAINT,
        "users",
        ["email"],
        schema=_TABLE_SCHEMA,
    )


def upgrade() -> None:
    _ensure_email_column()
    _normalize_and_backfill_email()
    _ensure_unique_constraint()


def downgrade() -> None:
    constraints = {
        constraint["name"]: constraint
        for constraint in _inspector().get_unique_constraints(
            "users", schema=_TABLE_SCHEMA
        )
    }
    if _UNIQUE_CONSTRAINT in constraints:
        op.drop_constraint(
            _UNIQUE_CONSTRAINT,
            "users",
            type_="unique",
            schema=_TABLE_SCHEMA,
        )

    columns = {
        column["name"]
        for column in _inspector().get_columns("users", schema=_TABLE_SCHEMA)
    }
    if "email" in columns:
        op.drop_column("users", "email", schema=_TABLE_SCHEMA)
