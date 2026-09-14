from __future__ import annotations

import inspect
from collections.abc import Generator

import pytest
import sqlalchemy as sa
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.account_projects import (
    ACCOUNT_GENERAL_PROJECT_DUPLICATE,
    CANONICAL_USER_ID_REQUIRED,
    CANONICAL_USER_NOT_FOUND,
    AccountProjectProvisioningError,
    ensure_account_general_project,
)
from guardian.core.default_project import (
    DEFAULT_PROJECT_DESCRIPTION,
    DEFAULT_PROJECT_NAME,
)
from guardian.core.project_lifecycle import PROJECT_SYSTEM_ROLE_GENERAL
from guardian.db.models import Base, Project, User


@pytest.fixture
def session() -> Generator[Session, None, None]:
    engine = sa.create_engine("sqlite+pysqlite:///:memory:", future=True)
    sa.event.listen(
        engine,
        "connect",
        lambda connection, _: connection.execute("PRAGMA foreign_keys=ON"),
    )
    Base.metadata.create_all(
        engine,
        tables=[User.__table__, Project.__table__],
    )
    factory = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    with factory() as db_session:
        try:
            yield db_session
        finally:
            db_session.rollback()
    engine.dispose()


def _add_user(session: Session, user_id: str) -> User:
    user = User(
        id=user_id,
        username=user_id,
        password_hash="not-a-real-hash",
        role="guest",
    )
    session.add(user)
    session.flush()
    return user


def _general_projects(session: Session, user_id: str) -> list[Project]:
    return list(
        session.execute(
            sa.select(Project).where(
                Project.user_id == user_id,
                Project.system_role == PROJECT_SYSTEM_ROLE_GENERAL,
            )
        ).scalars()
    )


def test_user_id_is_explicit_and_required(session: Session) -> None:
    parameter = inspect.signature(ensure_account_general_project).parameters["user_id"]
    assert parameter.default is inspect.Parameter.empty

    with pytest.raises(TypeError):
        ensure_account_general_project(session)  # type: ignore[call-arg]
    with pytest.raises(AccountProjectProvisioningError) as exc_info:
        ensure_account_general_project(session, "")
    assert exc_info.value.code == CANONICAL_USER_ID_REQUIRED


def test_existing_general_is_returned_without_rewrite(session: Session) -> None:
    _add_user(session, "account-a")
    existing = Project(
        user_id="account-a",
        name="Home Base",
        description="keep this description",
        icon="home",
        identity_depth="deep",
        system_role=PROJECT_SYSTEM_ROLE_GENERAL,
    )
    session.add(existing)
    session.flush()
    existing_id = existing.id

    resolved = ensure_account_general_project(session, "account-a")

    assert resolved is existing
    assert resolved.id == existing_id
    assert resolved.name == "Home Base"
    assert resolved.description == "keep this description"
    assert resolved.icon == "home"
    assert resolved.identity_depth == "deep"
    assert len(_general_projects(session, "account-a")) == 1


def test_missing_general_is_created_and_idempotent(session: Session) -> None:
    _add_user(session, "account-a")

    created = ensure_account_general_project(session, "account-a")
    resolved_again = ensure_account_general_project(session, "account-a")

    assert created.id is not None
    assert resolved_again.id == created.id
    assert created.user_id == "account-a"
    assert created.system_role == PROJECT_SYSTEM_ROLE_GENERAL
    assert created.name == DEFAULT_PROJECT_NAME
    assert created.description == DEFAULT_PROJECT_DESCRIPTION
    assert len(_general_projects(session, "account-a")) == 1


def test_each_account_receives_a_distinct_same_named_general(
    session: Session,
) -> None:
    _add_user(session, "account-a")
    _add_user(session, "account-b")

    general_a = ensure_account_general_project(session, "account-a")
    general_b = ensure_account_general_project(session, "account-b")

    assert general_a.id != general_b.id
    assert general_a.user_id == "account-a"
    assert general_b.user_id == "account-b"
    assert general_a.name == general_b.name == DEFAULT_PROJECT_NAME
    assert _general_projects(session, "account-a") == [general_a]
    assert _general_projects(session, "account-b") == [general_b]


def test_missing_canonical_user_fails_without_creating_project(
    session: Session,
) -> None:
    with pytest.raises(AccountProjectProvisioningError) as exc_info:
        ensure_account_general_project(session, "missing-account")

    assert exc_info.value.code == CANONICAL_USER_NOT_FOUND
    assert session.scalar(sa.select(sa.func.count()).select_from(Project)) == 0
    assert session.scalar(sa.select(sa.func.count()).select_from(User)) == 0


def test_duplicate_general_state_fails_closed(session: Session) -> None:
    session.execute(sa.text("DROP INDEX uq_projects_user_id_system_role"))
    _add_user(session, "account-a")
    session.add_all(
        (
            Project(
                user_id="account-a",
                name="General",
                system_role=PROJECT_SYSTEM_ROLE_GENERAL,
            ),
            Project(
                user_id="account-a",
                name="Home Base",
                system_role=PROJECT_SYSTEM_ROLE_GENERAL,
            ),
        )
    )
    session.flush()

    with pytest.raises(AccountProjectProvisioningError) as exc_info:
        ensure_account_general_project(session, "account-a")

    assert exc_info.value.code == ACCOUNT_GENERAL_PROJECT_DUPLICATE
    assert {project.name for project in _general_projects(session, "account-a")} == {
        "General",
        "Home Base",
    }


def test_caller_rollback_removes_created_general(session: Session) -> None:
    _add_user(session, "account-a")

    created = ensure_account_general_project(session, "account-a")
    created_id = created.id
    session.rollback()

    assert session.get(User, "account-a") is None
    assert session.get(Project, created_id) is None
    assert _general_projects(session, "account-a") == []
