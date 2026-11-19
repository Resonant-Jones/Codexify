"""Published histories converge through real upgrades on owned synthetic stores."""

import hashlib
import importlib
import os
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

MAIN = "e723ba9046cd"
PREVIEW = "f3a9c7d2b8e1"
MERGE = "a3f8c2d6e901"
COMMON = "ab71d5ce9604"
OWNER = "profile-merge-synthetic-owner"
WORKSPACE = "11111111-1111-4111-8111-111111111111"


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
    assert len(list(scripts.walk_revisions())) == 145
    merge = scripts.get_revision(MERGE)
    assert merge.down_revision == (MAIN, PREVIEW)
    assert scripts.get_revision("d2e7a9b4c1f6").down_revision == COMMON
    assert scripts.get_revision(PREVIEW).down_revision == "d2e7a9b4c1f6"
    assert scripts.get_revision("c7e4a1b9d602").down_revision == COMMON
    assert scripts.get_revision("c13f0713a901").down_revision == "c7e4a1b9d602"
    assert scripts.get_revision("d8a90bf32107").down_revision == "c13f0713a901"
    assert scripts.get_revision(MAIN).down_revision == "d8a90bf32107"
    for installed, missing in ((MAIN, PREVIEW), (PREVIEW, MAIN)):
        pending = {
            r.revision
            for r in scripts.iterate_revisions(MERGE, installed, implicit_base=True)
        }
        assert installed not in pending and missing in pending and MERGE in pending
    # The new mergepoint performs no data operation in either direction.
    module = importlib.import_module(
        "guardian.db.migrations.versions.a3f8c2d6e901_merge_main_and_account_presentation"
    )
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
    thread = connection.execute(
        threads.insert()
        .values(user_id=OWNER, project_id=project_id, title="Synthetic thread")
        .returning(threads.c.id)
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
    if omit:
        assert omit in {"greeting_name", "accepted_account_id"}
        expression += " - '" + omit + "'"
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


@pytest.mark.parametrize("installed", ["empty", MAIN, PREVIEW])
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
        omit = (
            {"user_profiles": "greeting_name"}
            if installed == MAIN
            else {"chat_completion_attempts": "accepted_account_id"}
        )
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
            if installed == MAIN:
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
            assert custody == (OWNER if installed == MAIN else None)
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
    with engine.connect() as connection:
        after = {
            name: digest(connection, name)
            for name in [
                "user_profiles",
                "user_presentation",
                "chat_completion_attempts",
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
