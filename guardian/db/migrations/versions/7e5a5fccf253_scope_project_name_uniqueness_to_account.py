"""Scope Project display-name uniqueness to canonical account ownership.

Revision ID: 7e5a5fccf253
Revises: f6b0d3e8c5a2
Create Date: 2026-09-10 09:45:45.390203

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision: str = "7e5a5fccf253"
down_revision: str | Sequence[str] | None = "f6b0d3e8c5a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

ACCOUNT_PROJECT_NAME_UNIQUE = "uq_projects_user_id_name"
DOWNGRADE_GLOBAL_PROJECT_NAME_UNIQUE = "uq_projects_name"

PROJECT_NAME_SCOPE_SOURCE_UNEXPECTED = "project_name_scope_source_unexpected"
PROJECT_NAME_SCOPE_TARGET_UNEXPECTED = "project_name_scope_target_unexpected"
PROJECT_NAME_SCOPE_DOWNGRADE_DUPLICATES = (
    "project_name_scope_downgrade_cross_account_duplicates"
)


def _unique_constraints(connection: Any) -> list[dict[str, Any]]:
    return list(sa.inspect(connection).get_unique_constraints("projects"))


def _constraints_for_columns(
    constraints: Sequence[dict[str, Any]],
    columns: Sequence[str],
) -> list[dict[str, Any]]:
    expected = tuple(columns)
    return [
        constraint
        for constraint in constraints
        if tuple(constraint.get("column_names") or ()) == expected
    ]


def _require_single_constraint_name(
    constraints: Sequence[dict[str, Any]],
    columns: Sequence[str],
    *,
    error_code: str,
) -> str:
    matches = _constraints_for_columns(constraints, columns)
    if len(matches) != 1 or not isinstance(matches[0].get("name"), str):
        raise RuntimeError(
            f"{error_code}: expected exactly one projects unique constraint "
            f"on {tuple(columns)!r}; found {len(matches)}"
        )
    return str(matches[0]["name"])


def upgrade() -> None:
    """Replace global Project-name uniqueness with account-scoped uniqueness."""
    connection = op.get_bind()
    constraints = _unique_constraints(connection)
    global_name_constraint = _require_single_constraint_name(
        constraints,
        ("name",),
        error_code=PROJECT_NAME_SCOPE_SOURCE_UNEXPECTED,
    )
    if _constraints_for_columns(constraints, ("user_id", "name")):
        raise RuntimeError(
            f"{PROJECT_NAME_SCOPE_SOURCE_UNEXPECTED}: account-scoped Project "
            "name uniqueness already exists"
        )

    op.drop_constraint(global_name_constraint, "projects", type_="unique")
    op.create_unique_constraint(
        ACCOUNT_PROJECT_NAME_UNIQUE,
        "projects",
        ["user_id", "name"],
    )


def downgrade() -> None:
    """Restore global uniqueness only when no cross-account names collide."""
    connection = op.get_bind()
    constraints = _unique_constraints(connection)
    account_name_constraint = _require_single_constraint_name(
        constraints,
        ("user_id", "name"),
        error_code=PROJECT_NAME_SCOPE_TARGET_UNEXPECTED,
    )
    if _constraints_for_columns(constraints, ("name",)):
        raise RuntimeError(
            f"{PROJECT_NAME_SCOPE_TARGET_UNEXPECTED}: global Project name "
            "uniqueness still exists"
        )

    duplicate_name_groups = connection.execute(
        sa.text(
            "SELECT count(*) FROM ("
            "SELECT name FROM projects GROUP BY name HAVING count(*) > 1"
            ") AS duplicate_project_names"
        )
    ).scalar_one()
    if int(duplicate_name_groups) != 0:
        raise RuntimeError(PROJECT_NAME_SCOPE_DOWNGRADE_DUPLICATES)

    op.drop_constraint(account_name_constraint, "projects", type_="unique")
    op.create_unique_constraint(
        DOWNGRADE_GLOBAL_PROJECT_NAME_UNIQUE,
        "projects",
        ["name"],
    )
