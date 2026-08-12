"""Disposable Postgres transaction proof for explicit repository import."""

from __future__ import annotations

import os
import subprocess
import uuid
from collections.abc import Generator
from pathlib import Path

import pytest

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover - environment specific
    psycopg = None

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.repository_authority import ActiveBindingAlreadyExists
from guardian.core.repository_import import (
    RepositoryBindingOwnedByAnotherAccount,
    import_explicit_repository_candidate,
)
from guardian.db.models import Project, RepositoryBinding


ALEMBIC_HEAD = "6e2b9c4a7d1f"


def _database_url(base_url: str, database_name: str) -> str:
    return make_url(base_url).set(
        drivername="postgresql+psycopg", database=database_name
    ).render_as_string(hide_password=False)


def _admin_database_url(base_url: str) -> str:
    return make_url(base_url).set(
        drivername="postgresql", database="postgres"
    ).render_as_string(hide_password=False)


@pytest.fixture
def disposable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[Engine, None, None]:
    """Create and destroy one uniquely named database under TEST_DATABASE_URL."""
    if psycopg is None:
        pytest.skip("psycopg is required for the disposable Postgres proof")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL is required for the disposable Postgres proof"
        )

    database_name = f"codexify_stage2k3_import_{uuid.uuid4().hex[:12]}"
    admin_url = _admin_database_url(base_url)
    database_url = _database_url(base_url, database_name)
    try:
        with psycopg.connect(admin_url, autocommit=True) as connection:
            with connection.cursor() as cursor:
                cursor.execute(f'CREATE DATABASE "{database_name}"')
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"unable to create disposable Postgres database: {exc}")

    repository_root = Path(__file__).resolve().parents[2]
    config = Config(str(repository_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location", str(repository_root / "guardian" / "db" / "migrations")
    )
    monkeypatch.setenv("DATABASE_URL", database_url)
    engine: Engine | None = None
    try:
        command.upgrade(config, ALEMBIC_HEAD)
        engine = create_engine(database_url, future=True)
        yield engine
    finally:
        if engine is not None:
            engine.dispose()
        try:
            with psycopg.connect(admin_url, autocommit=True) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT pg_terminate_backend(pid) "
                        "FROM pg_stat_activity "
                        "WHERE datname = %s AND pid <> pg_backend_pid()",
                        (database_name,),
                    )
                    cursor.execute(f'DROP DATABASE IF EXISTS "{database_name}"')
        except Exception:
            pass


def _run_git(*args: str, cwd: Path) -> str:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()


def _init_repository(path: Path) -> Path:
    path.mkdir()
    _run_git("init", "--quiet", cwd=path)
    _run_git("config", "user.email", "fixture@example.invalid", cwd=path)
    _run_git("config", "user.name", "Fixture", cwd=path)
    (path / "fixture.txt").write_text("Postgres import fixture\n")
    _run_git("add", "fixture.txt", cwd=path)
    _run_git("commit", "--quiet", "-m", "fixture", cwd=path)
    return path.resolve()


def _seed_account(engine: Engine, account_id: str) -> None:
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES (:id, :username, :password_hash, :role)"
            ),
            {
                "id": account_id,
                "username": account_id,
                "password_hash": "not-a-real-password-hash",
                "role": "guest",
            },
        )


def _import(
    session: Session,
    *,
    account_id: str,
    discovery_root: Path,
    selector: str,
    project_id: int | None = None,
    project_name: str | None = None,
) -> object:
    return import_explicit_repository_candidate(
        session,
        authenticated_account_id=account_id,
        discovery_root=discovery_root,
        candidate_relative_path=selector,
        project_id=project_id,
        project_name=project_name,
        project_description=(
            "transaction proof" if project_id is None else None
        ),
    )


@pytest.mark.integration
def test_repository_import_postgres_commit_rollback_and_conflicts(
    disposable_database: Engine,
    tmp_path: Path,
) -> None:
    engine = disposable_database
    sessions = sessionmaker(engine, expire_on_commit=False, future=True)
    _seed_account(engine, "account-a")
    _seed_account(engine, "account-b")

    discovery_root = tmp_path / "discovery"
    discovery_root.mkdir()
    repository_a = _init_repository(discovery_root / "repository-a")
    repository_b = _init_repository(discovery_root / "repository-b")
    repository_c = _init_repository(discovery_root / "repository-c")
    repository_rollback = _init_repository(discovery_root / "repository-rollback")

    with sessions() as session:
        committed = _import(
            session,
            account_id="account-a",
            discovery_root=discovery_root,
            selector="repository-a",
            project_name="Stage 2K.3 committed project",
        )
        assert session.get(Project, committed.project_id) is not None
        binding_before_commit = session.get(RepositoryBinding, committed.binding_id)
        assert binding_before_commit is not None
        assert binding_before_commit.project_id == committed.project_id
        assert binding_before_commit.source_class == "external_linked"
        assert binding_before_commit.canonical_root == str(repository_a)
        session.commit()

    with sessions() as session:
        persisted_project = session.get(Project, committed.project_id)
        persisted_binding = session.get(RepositoryBinding, committed.binding_id)
        assert persisted_project is not None
        assert persisted_project.user_id == "account-a"
        assert persisted_binding is not None
        assert persisted_binding.is_active is True
        assert persisted_binding.project_id == committed.project_id

    with sessions() as session:
        rolled_back = _import(
            session,
            account_id="account-a",
            discovery_root=discovery_root,
            selector="repository-rollback",
            project_name="Stage 2K.3 rolled back project",
        )
        rolled_back_project_id = rolled_back.project_id
        rolled_back_binding_id = rolled_back.binding_id
        session.rollback()

    with sessions() as session:
        assert session.get(Project, rolled_back_project_id) is None
        assert session.get(RepositoryBinding, rolled_back_binding_id) is None

    with sessions() as session:
        existing_project = Project(
            user_id="account-a",
            name="Stage 2K.3 existing project",
            description="repository-less before explicit import",
        )
        session.add(existing_project)
        session.commit()
        existing_project_id = existing_project.id

    with sessions() as session:
        linked = _import(
            session,
            account_id="account-a",
            discovery_root=discovery_root,
            selector="repository-b",
            project_id=existing_project_id,
        )
        session.commit()
        assert linked.project_id == existing_project_id
        assert linked.created_project is False

    with sessions() as session:
        binding = session.scalar(
            select(RepositoryBinding).where(
                RepositoryBinding.project_id == existing_project_id,
                RepositoryBinding.is_active.is_(True),
            )
        )
        assert binding is not None
        assert binding.canonical_root == str(repository_b)

    with sessions() as session:
        reused = _import(
            session,
            account_id="account-a",
            discovery_root=discovery_root,
            selector="repository-a",
            project_name="This project must not be created",
        )
        assert reused.reused_existing is True
        assert reused.project_id == committed.project_id
        session.commit()

    with sessions() as session:
        with pytest.raises(RepositoryBindingOwnedByAnotherAccount):
            _import(
                session,
                account_id="account-b",
                discovery_root=discovery_root,
                selector="repository-a",
                project_name="Account B must not receive a project",
            )
        session.rollback()

    with sessions() as session:
        account_b_projects = session.scalars(
            select(Project).where(Project.user_id == "account-b")
        ).all()
        assert account_b_projects == []

    with sessions() as session:
        with pytest.raises(ActiveBindingAlreadyExists):
            _import(
                session,
                account_id="account-a",
                discovery_root=discovery_root,
                selector="repository-c",
                project_id=existing_project_id,
            )
        session.rollback()

    with sessions() as session:
        original_binding = session.scalar(
            select(RepositoryBinding).where(
                RepositoryBinding.project_id == existing_project_id,
                RepositoryBinding.is_active.is_(True),
            )
        )
        assert original_binding is not None
        assert original_binding.canonical_root == str(repository_b)
