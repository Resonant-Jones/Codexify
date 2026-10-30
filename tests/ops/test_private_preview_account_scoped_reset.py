"""Regression tests for the live Private Preview account-scoped reset.

The reset removes synthetic qualification accounts from the live Preview. The
danger is scope: a direct-message relationship is a two-party construct, so
deleting one participant's half of it silently destroys the other
participant's messages and read cursor. These tests exercise the real
operator script against a disposable Postgres with the real migrated schema.

Covered:
  * a relationship that joins a named account to an unnamed account is
    REFUSED, and the shared relationship, its conversation, its messages, and
    the unnamed participant's read cursor all survive;
  * a request that joins a named account to an unnamed account is REFUSED;
  * state that belongs only to the named account IS removed, and unrelated
    accounts' rows are left untouched;
  * a crafted account identifier is bound as a literal and cannot widen the
    selected scope.
"""

from __future__ import annotations

import os
import socket
import subprocess
import time
import uuid
from collections.abc import Generator
from pathlib import Path

import psycopg
import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine, make_url


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "ops" / "private_preview_account_scoped_reset.sh"

TARGET_USER = "target-user"
OTHER_USER = "other-user"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def postgres_server() -> Generator[str, None, None]:
    configured_url = os.getenv("TEST_DATABASE_URL")
    if configured_url:
        yield configured_url
        return

    port = _free_port()
    container_name = f"codexify_scoped_reset_{uuid.uuid4().hex[:12]}"
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "--detach",
                "--rm",
                "--name",
                container_name,
                "--env",
                "POSTGRES_USER=postgres",
                "--env",
                "POSTGRES_PASSWORD=postgres",
                "--env",
                "POSTGRES_DB=postgres",
                "--publish",
                f"127.0.0.1:{port}:5432",
                "postgres:15",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
        subprocess.TimeoutExpired,
    ) as exc:
        pytest.fail(f"unable to start disposable Postgres: {exc}")

    base_url = f"postgresql://postgres:postgres@127.0.0.1:{port}/postgres"
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        try:
            with psycopg.connect(base_url):
                break
        except psycopg.Error:
            time.sleep(0.5)
    else:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            timeout=30,
        )
        pytest.fail("disposable Postgres did not become ready")

    try:
        yield base_url
    finally:
        subprocess.run(
            ["docker", "rm", "--force", container_name],
            capture_output=True,
            timeout=30,
        )


@pytest.fixture
def reset_database(
    postgres_server: str,
    monkeypatch: pytest.MonkeyPatch,
) -> Generator[tuple[str, str, Engine], None, None]:
    """A disposable database with the real migrated schema."""
    database_name = f"codexify_scoped_reset_{uuid.uuid4().hex[:12]}"
    admin_url = make_url(postgres_server).set(database="postgres").render_as_string(
        hide_password=False
    )
    sqlalchemy_url = make_url(postgres_server).set(
        drivername="postgresql+psycopg", database=database_name
    ).render_as_string(hide_password=False)

    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)

    with psycopg.connect(admin_url, autocommit=True) as connection:
        connection.execute(f'CREATE DATABASE "{database_name}"')

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", sqlalchemy_url)
    config.set_main_option(
        "script_location", str(REPO_ROOT / "guardian" / "db" / "migrations")
    )
    monkeypatch.setenv("DATABASE_URL", sqlalchemy_url)

    engine: Engine | None = None
    try:
        command.upgrade(config, "head")
        engine = create_engine(sqlalchemy_url, future=True)
        container_name = postgres_server_container()
        yield container_name, database_name, engine
    finally:
        if engine is not None:
            engine.dispose()
        with psycopg.connect(admin_url, autocommit=True) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s AND pid <> pg_backend_pid()",
                (database_name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{database_name}"')


def postgres_server_container() -> str:
    """The running disposable container name."""
    result = subprocess.run(
        ["docker", "ps", "--filter", "ancestor=postgres:15", "--format", "{{.Names}}"],
        check=True,
        capture_output=True,
        text=True,
    )
    names = [n for n in result.stdout.split() if n.startswith("codexify_scoped_reset_")]
    assert names, "disposable Postgres container not found"
    return names[0]


def run_reset(
    container_name: str,
    database_name: str,
    identifier: str,
    *,
    confirm: bool,
    by: str = "username",
) -> subprocess.CompletedProcess[str]:
    args = ["bash", str(SCRIPT), f"--{by}", identifier]
    if confirm:
        args.append("--confirm")
    env = {
        **os.environ,
        "CODEXIFY_PREVIEW_DB_CONTAINER": container_name,
        "CODEXIFY_PREVIEW_DB_USER": "postgres",
        "CODEXIFY_PREVIEW_DB_NAME": database_name,
    }
    return subprocess.run(args, capture_output=True, text=True, env=env, timeout=180)


def seed_accounts(
    engine: Engine,
    usernames: list[str],
    *,
    emails: dict[str, str] | None = None,
) -> None:
    emails = emails or {}
    with engine.begin() as connection:
        for name in usernames:
            node_id = f"node-{name}"
            profile_id = f"profile-{name}"
            email = emails.get(name, f"{name}@example.invalid")
            connection.execute(
                text(
                    "INSERT INTO threadspace_nodes (node_id, name) "
                    "VALUES (:node_id, :name)"
                ),
                {"node_id": node_id, "name": f"Node {name}"},
            )
            connection.execute(
                text(
                    "INSERT INTO users (id, username, password_hash, role, email) "
                    "VALUES (:id, :username, '!not-a-real-hash', 'guest', :email)"
                ),
                {"id": email, "username": name, "email": email},
            )
            connection.execute(
                text(
                    "INSERT INTO user_profiles "
                    "(user_id, profile_id, node_id, username, accent_color, "
                    " username_state) "
                    "VALUES (:user_id, :profile_id, :node_id, :username, "
                    "        'default', 'active')"
                ),
                {"user_id": email, "profile_id": profile_id,
                 "node_id": node_id, "username": name},
            )


def participant_pair_key(participants: list[str]) -> str:
    """The canonical pair key: sorted ``node:profile`` pairs joined by ``:``."""
    pairs = sorted(f"node-{name}:profile-{name}" for name in participants)
    return ":".join(pairs)


def seed_relationship(
    engine: Engine,
    relationship_id: str,
    participants: list[str],
    *,
    with_request: bool = False,
) -> tuple[str, str]:
    """Create a relationship, one conversation, one message, one cursor.

    Returns the conversation id and the message id.
    """
    conversation_id = f"conv-{relationship_id}"
    message_id = f"msg-{relationship_id}"
    with engine.begin() as connection:
        connection.execute(
            text(
                "INSERT INTO direct_message_relationships (id, participant_pair_key) "
                "VALUES (:id, :pair_key)"
            ),
            {"id": relationship_id, "pair_key": participant_pair_key(participants)},
        )
        for name in participants:
            connection.execute(
                text(
                    "INSERT INTO direct_message_relationship_participants "
                    "(id, relationship_id, node_id, profile_id) "
                    "VALUES (:id, :relationship_id, :node_id, :profile_id)"
                ),
                {
                    "id": f"part-{relationship_id}-{name}",
                    "relationship_id": relationship_id,
                    "node_id": f"node-{name}",
                    "profile_id": f"profile-{name}",
                },
            )
        connection.execute(
            text(
                "INSERT INTO direct_message_conversations "
                "(id, relationship_id, created_by_profile_id) "
                "VALUES (:id, :relationship_id, :created_by)"
            ),
            {
                "id": conversation_id,
                "relationship_id": relationship_id,
                "created_by": f"profile-{participants[0]}",
            },
        )
        connection.execute(
            text(
                "INSERT INTO direct_messages "
                "(id, conversation_id, sender_node_id, sender_profile_id, "
                " content_type, body) "
                "VALUES (:id, :conversation_id, :sender_node, :sender_profile, "
                "        'text/plain', 'hello')"
            ),
            {
                "id": message_id,
                "conversation_id": conversation_id,
                "sender_node": f"node-{participants[0]}",
                "sender_profile": f"profile-{participants[0]}",
            },
        )
        # The recipient's durable read position in this conversation.
        connection.execute(
            text(
                "INSERT INTO direct_message_read_cursors "
                "(conversation_id, profile_id, last_read_message_id) "
                "VALUES (:conversation_id, :profile_id, :message_id)"
            ),
            {
                "conversation_id": conversation_id,
                "profile_id": f"profile-{participants[-1]}",
                "message_id": message_id,
            },
        )
        if with_request:
            # A pending request carries no materialized conversation; the
            # ck_message_requests_materialization constraint requires that.
            connection.execute(
                text(
                    "INSERT INTO message_requests "
                    "(id, relationship_id, sender_profile_id, "
                    " recipient_profile_id, note, state, created_at, expires_at) "
                    "VALUES (:id, :relationship_id, :sender, :recipient, "
                    "        'note', 'pending', now(), now() + interval '30 days')"
                ),
                {
                    "id": f"req-{relationship_id}",
                    "relationship_id": relationship_id,
                    "sender": f"profile-{participants[0]}",
                    "recipient": f"profile-{participants[-1]}",
                },
            )
    return conversation_id, message_id


def count(engine: Engine, sql: str) -> int:
    with engine.connect() as connection:
        return int(connection.execute(text(sql)).scalar_one())


def snapshot(engine: Engine) -> dict[str, int]:
    """Row counts per affected table.

    Assertions are written as deltas rather than absolute values, because a
    freshly migrated database may carry seeded rows that the reset must not
    touch.
    """
    return {
        "relationships": count(engine, "select count(*) from direct_message_relationships"),
        "conversations": count(engine, "select count(*) from direct_message_conversations"),
        "messages": count(engine, "select count(*) from direct_messages"),
        "cursors": count(engine, "select count(*) from direct_message_read_cursors"),
        "requests": count(engine, "select count(*) from message_requests"),
        "profiles": count(engine, "select count(*) from user_profiles"),
        "users": count(engine, "select count(*) from users"),
    }


def test_shared_relationship_is_refused_and_survives(
    reset_database: tuple[str, str, Engine],
) -> None:
    """A named account sharing a relationship with an unnamed account is refused."""
    container_name, database_name, engine = reset_database
    seed_accounts(engine, [TARGET_USER, OTHER_USER])
    seed_relationship(
        engine, "rel-mixed", [TARGET_USER, OTHER_USER], with_request=True
    )
    before = snapshot(engine)

    result = run_reset(
        container_name, database_name, TARGET_USER, confirm=True
    )

    assert result.returncode != 0, result.stdout + result.stderr
    assert "REFUSED" in (result.stdout + result.stderr)

    # The shared relationship, its conversation, its message, and the other
    # participant's read cursor must all still be present. Nothing at all was
    # removed: the refusal happens before any destructive statement.
    after = snapshot(engine)
    assert after == before
    assert (
        count(
            engine,
            "select count(*) from direct_message_relationships where id = 'rel-mixed'",
        )
        == 1
    )
    assert (
        count(
            engine,
            "select count(*) from direct_message_read_cursors "
            "where profile_id = 'profile-other-user'",
        )
        == 1
    )
    # Neither account was removed.
    assert (
        count(engine, "select count(*) from user_profiles where username = 'target-user'")
        == 1
    )
    assert (
        count(engine, "select count(*) from user_profiles where username = 'other-user'")
        == 1
    )


def test_dry_run_reports_shared_state_without_changing_anything(
    reset_database: tuple[str, str, Engine],
) -> None:
    """A dry run reports the shared state instead of refusing, and changes nothing."""
    container_name, database_name, engine = reset_database
    seed_accounts(engine, [TARGET_USER, OTHER_USER])
    seed_relationship(
        engine, "rel-mixed", [TARGET_USER, OTHER_USER], with_request=True
    )
    before = snapshot(engine)

    result = run_reset(container_name, database_name, TARGET_USER, confirm=False)

    assert result.returncode == 0, result.stdout + result.stderr
    assert "SHARED STATE DETECTED" in (result.stdout + result.stderr)
    assert OTHER_USER in (result.stdout + result.stderr)
    assert snapshot(engine) == before


def test_request_counterparty_is_refused(
    reset_database: tuple[str, str, Engine],
) -> None:
    """A message request that names an unnamed counterpart is refused."""
    container_name, database_name, engine = reset_database
    seed_accounts(engine, [TARGET_USER, OTHER_USER])
    seed_relationship(engine, "rel-shared", [TARGET_USER, OTHER_USER], with_request=True)

    result = run_reset(container_name, database_name, TARGET_USER, confirm=True)

    assert result.returncode != 0, result.stdout + result.stderr
    assert "REFUSED" in (result.stdout + result.stderr)
    assert count(engine, "select count(*) from message_requests") == 1
    assert count(engine, "select count(*) from direct_messages") == 1


def test_sole_owned_state_is_removed_and_others_survive(
    reset_database: tuple[str, str, Engine],
) -> None:
    """State owned only by the named account is removed; other rows survive."""
    container_name, database_name, engine = reset_database
    seed_accounts(engine, [TARGET_USER, OTHER_USER])
    seed_relationship(engine, "rel-target-only", [TARGET_USER])
    seed_relationship(engine, "rel-other-only", [OTHER_USER])
    before = snapshot(engine)

    result = run_reset(container_name, database_name, TARGET_USER, confirm=True)

    assert result.returncode == 0, result.stdout + result.stderr
    after = snapshot(engine)

    # The named account's state is gone; everything else is untouched.
    assert after["relationships"] == before["relationships"] - 1
    assert after["conversations"] == before["conversations"] - 1
    assert after["messages"] == before["messages"] - 1
    assert after["cursors"] == before["cursors"] - 1
    assert after["profiles"] == before["profiles"] - 1
    assert after["users"] == before["users"] - 1
    assert (
        count(
            engine,
            "select count(*) from direct_message_read_cursors "
            "where profile_id = 'profile-target-user'",
        )
        == 0
    )

    # The other account's relationship, conversation, message, and cursor remain.
    assert (
        count(
            engine,
            "select count(*) from direct_message_relationships where id = 'rel-other-only'",
        )
        == 1
    )
    assert (
        count(
            engine,
            "select count(*) from direct_messages where conversation_id = 'conv-rel-other-only'",
        )
        == 1
    )
    assert (
        count(
            engine,
            "select count(*) from direct_message_read_cursors "
            "where profile_id = 'profile-other-user'",
        )
        == 1
    )


def test_crafted_identifier_cannot_widen_the_scope(
    reset_database: tuple[str, str, Engine],
) -> None:
    """A crafted identifier is bound as a literal and matches only itself.

    The username grammar is constrained by the database, so the crafted value
    is carried on the email path, which is the identifier the operator would
    most likely paste.
    """
    container_name, database_name, engine = reset_database
    crafted_email = "evil' OR '1'='1@example.invalid"
    seed_accounts(
        engine,
        ["crafted-user", OTHER_USER],
        emails={"crafted-user": crafted_email},
    )
    seed_relationship(engine, "rel-crafted", ["crafted-user"])
    seed_relationship(engine, "rel-other", [OTHER_USER])

    result = run_reset(
        container_name, database_name, crafted_email, confirm=True, by="email"
    )

    assert result.returncode == 0, result.stdout + result.stderr

    # Only the crafted account's own state was touched.
    assert (
        count(
            engine,
            "select count(*) from direct_message_relationships where id = 'rel-other'",
        )
        == 1
    )
    assert (
        count(
            engine,
            "select count(*) from direct_messages where conversation_id = 'conv-rel-other'",
        )
        == 1
    )
    assert count(engine, "select count(*) from users where username = 'other-user'") == 1


def test_unscoped_invocation_is_refused(
    reset_database: tuple[str, str, Engine],
) -> None:
    """The script refuses to run without explicit account identifiers."""
    container_name, database_name, _engine = reset_database
    env = {
        **os.environ,
        "CODEXIFY_PREVIEW_DB_CONTAINER": container_name,
        "CODEXIFY_PREVIEW_DB_USER": "postgres",
        "CODEXIFY_PREVIEW_DB_NAME": database_name,
    }
    result = subprocess.run(
        ["bash", str(SCRIPT), "--confirm"],
        capture_output=True,
        text=True,
        env=env,
        timeout=120,
    )
    assert result.returncode != 0
    assert "refuses to run unscoped" in (result.stdout + result.stderr)
