"""Reconcile legacy local Project owners from canonical thread evidence.

Every ``projects.user_id = 'local'`` candidate is classified before any
ownership mutation.  Reconciliation succeeds only when all referencing
threads name the same exact non-local canonical user and account-scoped
built-in Project role uniqueness remains valid.

Revision ID: d4e8f1a2b6c9
Revises: c3d9e4f6a8b1
Create Date: 2026-09-04 00:00:00.000000
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from typing import Any, NamedTuple, Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "d4e8f1a2b6c9"
down_revision: str | Sequence[str] | None = "c3d9e4f6a8b1"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_PROJECT_OWNER_SENTINEL = "__codexify_project_owner__"

RECONCILABLE_SINGLE_THREAD_OWNER = "reconcilable_single_thread_owner"
UNRESOLVED_NO_REFERENCING_THREADS = "unresolved_no_referencing_threads"
UNRESOLVED_LOCAL_THREAD_OWNER = "unresolved_local_thread_owner"
UNRESOLVED_MIXED_LOCAL_AND_NON_LOCAL_THREAD_OWNERS = (
    "unresolved_mixed_local_and_non_local_thread_owners"
)
UNRESOLVED_MULTIPLE_THREAD_OWNERS = "unresolved_multiple_thread_owners"
UNRESOLVED_INVALID_THREAD_OWNER = "unresolved_invalid_thread_owner"
UNRESOLVED_MISSING_TARGET_USER = "unresolved_missing_target_user"
UNRESOLVED_PROJECT_CONSTRAINT_CONFLICT = "unresolved_project_constraint_conflict"

PROJECT_OWNERSHIP_RECONCILIATION_UNRESOLVED = (
    "project_ownership_reconciliation_unresolved"
)
PROJECT_OWNERSHIP_RECONCILIATION_PRECONDITION_FAILED = (
    "project_ownership_reconciliation_precondition_failed"
)


class ProjectOwnerReconciliation(NamedTuple):
    project_id: int
    classification: str
    proposed_owner_id: str | None = None
    thread_count: int = 0

    @property
    def is_reconcilable(self) -> bool:
        return self.classification == RECONCILABLE_SINGLE_THREAD_OWNER


def _is_legacy_owner_envelope(description: Any) -> bool:
    if not isinstance(description, str) or not description:
        return False
    try:
        payload = json.loads(description)
    except (TypeError, ValueError):
        return False
    return (
        isinstance(payload, dict) and payload.get(LEGACY_PROJECT_OWNER_SENTINEL) is True
    )


def _abort(token: str, classifications: list[ProjectOwnerReconciliation]) -> None:
    reason_counts = Counter(item.classification for item in classifications)
    detail = {
        "project_ids": sorted(item.project_id for item in classifications),
        "reason_counts": dict(sorted(reason_counts.items())),
    }
    raise RuntimeError(f"{token}:{json.dumps(detail, sort_keys=True)}")


def _classify_local_projects(
    connection,
) -> list[ProjectOwnerReconciliation]:
    projects = [
        dict(row)
        for row in (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, description, system_role "
                    "FROM projects ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
    ]

    precondition_failures = [
        ProjectOwnerReconciliation(
            project_id=int(project["id"]),
            classification=(PROJECT_OWNERSHIP_RECONCILIATION_PRECONDITION_FAILED),
        )
        for project in projects
        if _is_legacy_owner_envelope(project.get("description"))
    ]
    if precondition_failures:
        _abort(
            PROJECT_OWNERSHIP_RECONCILIATION_PRECONDITION_FAILED,
            precondition_failures,
        )

    candidates = [project for project in projects if project["user_id"] == "local"]
    if not candidates:
        return []

    candidate_ids = [int(project["id"]) for project in candidates]
    thread_statement = sa.text(
        "SELECT id, project_id, user_id FROM chat_threads "
        "WHERE project_id IN :project_ids ORDER BY project_id, id"
    ).bindparams(sa.bindparam("project_ids", expanding=True))
    thread_rows = [
        dict(row)
        for row in (
            connection.execute(thread_statement, {"project_ids": candidate_ids})
            .mappings()
            .all()
        )
    ]
    threads_by_project: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for thread in thread_rows:
        threads_by_project[int(thread["project_id"])].append(thread)

    canonical_user_ids = {
        row["id"]
        for row in connection.execute(sa.text("SELECT id FROM users")).mappings().all()
    }

    classifications: list[ProjectOwnerReconciliation] = []
    candidate_by_id = {int(project["id"]): project for project in candidates}
    for project_id in candidate_ids:
        threads = threads_by_project.get(project_id, [])
        if not threads:
            classifications.append(
                ProjectOwnerReconciliation(
                    project_id=project_id,
                    classification=UNRESOLVED_NO_REFERENCING_THREADS,
                )
            )
            continue

        owner_values = [thread.get("user_id") for thread in threads]
        if any(
            not isinstance(owner_id, str)
            or not owner_id
            or owner_id.strip() != owner_id
            for owner_id in owner_values
        ):
            classifications.append(
                ProjectOwnerReconciliation(
                    project_id=project_id,
                    classification=UNRESOLVED_INVALID_THREAD_OWNER,
                    thread_count=len(threads),
                )
            )
            continue

        distinct_owner_ids = set(owner_values)
        if distinct_owner_ids == {"local"}:
            classifications.append(
                ProjectOwnerReconciliation(
                    project_id=project_id,
                    classification=UNRESOLVED_LOCAL_THREAD_OWNER,
                    thread_count=len(threads),
                )
            )
            continue
        if len(distinct_owner_ids) != 1:
            classification = (
                UNRESOLVED_MIXED_LOCAL_AND_NON_LOCAL_THREAD_OWNERS
                if "local" in distinct_owner_ids
                else UNRESOLVED_MULTIPLE_THREAD_OWNERS
            )
            classifications.append(
                ProjectOwnerReconciliation(
                    project_id=project_id,
                    classification=classification,
                    thread_count=len(threads),
                )
            )
            continue

        proposed_owner_id = next(iter(distinct_owner_ids))
        if proposed_owner_id not in canonical_user_ids:
            classifications.append(
                ProjectOwnerReconciliation(
                    project_id=project_id,
                    classification=UNRESOLVED_MISSING_TARGET_USER,
                    thread_count=len(threads),
                )
            )
            continue

        classifications.append(
            ProjectOwnerReconciliation(
                project_id=project_id,
                classification=RECONCILABLE_SINGLE_THREAD_OWNER,
                proposed_owner_id=proposed_owner_id,
                thread_count=len(threads),
            )
        )

    occupied_roles = {
        (project["user_id"], project["system_role"])
        for project in projects
        if project["user_id"] != "local" and project["system_role"] is not None
    }
    proposed_roles: dict[tuple[str, str], list[int]] = defaultdict(list)
    for index, result in enumerate(classifications):
        project = candidate_by_id[result.project_id]
        role = project["system_role"]
        if result.is_reconcilable and role is not None:
            proposed_roles[(result.proposed_owner_id, role)].append(index)

    conflict_indexes: set[int] = set()
    for role_key, indexes in proposed_roles.items():
        if role_key in occupied_roles or len(indexes) > 1:
            conflict_indexes.update(indexes)
    for index in conflict_indexes:
        classifications[index] = classifications[index]._replace(
            classification=UNRESOLVED_PROJECT_CONSTRAINT_CONFLICT,
            proposed_owner_id=None,
        )

    return classifications


def upgrade() -> None:
    """Reconcile all legacy local Projects or fail without partial mutation."""

    connection = op.get_bind()
    classifications = _classify_local_projects(connection)
    unresolved = [item for item in classifications if not item.is_reconcilable]
    if unresolved:
        _abort(PROJECT_OWNERSHIP_RECONCILIATION_UNRESOLVED, unresolved)

    for item in classifications:
        result = connection.execute(
            sa.text(
                "UPDATE projects SET user_id = :owner_id "
                "WHERE id = :project_id AND user_id = 'local'"
            ),
            {"owner_id": item.proposed_owner_id, "project_id": item.project_id},
        )
        if result.rowcount != 1:
            _abort(PROJECT_OWNERSHIP_RECONCILIATION_UNRESOLVED, [item])

    remaining_local = connection.execute(
        sa.text("SELECT count(*) FROM projects WHERE user_id = 'local'")
    ).scalar_one()
    if int(remaining_local) != 0:
        _abort(PROJECT_OWNERSHIP_RECONCILIATION_UNRESOLVED, classifications)


def downgrade() -> None:
    """No-op: never manufacture ambiguous legacy ``local`` ownership."""

    return None
