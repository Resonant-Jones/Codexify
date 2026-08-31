from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest

from guardian.core.db import _PostgresGuardianDB
from guardian.core.default_project import (
    canonicalize_default_project,
    normalize_projects_for_listing,
)
from guardian.core.project_lifecycle import (
    PROJECT_MUST_BE_ARCHIVED_BEFORE_DELETE,
    PROJECT_SYSTEM_CONTAINER_IMMUTABLE,
    ProjectLifecycleError,
)


def _database_with_project(project: MagicMock) -> tuple[_PostgresGuardianDB, MagicMock]:
    database = _PostgresGuardianDB.__new__(_PostgresGuardianDB)
    session = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = False
    database.get_session = MagicMock(return_value=context)  # type: ignore[method-assign]
    project_query = MagicMock()
    project_query.filter_by.return_value.first.return_value = project
    session.query.return_value = project_query
    return database, session


def test_core_rejects_active_project_delete_before_thread_ejection() -> None:
    project = MagicMock(
        id=7,
        user_id="local",
        system_role=None,
        archived_at=None,
    )
    database, session = _database_with_project(project)

    with pytest.raises(ProjectLifecycleError) as raised:
        database.delete_project(7)

    assert raised.value.code == PROJECT_MUST_BE_ARCHIVED_BEFORE_DELETE
    assert session.query.call_count == 1
    session.delete.assert_not_called()
    session.commit.assert_not_called()


@pytest.mark.parametrize("system_role", ["general", "imports"])
def test_core_rejects_built_in_project_lifecycle_mutation(
    system_role: str,
) -> None:
    project = MagicMock(
        id=2,
        user_id="local",
        system_role=system_role,
        archived_at=datetime.now(timezone.utc),
    )
    database, session = _database_with_project(project)

    with pytest.raises(ProjectLifecycleError) as raised:
        database.delete_project(2)

    assert raised.value.code == PROJECT_SYSTEM_CONTAINER_IMMUTABLE
    assert session.query.call_count == 1
    session.delete.assert_not_called()
    session.commit.assert_not_called()


def test_core_archives_and_restores_only_ordinary_projects() -> None:
    project = MagicMock(id=7, system_role=None, archived_at=None)
    database, session = _database_with_project(project)

    database.archive_project(7, True)

    assert project.archived_at is not None
    session.commit.assert_called_once()

    session.reset_mock()
    database.archive_project(7, False)

    assert project.archived_at is None
    session.commit.assert_called_once()


def test_core_ejects_threads_and_deletes_archived_project_in_one_session() -> None:
    project = MagicMock(
        id=7,
        user_id="local",
        system_role=None,
        archived_at=datetime.now(timezone.utc),
    )
    general = MagicMock(id=1, user_id="local", system_role="general")
    database = _PostgresGuardianDB.__new__(_PostgresGuardianDB)
    session = MagicMock()
    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = False
    database.get_session = MagicMock(return_value=context)  # type: ignore[method-assign]

    project_query = MagicMock()
    project_query.filter_by.return_value.first.return_value = project
    general_query = MagicMock()
    general_query.filter_by.return_value.first.return_value = general
    thread_query = MagicMock()
    session.query.side_effect = [project_query, general_query, thread_query]

    assert database.delete_project(7) is True

    thread_query.filter_by.assert_called_once_with(project_id=7)
    thread_query.filter_by.return_value.update.assert_called_once_with(
        {"project_id": 1}
    )
    session.delete.assert_called_once_with(project)
    session.commit.assert_called_once()


def test_renamed_general_role_remains_default_without_rewriting_its_name() -> None:
    database = MagicMock()
    database.list_projects.return_value = [
        {
            "id": 11,
            "name": "Home Base",
            "description": "Default container",
            "system_role": "general",
            "archived_at": None,
        }
    ]

    assert canonicalize_default_project(database) == 11
    assert normalize_projects_for_listing(database.list_projects())[0]["name"] == "Home Base"
    database.ensure_project.assert_not_called()
    database.set_project_system_role.assert_not_called()
    database.update_project.assert_not_called()
