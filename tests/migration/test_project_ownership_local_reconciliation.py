"""Proof for ADR-081 legacy ``local`` Project ownership reconciliation."""

from __future__ import annotations

import hashlib
import importlib
import json
import os
import uuid
from pathlib import Path

import pytest
import sqlalchemy as sa
from sqlalchemy.engine import make_url

try:
    import psycopg  # type: ignore
except ImportError:  # pragma: no cover - environment specific
    psycopg = None


PRE_UMS_01_REVISION = "b2c8d0e3f5a7"
UMS_01A_REVISION = "c3d9e4f6a8b1"
UMS_01B_REVISION = "d4e8f1a2b6c9"
MIGRATION_MODULE = (
    "guardian.db.migrations.versions.d4e8f1a2b6c9_reconcile_legacy_local_project_owners"
)


def _migration():
    return importlib.import_module(MIGRATION_MODULE)


def _envelope(owner_id: str, description: str) -> str:
    return json.dumps(
        {
            "__codexify_project_owner__": True,
            "owner_user_id": owner_id,
            "description": description,
        },
        ensure_ascii=False,
        sort_keys=True,
    )


class _FakeMappings:
    def __init__(self, rows):
        self._rows = rows

    def all(self):
        return self._rows


class _FakeResult:
    def __init__(self, rows=(), *, scalar=None, rowcount=0):
        self._rows = list(rows)
        self._scalar = scalar
        self.rowcount = rowcount

    def mappings(self):
        return _FakeMappings(self._rows)

    def scalar_one(self):
        return self._scalar


class _FakeConnection:
    def __init__(self, *, projects, threads=(), users=()):
        self.projects = [dict(row) for row in projects]
        self.threads = [dict(row) for row in threads]
        self.users = [{"id": user_id} for user_id in users]
        self.updates: list[dict[str, object]] = []

    def execute(self, statement, parameters=None):
        sql = " ".join(str(statement).split())
        if sql.startswith("SELECT id, user_id, description, system_role FROM projects"):
            return _FakeResult(self.projects)
        if sql.startswith("SELECT id, project_id, user_id FROM chat_threads"):
            project_ids = set((parameters or {}).get("project_ids", []))
            return _FakeResult(
                row for row in self.threads if row["project_id"] in project_ids
            )
        if sql == "SELECT id FROM users":
            return _FakeResult(self.users)
        if sql.startswith("UPDATE projects SET user_id"):
            params = dict(parameters or {})
            for project in self.projects:
                if (
                    project["id"] == params["project_id"]
                    and project["user_id"] == "local"
                ):
                    project["user_id"] = params["owner_id"]
                    self.updates.append(params)
                    return _FakeResult(rowcount=1)
            return _FakeResult(rowcount=0)
        if sql == "SELECT count(*) FROM projects WHERE user_id = 'local'":
            remaining = sum(project["user_id"] == "local" for project in self.projects)
            return _FakeResult(scalar=remaining)
        raise AssertionError(f"Unexpected migration SQL: {sql}")


def _classification_by_project(connection):
    return {
        item.project_id: item
        for item in _migration()._classify_local_projects(connection)
    }


def test_classifies_single_and_multiple_same_owner_threads_as_reconcilable():
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {"id": 1, "user_id": "local", "description": "one", "system_role": None},
            {"id": 2, "user_id": "local", "description": "two", "system_role": None},
        ],
        threads=[
            {"id": 11, "project_id": 1, "user_id": "owner-a"},
            {"id": 21, "project_id": 2, "user_id": "owner-a"},
            {"id": 22, "project_id": 2, "user_id": "owner-a"},
        ],
        users=["local", "owner-a"],
    )

    classified = _classification_by_project(connection)

    assert classified[1].classification == migration.RECONCILABLE_SINGLE_THREAD_OWNER
    assert classified[1].proposed_owner_id == "owner-a"
    assert classified[1].thread_count == 1
    assert classified[2].classification == migration.RECONCILABLE_SINGLE_THREAD_OWNER
    assert classified[2].proposed_owner_id == "owner-a"
    assert classified[2].thread_count == 2


@pytest.mark.parametrize(
    ("threads", "users", "expected"),
    [
        ([], ["local", "owner-a"], "UNRESOLVED_NO_REFERENCING_THREADS"),
        (["local"], ["local", "owner-a"], "UNRESOLVED_LOCAL_THREAD_OWNER"),
        (
            ["local", "owner-a"],
            ["local", "owner-a"],
            "UNRESOLVED_MIXED_LOCAL_AND_NON_LOCAL_THREAD_OWNERS",
        ),
        (
            ["owner-a", "owner-b"],
            ["local", "owner-a", "owner-b"],
            "UNRESOLVED_MULTIPLE_THREAD_OWNERS",
        ),
        ([" owner-a"], ["local", " owner-a"], "UNRESOLVED_INVALID_THREAD_OWNER"),
        (["missing-owner"], ["local"], "UNRESOLVED_MISSING_TARGET_USER"),
    ],
)
def test_classifies_every_unresolved_thread_evidence_shape(
    threads,
    users,
    expected,
):
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {
                "id": 1,
                "user_id": "local",
                "description": "description",
                "system_role": None,
            }
        ],
        threads=[
            {"id": index + 1, "project_id": 1, "user_id": owner_id}
            for index, owner_id in enumerate(threads)
        ],
        users=users,
    )

    classified = _classification_by_project(connection)[1]

    assert classified.classification == getattr(migration, expected)
    assert classified.proposed_owner_id is None


def test_classifies_existing_and_proposed_builtin_role_collisions():
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {
                "id": 1,
                "user_id": "owner-a",
                "description": "canonical",
                "system_role": "general",
            },
            {
                "id": 2,
                "user_id": "local",
                "description": "legacy one",
                "system_role": "general",
            },
            {
                "id": 3,
                "user_id": "local",
                "description": "legacy two",
                "system_role": "imports",
            },
            {
                "id": 4,
                "user_id": "local",
                "description": "legacy three",
                "system_role": "imports",
            },
        ],
        threads=[
            {"id": 12, "project_id": 2, "user_id": "owner-a"},
            {"id": 13, "project_id": 3, "user_id": "owner-a"},
            {"id": 14, "project_id": 4, "user_id": "owner-a"},
        ],
        users=["local", "owner-a"],
    )

    classified = _classification_by_project(connection)

    assert all(
        classified[project_id].classification
        == migration.UNRESOLVED_PROJECT_CONSTRAINT_CONFLICT
        for project_id in (2, 3, 4)
    )


def test_precondition_rejects_surviving_legacy_envelope_before_thread_queries():
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {
                "id": 1,
                "user_id": "local",
                "description": _envelope("local", "description"),
                "system_role": None,
            }
        ],
        users=["local", "owner-a"],
    )

    with pytest.raises(
        RuntimeError,
        match=migration.PROJECT_OWNERSHIP_RECONCILIATION_PRECONDITION_FAILED,
    ):
        migration._classify_local_projects(connection)

    assert connection.updates == []


def test_upgrade_classifies_all_candidates_before_any_mutation(monkeypatch):
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {
                "id": 1,
                "user_id": "local",
                "description": "reconcilable",
                "system_role": None,
            },
            {
                "id": 2,
                "user_id": "local",
                "description": "unresolved",
                "system_role": None,
            },
        ],
        threads=[{"id": 11, "project_id": 1, "user_id": "owner-a"}],
        users=["local", "owner-a"],
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    with pytest.raises(
        RuntimeError,
        match=migration.PROJECT_OWNERSHIP_RECONCILIATION_UNRESOLVED,
    ):
        migration.upgrade()

    assert connection.updates == []
    assert [project["user_id"] for project in connection.projects] == [
        "local",
        "local",
    ]


def test_upgrade_mutates_only_reconcilable_local_projects(monkeypatch):
    migration = _migration()
    connection = _FakeConnection(
        projects=[
            {
                "id": 1,
                "user_id": "local",
                "description": "legacy",
                "system_role": None,
            },
            {
                "id": 2,
                "user_id": "owner-b",
                "description": "canonical",
                "system_role": None,
            },
        ],
        threads=[
            {"id": 11, "project_id": 1, "user_id": "owner-a"},
            {"id": 12, "project_id": 2, "user_id": "owner-b"},
        ],
        users=["local", "owner-a", "owner-b"],
    )
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    migration.upgrade()

    assert connection.updates == [{"owner_id": "owner-a", "project_id": 1}]
    assert [project["user_id"] for project in connection.projects] == [
        "owner-a",
        "owner-b",
    ]


def test_downgrade_is_non_fabricating_no_op(monkeypatch):
    migration = _migration()
    connection = _FakeConnection(projects=[], users=[])
    monkeypatch.setattr(migration.op, "get_bind", lambda: connection)

    assert migration.downgrade() is None
    assert connection.updates == []


def _database_url(base_url: str, database_name: str) -> str:
    return (
        make_url(base_url)
        .set(database=database_name)
        .render_as_string(hide_password=False)
    )


def _admin_database_url(base_url: str) -> str:
    return (
        make_url(base_url)
        .set(drivername="postgresql", database="postgres")
        .render_as_string(hide_password=False)
    )


@pytest.fixture
def temporary_postgres(monkeypatch):
    if psycopg is None:
        pytest.skip("psycopg not installed")

    base_url = os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL or DATABASE_URL environment variable required")

    admin_url = _admin_database_url(base_url)
    database_name = f"codexify_local_owner_{uuid.uuid4().hex[:10]}"
    database_url = _database_url(base_url, database_name)

    try:
        admin_connection = psycopg.connect(admin_url, autocommit=True)
    except Exception as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to connect to admin database: {exc}")

    try:
        with admin_connection.cursor() as cursor:
            cursor.execute(f"CREATE DATABASE {database_name}")
    except psycopg.Error as exc:  # pragma: no cover - environment specific
        pytest.skip(f"Unable to create test database: {exc.sqlstate}")
    finally:
        admin_connection.close()

    from alembic.config import Config

    repo_root = Path(__file__).resolve().parents[2]
    config = Config(str(repo_root / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url)
    config.set_main_option(
        "script_location",
        str(repo_root / "guardian" / "db" / "migrations"),
    )
    monkeypatch.setenv("DATABASE_URL", database_url)

    try:
        yield config, database_url
    finally:
        cleanup_connection = psycopg.connect(admin_url, autocommit=True)
        try:
            with cleanup_connection.cursor() as cursor:
                cursor.execute(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity WHERE datname = %s",
                    (database_name,),
                )
                cursor.execute(f"DROP DATABASE IF EXISTS {database_name}")
        finally:
            cleanup_connection.close()


def _upgrade_to(config, revision: str) -> None:
    from alembic import command

    command.upgrade(config, revision)


def _downgrade_to(config, revision: str) -> None:
    from alembic import command

    command.downgrade(config, revision)


def _seed_users(connection) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) VALUES "
            "('account-a', 'local-owner-a', 'not-a-real-hash', 'guest'), "
            "('account-b', 'local-owner-b', 'not-a-real-hash', 'guest'), "
            "('local', 'local-owner-legacy', 'not-a-real-hash', 'guest')"
        )
    )


def _digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


@pytest.mark.integration
def test_postgres_complete_ums_01_chain_reconciles_and_preserves_state(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)
    exact_description = "  exact legacy description\nwith unicode café  "

    _upgrade_to(config, PRE_UMS_01_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, user_id, name, description, archived_at) VALUES "
                "(901, 'local', 'Local chain one', :description, NULL), "
                "(902, 'local', 'Local chain two', 'plain two', NULL), "
                "(903, 'account-b', 'Canonical second account', "
                "'second account description', NULL)"
            ),
            {"description": _envelope("local", exact_description)},
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_threads (id, user_id, project_id, title) VALUES "
                "(911, 'account-a', 901, 'First evidence thread'), "
                "(912, 'account-a', 902, 'Second evidence thread'), "
                "(913, 'account-a', 902, 'Third evidence thread'), "
                "(914, 'account-b', 903, 'Second account thread')"
            )
        )

    _upgrade_to(config, UMS_01B_REVISION)
    _upgrade_to(config, UMS_01B_REVISION)

    with engine.connect() as connection:
        projects = (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, description, archived_at FROM projects "
                    "WHERE id BETWEEN 901 AND 903 ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
        threads = (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, project_id FROM chat_threads "
                    "WHERE id BETWEEN 911 AND 914 ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
        current_revision = connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert [row["id"] for row in projects] == [901, 902, 903]
    assert [row["user_id"] for row in projects] == [
        "account-a",
        "account-a",
        "account-b",
    ]
    assert projects[0]["description"] == exact_description
    assert len(projects[0]["description"]) == len(exact_description)
    assert _digest(projects[0]["description"]) == _digest(exact_description)
    assert projects[1]["description"] == "plain two"
    assert projects[2]["description"] == "second account description"
    assert all(row["archived_at"] is None for row in projects)
    assert [dict(row) for row in threads] == [
        {"id": 911, "user_id": "account-a", "project_id": 901},
        {"id": 912, "user_id": "account-a", "project_id": 902},
        {"id": 913, "user_id": "account-a", "project_id": 902},
        {"id": 914, "user_id": "account-b", "project_id": 903},
    ]
    assert current_revision == UMS_01B_REVISION

    _downgrade_to(config, UMS_01A_REVISION)
    with engine.connect() as connection:
        owners_and_descriptions = (
            connection.execute(
                sa.text(
                    "SELECT user_id, description FROM projects "
                    "WHERE id IN (901, 902) ORDER BY id"
                )
            )
            .mappings()
            .all()
        )
    assert [row["user_id"] for row in owners_and_descriptions] == [
        "account-a",
        "account-a",
    ]
    assert all(
        "__codexify_project_owner__" not in row["description"]
        for row in owners_and_descriptions
    )
    engine.dispose()


@pytest.mark.integration
@pytest.mark.parametrize(
    "case",
    ["zero", "local_only", "mixed", "multiple", "missing_user", "role_conflict"],
)
def test_postgres_unresolved_evidence_fails_without_guessing(
    temporary_postgres,
    case: str,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, UMS_01A_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        if case == "role_conflict":
            connection.execute(
                sa.text(
                    "INSERT INTO projects "
                    "(id, user_id, name, description, system_role) VALUES "
                    "(920, 'account-a', 'Canonical General fixture', "
                    "'canonical', 'general')"
                )
            )
        connection.execute(
            sa.text(
                "INSERT INTO projects "
                "(id, user_id, name, description, system_role) VALUES "
                "(921, 'local', 'Unresolved local fixture', 'unchanged', :role)"
            ),
            {"role": "general" if case == "role_conflict" else None},
        )

        owner_ids = {
            "zero": [],
            "local_only": ["local"],
            "mixed": ["local", "account-a"],
            "multiple": ["account-a", "account-b"],
            "missing_user": ["missing-owner"],
            "role_conflict": ["account-a"],
        }[case]
        if case == "missing_user":
            connection.execute(sa.text("ALTER TABLE chat_threads DISABLE TRIGGER ALL"))
        for offset, owner_id in enumerate(owner_ids):
            connection.execute(
                sa.text(
                    "INSERT INTO chat_threads (id, user_id, project_id, title) "
                    "VALUES (:id, :owner_id, 921, :title)"
                ),
                {
                    "id": 930 + offset,
                    "owner_id": owner_id,
                    "title": f"Evidence {offset}",
                },
            )
        if case == "missing_user":
            connection.execute(sa.text("ALTER TABLE chat_threads ENABLE TRIGGER ALL"))

    with pytest.raises(
        RuntimeError, match="project_ownership_reconciliation_unresolved"
    ):
        _upgrade_to(config, UMS_01B_REVISION)

    with engine.connect() as connection:
        project = (
            connection.execute(
                sa.text(
                    "SELECT id, user_id, name, description, system_role "
                    "FROM projects WHERE id = 921"
                )
            )
            .mappings()
            .one()
        )
        current_revision = connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one()
        missing_user_count = connection.execute(
            sa.text("SELECT count(*) FROM users WHERE id = 'missing-owner'")
        ).scalar_one()

    assert dict(project) == {
        "id": 921,
        "user_id": "local",
        "name": "Unresolved local fixture",
        "description": "unchanged",
        "system_role": "general" if case == "role_conflict" else None,
    }
    assert current_revision == UMS_01A_REVISION
    assert missing_user_count == 0
    engine.dispose()


@pytest.mark.integration
def test_postgres_mixed_reconcilable_and_unresolved_is_atomic(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, UMS_01A_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, user_id, name, description) VALUES "
                "(941, 'local', 'Atomic reconcilable', 'one'), "
                "(942, 'local', 'Atomic unresolved', 'two')"
            )
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_threads (id, user_id, project_id, title) "
                "VALUES (951, 'account-a', 941, 'Reconcilable evidence')"
            )
        )

    with pytest.raises(
        RuntimeError, match="project_ownership_reconciliation_unresolved"
    ):
        _upgrade_to(config, UMS_01B_REVISION)

    with engine.connect() as connection:
        owners = (
            connection.execute(
                sa.text(
                    "SELECT user_id FROM projects WHERE id IN (941, 942) ORDER BY id"
                )
            )
            .scalars()
            .all()
        )
        current_revision = connection.execute(
            sa.text("SELECT version_num FROM alembic_version")
        ).scalar_one()

    assert owners == ["local", "local"]
    assert current_revision == UMS_01A_REVISION
    engine.dispose()


@pytest.mark.integration
def test_postgres_surviving_envelope_fails_ums_01a_precondition(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, UMS_01A_REVISION)
    envelope = _envelope("local", "must remain wrapped on failure")
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, user_id, name, description) "
                "VALUES (961, 'local', 'Precondition fixture', :description)"
            ),
            {"description": envelope},
        )
        connection.execute(
            sa.text(
                "INSERT INTO chat_threads (id, user_id, project_id, title) "
                "VALUES (962, 'account-a', 961, 'Otherwise sufficient evidence')"
            )
        )

    with pytest.raises(
        RuntimeError,
        match="project_ownership_reconciliation_precondition_failed",
    ):
        _upgrade_to(config, UMS_01B_REVISION)

    with engine.connect() as connection:
        project = (
            connection.execute(
                sa.text("SELECT user_id, description FROM projects WHERE id = 961")
            )
            .mappings()
            .one()
        )
    assert dict(project) == {"user_id": "local", "description": envelope}
    engine.dispose()


@pytest.mark.integration
def test_postgres_no_local_projects_is_no_op_and_downgrade_preserves_owner(
    temporary_postgres,
) -> None:
    config, database_url = temporary_postgres
    engine = sa.create_engine(database_url, future=True)

    _upgrade_to(config, UMS_01A_REVISION)
    with engine.begin() as connection:
        _seed_users(connection)
        connection.execute(
            sa.text(
                "INSERT INTO projects (id, user_id, name, description) "
                "VALUES (971, 'account-a', 'Canonical no-op', 'unchanged')"
            )
        )

    _upgrade_to(config, UMS_01B_REVISION)
    _downgrade_to(config, UMS_01A_REVISION)

    with engine.connect() as connection:
        project = (
            connection.execute(
                sa.text("SELECT id, user_id, description FROM projects WHERE id = 971")
            )
            .mappings()
            .one()
        )
    assert dict(project) == {
        "id": 971,
        "user_id": "account-a",
        "description": "unchanged",
    }
    engine.dispose()
