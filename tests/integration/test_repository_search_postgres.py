"""Disposable Postgres proof for binding-authorized repository search."""

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
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from guardian.core.repository_authority import (
    AccountProjectMismatch,
    SOURCE_CLASS_EXTERNAL_LINKED,
    create_repository_binding,
)
from guardian.core.repository_search import (
    RepositorySearchUnavailable,
    search_project_repository,
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
    """Create and destroy a unique database under the explicit test server."""
    if psycopg is None:
        pytest.skip("psycopg is required for the disposable Postgres proof")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip(
            "TEST_DATABASE_URL is required for the disposable Postgres proof"
        )

    database_name = f"codexify_stage2k4_search_{uuid.uuid4().hex[:12]}"
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


def _init_repository(path: Path, marker: str) -> Path:
    path.mkdir()
    _run_git("init", "--quiet", cwd=path)
    _run_git("config", "user.email", "fixture@example.invalid", cwd=path)
    _run_git("config", "user.name", "Fixture", cwd=path)
    (path / "fixture.txt").write_text(marker + "\n")
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


def _create_bound_project(
    session: Session,
    *,
    account_id: str,
    name: str,
    repository: Path,
) -> tuple[Project, RepositoryBinding]:
    project = Project(
        user_id=account_id,
        name=name,
        description="repository search proof",
    )
    session.add(project)
    session.flush()
    binding = create_repository_binding(
        session,
        authenticated_account_id=account_id,
        project_id=project.id,
        source_class=SOURCE_CLASS_EXTERNAL_LINKED,
        working_tree_root=repository,
        provenance={
            "registration_source": "repository_search_integration_proof",
            "operation_class": "external_link",
        },
    )
    return project, binding


@pytest.mark.integration
def test_repository_search_postgres_authority_and_read_only_proof(
    disposable_database: Engine,
    tmp_path: Path,
) -> None:
    engine = disposable_database
    sessions = sessionmaker(engine, expire_on_commit=False, future=True)
    _seed_account(engine, "account-a")
    _seed_account(engine, "account-b")

    repository_a = _init_repository(tmp_path / "repository-a", "needle-a")
    repository_b = _init_repository(tmp_path / "repository-b", "needle-b")
    repository_stale = _init_repository(
        tmp_path / "repository-stale", "needle-stale"
    )
    fixture = repository_a / "fixture.txt"
    before_bytes = fixture.read_bytes()
    before_head = _run_git("rev-parse", "HEAD", cwd=repository_a)
    before_branch = _run_git(
        "rev-parse", "--abbrev-ref", "HEAD", cwd=repository_a
    )

    with sessions() as session:
        project_a, binding_a = _create_bound_project(
            session,
            account_id="account-a",
            name="Stage 2K.4 Project A",
            repository=repository_a,
        )
        project_stale, _ = _create_bound_project(
            session,
            account_id="account-a",
            name="Stage 2K.4 Project Stale",
            repository=repository_stale,
        )
        repository_less = Project(
            user_id="account-a",
            name="Stage 2K.4 Repository-less",
            description="remains valid without a binding",
        )
        session.add(repository_less)
        session.commit()
        project_a_id = project_a.id
        binding_a_id = binding_a.id
        project_stale_id = project_stale.id
        repository_less_id = repository_less.id

    with sessions() as session:
        before_project_rows = session.scalar(select(func.count()).select_from(Project))
        before_binding_rows = session.scalar(
            select(func.count()).select_from(RepositoryBinding)
        )
        project_before = session.get(Project, project_a_id)
        binding_before = session.get(RepositoryBinding, binding_a_id)
        assert project_before is not None
        assert binding_before is not None
        project_snapshot = (
            project_before.user_id,
            project_before.name,
            project_before.description,
        )
        binding_snapshot = (
            binding_before.canonical_root,
            binding_before.source_class,
            binding_before.is_active,
            dict(binding_before.provenance),
        )

        result = search_project_repository(
            session,
            authenticated_account_id="account-a",
            project_id=project_a_id,
            query="needle-a",
        )
        assert [(match.path, match.line) for match in result.matches] == [
            ("fixture.txt", 1)
        ]
        assert "needle-b" not in repr(result.to_payload())
        assert str(repository_a) not in repr(result.to_payload())
        assert not session.new
        assert not session.dirty
        assert not session.deleted
        assert session.scalar(select(func.count()).select_from(Project)) == before_project_rows
        assert (
            session.scalar(select(func.count()).select_from(RepositoryBinding))
            == before_binding_rows
        )
        project_after = session.get(Project, project_a_id)
        binding_after = session.get(RepositoryBinding, binding_a_id)
        assert project_after is not None
        assert binding_after is not None
        assert (
            project_after.user_id,
            project_after.name,
            project_after.description,
        ) == project_snapshot
        assert (
            binding_after.canonical_root,
            binding_after.source_class,
            binding_after.is_active,
            dict(binding_after.provenance),
        ) == binding_snapshot

    with sessions() as session:
        with pytest.raises(AccountProjectMismatch):
            search_project_repository(
                session,
                authenticated_account_id="account-b",
                project_id=project_a_id,
                query="needle-a",
            )

        with pytest.raises(RepositorySearchUnavailable):
            search_project_repository(
                session,
                authenticated_account_id="account-a",
                project_id=repository_less_id,
                query="needle",
            )

    moved_stale_repository = tmp_path / "repository-stale-moved"
    repository_stale.rename(moved_stale_repository)
    with sessions() as session:
        with pytest.raises(RepositorySearchUnavailable):
            search_project_repository(
                session,
                authenticated_account_id="account-a",
                project_id=project_stale_id,
                query="needle-stale",
            )

    assert fixture.read_bytes() == before_bytes
    assert _run_git("rev-parse", "HEAD", cwd=repository_a) == before_head
    assert (
        _run_git("rev-parse", "--abbrev-ref", "HEAD", cwd=repository_a)
        == before_branch
    )
