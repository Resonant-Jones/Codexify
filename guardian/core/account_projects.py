"""Account-scoped provisioning for canonical built-in Project containers."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from guardian.core.default_project import (
    DEFAULT_PROJECT_DESCRIPTION,
    DEFAULT_PROJECT_NAME,
)
from guardian.core.project_lifecycle import PROJECT_SYSTEM_ROLE_GENERAL
from guardian.db.models import Project, User


CANONICAL_USER_ID_REQUIRED = "canonical_user_id_required"
CANONICAL_USER_NOT_FOUND = "canonical_user_not_found"
ACCOUNT_GENERAL_PROJECT_DUPLICATE = "account_general_project_duplicate"


class AccountProjectProvisioningError(ValueError):
    """Fail-closed rejection while provisioning an account-owned Project."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


def ensure_account_general_project(session: Session, user_id: str) -> Project:
    """Return or create the explicit account's structural General Project.

    The caller owns the surrounding transaction. Locking the canonical User row
    serializes concurrent calls for the same account; this helper flushes a new
    Project when needed but never commits.
    """
    if not isinstance(user_id, str) or not user_id.strip():
        raise AccountProjectProvisioningError(
            CANONICAL_USER_ID_REQUIRED,
            "An explicit canonical user_id is required.",
        )

    canonical_user = session.execute(
        select(User).where(User.id == user_id).with_for_update()
    ).scalar_one_or_none()
    if canonical_user is None:
        raise AccountProjectProvisioningError(
            CANONICAL_USER_NOT_FOUND,
            f"Canonical User {user_id!r} does not exist.",
        )

    general_projects = list(
        session.execute(
            select(Project)
            .where(
                Project.user_id == user_id,
                Project.system_role == PROJECT_SYSTEM_ROLE_GENERAL,
            )
            .order_by(Project.id)
        ).scalars()
    )
    if len(general_projects) > 1:
        raise AccountProjectProvisioningError(
            ACCOUNT_GENERAL_PROJECT_DUPLICATE,
            f"Canonical User {user_id!r} has multiple General Projects.",
        )
    if general_projects:
        return general_projects[0]

    project = Project(
        user_id=user_id,
        name=DEFAULT_PROJECT_NAME,
        description=DEFAULT_PROJECT_DESCRIPTION,
        system_role=PROJECT_SYSTEM_ROLE_GENERAL,
    )
    session.add(project)
    session.flush()
    return project
