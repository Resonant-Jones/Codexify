"""Disposable Postgres proof for ordinary-chat repository eligibility."""

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

from guardian.core.chatlog_postgres import PostgresChatLogDB
from guardian.core.repository_authority import (
    SOURCE_CLASS_EXTERNAL_LINKED,
    create_repository_binding,
)
from guardian.core.repository_chat_capability import (
    resolve_repository_chat_capability,
)
from guardian.db.models import ChatThread, Project, RepositoryBinding


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
    if psycopg is None:
        pytest.skip("psycopg is required for the disposable Postgres proof")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL is required for the disposable Postgres proof")

    database_name = f"codexify_stage2k5_capability_{uuid.uuid4().hex[:12]}"
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
    (path / "fixture.txt").write_text("repository chat capability fixture\n")
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
        description="repository chat capability proof",
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
            "registration_source": "repository_chat_capability_integration_proof",
            "operation_class": "external_link",
        },
    )
    return project, binding


@pytest.mark.integration
def test_repository_chat_capability_postgres_authority_and_read_only_proof(
    disposable_database: Engine,
    tmp_path: Path,
) -> None:
    engine = disposable_database
    sessions = sessionmaker(engine, expire_on_commit=False, future=True)
    _seed_account(engine, "account-a")
    _seed_account(engine, "account-b")
    repository_a = _init_repository(tmp_path / "repository-a")
    repository_b = _init_repository(tmp_path / "repository-b")
    repository_stale = _init_repository(tmp_path / "repository-stale")

    with sessions() as session:
        project_a, binding_a = _create_bound_project(
            session,
            account_id="account-a",
            name="Stage 2K.5 Project A",
            repository=repository_a,
        )
        project_b, _ = _create_bound_project(
            session,
            account_id="account-b",
            name="Stage 2K.5 Project B",
            repository=repository_b,
        )
        project_stale, _ = _create_bound_project(
            session,
            account_id="account-a",
            name="Stage 2K.5 Project Stale",
            repository=repository_stale,
        )
        repository_less = Project(
            user_id="account-a",
            name="Stage 2K.5 Repository-less",
            description="remains valid without a binding",
        )
        session.add(repository_less)
        session.flush()
        thread_a = ChatThread(
            user_id="account-a",
            title="Stage 2K.5 Thread A",
            project_id=project_a.id,
        )
        thread_repository_less = ChatThread(
            user_id="account-a",
            title="Stage 2K.5 Repository-less Thread",
            project_id=repository_less.id,
        )
        thread_cross_project = ChatThread(
            user_id="account-a",
            title="Stage 2K.5 Cross-Account Project Thread",
            project_id=project_b.id,
        )
        thread_stale = ChatThread(
            user_id="account-a",
            title="Stage 2K.5 Stale Thread",
            project_id=project_stale.id,
        )
        session.add_all(
            [thread_a, thread_repository_less, thread_cross_project, thread_stale]
        )
        session.commit()
        project_a_id = project_a.id
        binding_a_id = binding_a.id
        repository_less_id = repository_less.id
        thread_a_id = thread_a.id
        thread_repository_less_id = thread_repository_less.id
        thread_cross_project_id = thread_cross_project.id
        thread_stale_id = thread_stale.id

    database_url = engine.url.render_as_string(hide_password=False)
    chatlog_db = PostgresChatLogDB(database_url)
    try:
        with sessions() as session:
            before_project_rows = session.scalar(
                select(func.count()).select_from(Project)
            )
            before_binding_rows = session.scalar(
                select(func.count()).select_from(RepositoryBinding)
            )
            before_thread_rows = session.scalar(
                select(func.count()).select_from(ChatThread)
            )
            project_before = session.get(Project, project_a_id)
            binding_before = session.get(RepositoryBinding, binding_a_id)
            thread_before = session.get(ChatThread, thread_a_id)
            assert project_before is not None
            assert binding_before is not None
            assert thread_before is not None
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
            thread_snapshot = (
                thread_before.user_id,
                thread_before.project_id,
                thread_before.title,
            )

            context = resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-a",
                thread_id=thread_a_id,
            )
            assert context is not None
            assert context.project_id == project_a_id
            assert not hasattr(context, "binding_id")
            assert not hasattr(context, "canonical_root")
            assert not session.new
            assert not session.dirty
            assert not session.deleted
            assert session.scalar(select(func.count()).select_from(Project)) == before_project_rows
            assert (
                session.scalar(select(func.count()).select_from(RepositoryBinding))
                == before_binding_rows
            )
            assert (
                session.scalar(select(func.count()).select_from(ChatThread))
                == before_thread_rows
            )
            project_after = session.get(Project, project_a_id)
            binding_after = session.get(RepositoryBinding, binding_a_id)
            thread_after = session.get(ChatThread, thread_a_id)
            assert project_after is not None
            assert binding_after is not None
            assert thread_after is not None
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
            assert (
                thread_after.user_id,
                thread_after.project_id,
                thread_after.title,
            ) == thread_snapshot

        assert (
            resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-a",
                thread_id=thread_repository_less_id,
            )
            is None
        )
        assert (
            resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-b",
                thread_id=thread_a_id,
            )
            is None
        )
        assert (
            resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-a",
                thread_id=thread_cross_project_id,
            )
            is None
        )

        moved_stale_repository = tmp_path / "repository-stale-moved"
        repository_stale.rename(moved_stale_repository)
        assert (
            resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-a",
                thread_id=thread_stale_id,
            )
            is None
        )

        with sessions() as session:
            thread_to_move = session.get(ChatThread, thread_a_id)
            assert thread_to_move is not None
            thread_to_move.project_id = repository_less_id
            session.commit()
        assert (
            resolve_repository_chat_capability(
                chatlog_db,
                authenticated_account_id="account-a",
                thread_id=thread_a_id,
            )
            is None
        )
    finally:
        chatlog_db._sa_engine.dispose()
