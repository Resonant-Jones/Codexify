"""Published histories converge through real upgrades on owned synthetic stores."""

import hashlib
import importlib
import os
from contextlib import contextmanager
from io import BytesIO
import json
from pathlib import Path
from uuid import uuid4

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
import pytest
import sqlalchemy as sa
from PIL import Image

LEGACY_MAIN = "e723ba9046cd"
MAIN = "a64c358e2241"
PREVIEW = "f3a9c7d2b8e1"
PROFILE_MERGE = "a3f8c2d6e901"
MERGE = "b7e6c4a29013"
COMMON = "ab71d5ce9604"
OWNER = "profile-merge-synthetic-owner"
WORKSPACE = "11111111-1111-4111-8111-111111111111"
SOURCE = "22222222-2222-4222-8222-222222222222"
GROUP = "g-p-" + "a" * 32
DELETED_GROUP = "g-p-" + "b" * 32


def image(color):
    output = BytesIO()
    Image.new("RGB", (2, 2), color).save(output, format="PNG")
    return output.getvalue()


WALLPAPER = image("red")
WORKSPACE_WALLPAPER = image("blue")


def config():
    value = Config("backend/alembic.ini")
    value.set_main_option("script_location", "guardian/db/migrations")
    return value


def test_explicit_merge_preserves_both_lineages_without_ddl():
    scripts = ScriptDirectory.from_config(config())
    assert scripts.get_heads() == [MERGE]
    assert len(list(scripts.walk_revisions())) == 147
    merge = scripts.get_revision(MERGE)
    assert merge.down_revision == (PROFILE_MERGE, MAIN)
    assert scripts.get_revision(PROFILE_MERGE).down_revision == (LEGACY_MAIN, PREVIEW)
    assert scripts.get_revision(MAIN).down_revision == LEGACY_MAIN
    assert scripts.get_revision("d2e7a9b4c1f6").down_revision == COMMON
    assert scripts.get_revision(PREVIEW).down_revision == "d2e7a9b4c1f6"
    assert scripts.get_revision("c7e4a1b9d602").down_revision == COMMON
    assert scripts.get_revision("c13f0713a901").down_revision == "c7e4a1b9d602"
    assert scripts.get_revision("d8a90bf32107").down_revision == "c13f0713a901"
    assert scripts.get_revision(LEGACY_MAIN).down_revision == "d8a90bf32107"
    for installed, missing in ((MAIN, PREVIEW), (PREVIEW, MAIN), (PROFILE_MERGE, MAIN)):
        pending = {
            r.revision
            for r in scripts.iterate_revisions(MERGE, installed, implicit_base=True)
        }
        assert installed not in pending and missing in pending and MERGE in pending
    # The new mergepoint performs no data operation in either direction.
    for name in (
        "a3f8c2d6e901_merge_main_and_account_presentation",
        "b7e6c4a29013_merge_profile_and_openai_import_sources",
    ):
        module = importlib.import_module("guardian.db.migrations.versions." + name)
        module.upgrade()
        module.downgrade()


@pytest.fixture
def database(request):
    supplied = os.environ.get("CODEXIFY_PROFILE_MERGE_TEST_DATABASE_URL")
    if not supplied:
        pytest.skip("Explicitly owned Unix-only PostgreSQL cluster required")
    root_url = sa.engine.make_url(supplied)
    socket = Path(root_url.query.get("host", "")).resolve()
    assert str(socket).startswith(
        ("/tmp/cxf-profile-merge.", "/private/tmp/cxf-profile-merge.")
    )
    assert socket.name == "socket"
    assert (
        root_url.username == "codexify_profile_merge_test"
        and root_url.database == "postgres"
    )
    root = sa.create_engine(root_url, isolation_level="AUTOCOMMIT")
    name = "profile_merge_" + uuid4().hex
    with root.connect() as connection:
        connection.exec_driver_sql(f'CREATE DATABASE "{name}"')
    url = root_url.set(database=name)
    engine = sa.create_engine(url)
    try:
        yield url, engine
    finally:
        engine.dispose()
        with root.connect() as connection:
            connection.exec_driver_sql(f'DROP DATABASE "{name}" WITH (FORCE)')
        root.dispose()


def upgrade(monkeypatch, url, revision):
    # libpq's Unix socket comes from PGHOST, avoiding ConfigParser's percent
    # interpolation of a URL-encoded socket path. Production env.py is unchanged.
    monkeypatch.setenv("PGHOST", url.query["host"])
    monkeypatch.setenv("PGPORT", str(url.query.get("port", "5432")))
    monkeypatch.setenv(
        "DATABASE_URL", url.set(query={}).render_as_string(hide_password=False)
    )
    command.upgrade(config(), revision)


def table(connection, name):
    return sa.Table(name, sa.MetaData(), autoload_with=connection)


def seed(connection, *, presentation):
    users = table(connection, "users")
    connection.execute(
        users.insert(),
        {
            "id": OWNER,
            "username": "synthetic-identifier",
            "password_hash": "synthetic-not-a-password",
            "role": "guest",
        },
    )
    nodes = table(connection, "threadspace_nodes")
    connection.execute(
        nodes.insert(),
        {"node_id": "synthetic-node", "name": "Synthetic node", "status": "active"},
    )
    profiles = table(connection, "user_profiles")
    value = {
        "user_id": OWNER,
        "display_name": "Preserved display label",
        "profile_id": str(uuid4()),
        "node_id": "synthetic-node",
        "accent_color": "blue",
    }
    if presentation:
        value["greeting_name"] = "Chosen greeting"
    connection.execute(profiles.insert(), value)
    projects = table(connection, "projects")
    project_id = connection.execute(
        projects.insert()
        .values(user_id=OWNER, name="Synthetic project")
        .returning(projects.c.id)
    ).scalar_one()
    threads = table(connection, "chat_threads")
    thread_values = dict(user_id=OWNER, project_id=project_id, title="Synthetic thread")
    if "openai_import_source_id" in threads.c:
        connection.execute(
            table(connection, "openai_import_sources").insert(),
            {"id": SOURCE, "user_id": OWNER, "label": "Synthetic chosen source"},
        )
        connection.execute(
            table(connection, "openai_import_project_groups").insert(),
            [
                dict(
                    user_id=OWNER,
                    source_id=SOURCE,
                    group_id=GROUP,
                    project_id=project_id,
                ),
                dict(
                    user_id=OWNER,
                    source_id=SOURCE,
                    group_id=DELETED_GROUP,
                    project_id=None,
                ),
            ],
        )
        thread_values.update(origin_system="openai", openai_import_source_id=SOURCE)
    thread = connection.execute(
        threads.insert().values(**thread_values).returning(threads.c.id)
    ).scalar_one()
    attempts = table(connection, "chat_completion_attempts")
    attempt = {
        "request_id": "synthetic-request",
        "backend_task_id": "synthetic-task",
        "thread_id": thread,
        "turn_id": "synthetic-turn",
    }
    if "accepted_account_id" in attempts.c:
        attempt["accepted_account_id"] = OWNER
    connection.execute(attempts.insert(), attempt)
    if presentation:
        preferences = table(connection, "user_presentation")
        connection.execute(
            preferences.insert(),
            [
                {
                    "user_id": OWNER,
                    "workspace_id": "account",
                    "is_unique": False,
                    "settings": {"theme_mode": "dark", "base_color": "#123456"},
                    "wallpaper_data": WALLPAPER,
                    "wallpaper_mime": "image/png",
                },
                {
                    "user_id": OWNER,
                    "workspace_id": WORKSPACE,
                    "is_unique": True,
                    "settings": {"theme_mode": "light"},
                    "wallpaper_data": WORKSPACE_WALLPAPER,
                    "wallpaper_mime": "image/png",
                },
            ],
        )
    else:
        credentials = table(connection, "github_knowledge_credentials")
        connection.execute(
            credentials.insert(),
            {
                "user_id": OWNER,
                "encrypted_token": "synthetic-opaque-ciphertext",
                "repositories": ["synthetic/repo"],
            },
        )


def digest(connection, name, omit=None):
    # Synthetic rows only. Keep raw values out of the test receipt.
    expression = "to_jsonb(t)"
    for column in omit or ():
        assert column in {
            "greeting_name",
            "accepted_account_id",
            "openai_import_source_id",
        }
        expression += " - '" + column + "'"
    rows = (
        connection.execute(
            sa.text(
                f"SELECT ({expression})::text FROM {name} t ORDER BY ({expression})::text"
            )
        )
        .scalars()
        .all()
    )
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()


def assert_group_routing_survives(url, engine):
    """Exercise #1097's real resolver on migrated, synthetic account state."""
    import psycopg
    from psycopg.rows import dict_row

    from guardian.core.openai_import_routing import (
        OpenAIImportPlacementConflict,
        classify_openai_group,
        lock_openai_import_owner,
        resolve_openai_fresh_project,
    )

    other = OWNER + "-other"
    source_b = "33333333-3333-4333-8333-333333333333"
    source_other = "44444444-4444-4444-8444-444444444444"
    with engine.begin() as connection:
        connection.execute(
            table(connection, "users").insert(),
            dict(
                id=other, username="synthetic-other", password_hash="test", role="guest"
            ),
        )
        connection.execute(
            sa.text(
                "INSERT INTO openai_import_sources (id,user_id,label) "
                "VALUES (:source,:owner,'Explicit source') ON CONFLICT DO NOTHING"
            ),
            [
                dict(source=SOURCE, owner=OWNER),
                dict(source=source_b, owner=OWNER),
                dict(source=source_other, owner=other),
            ],
        )
        unbound = connection.execute(
            sa.text(
                "INSERT INTO projects (user_id,name) VALUES (:owner,:name) RETURNING id"
            ),
            dict(owner=OWNER, name="OpenAI Project aaaaaaaa"),
        ).scalar_one()
        general = connection.execute(
            sa.text(
                "INSERT INTO projects (user_id,name,system_role) "
                "VALUES (:owner,'Renamed default','general') RETURNING id"
            ),
            dict(owner=OWNER),
        ).scalar_one()
        connection.execute(
            sa.text(
                "INSERT INTO openai_import_project_groups (user_id,source_id,group_id) "
                "VALUES (:owner,:source,:group) ON CONFLICT DO NOTHING"
            ),
            dict(owner=OWNER, source=SOURCE, group=DELETED_GROUP),
        )
        prior_project = connection.scalar(
            sa.text(
                "SELECT project_id FROM openai_import_project_groups "
                "WHERE user_id=:owner AND source_id=:source AND group_id=:group"
            ),
            dict(owner=OWNER, source=SOURCE, group=GROUP),
        )

    with psycopg.connect(
        url.set(drivername="postgresql").render_as_string(hide_password=False),
        row_factory=dict_row,
    ) as connection:

        class TransactionDB:
            @contextmanager
            def _connect(self):
                yield connection

        db = TransactionDB()

        def resolve(owner, source, group):
            lock_openai_import_owner(db, owner, source)
            return resolve_openai_fresh_project(
                db, user_id=owner, source_id=source, group_id=group
            )

        assert (
            classify_openai_group(
                dict(id="synthetic-record", conversation_template_id=GROUP)
            )
            == GROUP
        )
        first, created = resolve(OWNER, SOURCE, GROUP)
        assert first != unbound
        assert created == (prior_project is None)
        if prior_project is not None:
            assert first == prior_project
        assert resolve(OWNER, SOURCE, GROUP) == (first, False)
        second, second_created = resolve(OWNER, source_b, GROUP)
        third, third_created = resolve(other, source_other, GROUP)
        assert len({first, second, third}) == 3 and second_created and third_created
        assert resolve(OWNER, SOURCE, None) == (general, False)
        with pytest.raises(
            OpenAIImportPlacementConflict, match="source is unavailable"
        ):
            resolve(other, SOURCE, GROUP)
        with pytest.raises(OpenAIImportPlacementConflict, match="archived or deleted"):
            resolve(OWNER, SOURCE, DELETED_GROUP)
        # A source binding is immutable, including NULL -> selected source.
        thread = connection.execute(
            "INSERT INTO chat_threads (user_id,project_id,title,origin_system,openai_import_source_id) "
            "VALUES (%s,%s,'Synthetic bound thread','openai',%s) RETURNING id",
            (OWNER, first, SOURCE),
        ).fetchone()["id"]
        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.transaction():
                connection.execute(
                    "UPDATE chat_threads SET openai_import_source_id=%s WHERE id=%s",
                    (source_b, thread),
                )
        with pytest.raises(psycopg.errors.CheckViolation):
            with connection.transaction():
                connection.execute(
                    "UPDATE openai_import_project_groups SET project_id=%s "
                    "WHERE user_id=%s AND source_id=%s AND group_id=%s",
                    (unbound, OWNER, SOURCE, GROUP),
                )
        with pytest.raises(psycopg.errors.ForeignKeyViolation):
            with connection.transaction():
                connection.execute(
                    "INSERT INTO openai_import_project_groups (user_id,source_id,group_id,project_id) "
                    "VALUES (%s,%s,%s,%s)",
                    (other, source_other, "g-p-" + "c" * 32, unbound),
                )
        connection.execute(
            "UPDATE projects SET archived_at=now() WHERE id=%s", (second,)
        )
        with pytest.raises(OpenAIImportPlacementConflict, match="archived or deleted"):
            resolve(OWNER, source_b, GROUP)


@pytest.mark.parametrize("installed", ["empty", LEGACY_MAIN, MAIN, PREVIEW])
def test_real_upgrade_paths_preserve_authored_data_and_custody(
    database, monkeypatch, installed
):
    url, engine = database
    if installed != "empty":
        upgrade(monkeypatch, url, installed)
        with engine.begin() as connection:
            seed(connection, presentation=installed == PREVIEW)
        protected = ["users", "user_profiles", "projects", "chat_threads"]
        protected += ["chat_completion_attempts"]
        protected += (
            ["user_presentation"]
            if installed == PREVIEW
            else ["github_knowledge_credentials"]
        )
        omit = {}
        if installed != PREVIEW:
            omit["user_profiles"] = ("greeting_name",)
        else:
            omit["chat_completion_attempts"] = ("accepted_account_id",)
        if installed != MAIN:
            omit["chat_threads"] = ("openai_import_source_id",)
        else:
            protected += ["openai_import_sources", "openai_import_project_groups"]
        with engine.connect() as connection:
            before = {
                name: digest(connection, name, omit.get(name)) for name in protected
            }
    upgrade(monkeypatch, url, "head")
    with engine.connect() as connection:
        assert (
            connection.scalar(sa.text("SELECT version_num FROM alembic_version"))
            == MERGE
        )
        assert (
            len(
                connection.execute(
                    sa.text("SELECT version_num FROM alembic_version")
                ).all()
            )
            == 1
        )
        if installed == "empty":
            assert (
                connection.scalar(sa.text("SELECT count(*) FROM user_presentation"))
                == 0
            )
            assert (
                connection.scalar(
                    sa.text(
                        "SELECT count(*) FROM user_profiles WHERE greeting_name IS NOT NULL"
                    )
                )
                == 0
            )
        else:
            # A new NULL column changes a row's JSON shape; compare old profile
            # values separately when upgrading main, without inferring a name.
            if installed != PREVIEW:
                assert (
                    connection.scalar(
                        sa.text(
                            "SELECT greeting_name FROM user_profiles WHERE user_id=:owner"
                        ),
                        {"owner": OWNER},
                    )
                    is None
                )
                assert (
                    connection.scalar(
                        sa.text(
                            "SELECT display_name FROM user_profiles WHERE user_id=:owner"
                        ),
                        {"owner": OWNER},
                    )
                    == "Preserved display label"
                )
            assert {
                name: digest(connection, name, omit.get(name)) for name in protected
            } == before
            custody = connection.scalar(
                sa.text(
                    "SELECT accepted_account_id FROM chat_completion_attempts WHERE request_id='synthetic-request'"
                )
            )
            assert custody == (None if installed == PREVIEW else OWNER)
    if installed != "empty":
        # Existing main custody stays immutable. Preview legacy NULL is never
        # promoted into authenticated history by this schema join.
        with pytest.raises(sa.exc.IntegrityError):
            with engine.begin() as connection:
                connection.execute(
                    sa.text(
                        "UPDATE chat_completion_attempts SET accepted_account_id='different-account' WHERE request_id='synthetic-request'"
                    )
                )
    if installed != "empty":
        assert_group_routing_survives(url, engine)
    with engine.connect() as connection:
        after = {
            name: digest(connection, name)
            for name in [
                "user_profiles",
                "user_presentation",
                "chat_completion_attempts",
                "openai_import_sources",
                "openai_import_project_groups",
                "chat_threads",
                "projects",
            ]
        }
    upgrade(monkeypatch, url, "head")
    with engine.connect() as connection:
        assert {name: digest(connection, name) for name in after} == after


def test_published_branch_bytes_are_unchanged():
    expected = json.loads(
        Path("tests/migration/profile_main_published_branch_sha256.json").read_text()
    )
    for filename, digest_value in expected.items():
        assert (
            hashlib.sha256(
                (Path("guardian/db/migrations/versions") / filename).read_bytes()
            ).hexdigest()
            == digest_value
        )
