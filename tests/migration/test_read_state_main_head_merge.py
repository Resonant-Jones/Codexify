"""Migration proof for the read-cursor / unified-main-head merge.

The mainline carried the Saved Widget and consent branches unified behind
``7f2c9e1a4b63``, while the recipient-local read cursor arrived on a separate
branch at ``b3c8d1e5f7a2``.  This module proves that the graph-only merge
revision ``3a91d7c4e8b2`` joins them into a single head without changing the
schema, without rewriting either parent, and without disturbing Saved Widget
identities, immutable revision snapshots, account consent values, or
participant-local read cursors.

Every test runs against a uniquely named disposable PostgreSQL database built
from the repository's own Alembic migrations.  No production or Preview data
is used and the database is dropped afterwards.
"""

from __future__ import annotations

import ast
import os
import pathlib
import uuid
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"

MERGE_REVISION = "3a91d7c4e8b2"
UNIFIED_MAIN_REVISION = "7f2c9e1a4b63"
READ_CURSOR_REVISION = "b3c8d1e5f7a2"
CONSENT_REVISION = "c59e4d1a28f0"

WIDGETS_TABLE = "saved_widgets"
REVISIONS_TABLE = "saved_widget_revisions"
CURSOR_TABLE = "direct_message_read_cursors"

ACCOUNT_ID = "read-merge-proof-account"
#: ``uq_user_profiles_user_id`` is unique on ``user_id`` alone, so one account
#: carries exactly one profile. A two-participant direct-message conversation
#: therefore needs two distinct accounts, exactly as the reviewed read-cursor
#: migration test seeds them.
PEER_ACCOUNT_ID = "read-merge-proof-peer"
WIDGET_ID = "widget-read-merge-proof"


@pytest.fixture
def disposable_postgres(monkeypatch) -> Iterator[Any]:
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_read_merge_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)

    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(f"CREATE DATABASE {db_name}")

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option(
        "sqlalchemy.url",
        test_url.render_as_string(hide_password=False).replace("%", "%%"),
    )
    monkeypatch.setenv("DATABASE_URL", test_url.render_as_string(hide_password=False))
    monkeypatch.setenv(
        "GUARDIAN_DATABASE_URL", test_url.render_as_string(hide_password=False)
    )

    engine = sa.create_engine(test_url)
    try:
        yield config, engine
        engine.dispose()
    finally:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f"DROP DATABASE IF EXISTS {db_name}")


def _script_directory() -> ScriptDirectory:
    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    config.set_main_option("script_location", str(REPO_ROOT / "guardian/db/migrations"))
    return ScriptDirectory.from_config(config)


def _current_heads(engine: sa.Engine) -> set[str]:
    with engine.connect() as connection:
        return set(MigrationContext.configure(connection).get_current_heads())


def _seed_account(connection) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) VALUES "
            "(:uid, 'read-merge-user', 'not-a-real-hash', 'guest')"
        ),
        {"uid": ACCOUNT_ID},
    )
    connection.execute(
        sa.text(
            "INSERT INTO user_settings (user_id, memory_mode) VALUES (:uid, 'light')"
        ),
        {"uid": ACCOUNT_ID},
    )


def _seed_widget(connection) -> None:
    connection.execute(
        sa.text(
            "INSERT INTO saved_widgets "
            "(widget_id, owner_user_id, name, current_revision) "
            "VALUES (:widget_id, :uid, 'Read Merge Widget', 1)"
        ),
        {"widget_id": WIDGET_ID, "uid": ACCOUNT_ID},
    )
    connection.execute(
        sa.text(
            "INSERT INTO saved_widget_revisions "
            "(widget_id, revision, artifact_snapshot, provenance_snapshot, "
            "creation_context) VALUES "
            "(:widget_id, 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb)"
        ),
        {"widget_id": WIDGET_ID},
    )


def _seed_messaging_and_cursor(connection) -> tuple[str, str]:
    """Seed a conversation with one message and one participant-local cursor."""
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) VALUES "
            "(:uid, 'read-merge-peer-user', 'not-a-real-hash', 'guest')"
        ),
        {"uid": PEER_ACCOUNT_ID},
    )
    connection.execute(
        sa.text(
            "INSERT INTO threadspace_nodes (node_id, name, status) "
            "VALUES ('node-local', 'Local Node', 'active')"
        )
    )
    profile_a = uuid.uuid4().hex
    profile_b = uuid.uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO user_profiles "
            "(user_id, profile_id, node_id, username, username_state, "
            "accent_color) VALUES "
            "(:uid, :profile_a, 'node-local', 'reader', 'active', 'default'), "
            "(:peer_uid, :profile_b, 'node-local', 'writer', 'active', 'default')"
        ),
        {
            "uid": ACCOUNT_ID,
            "peer_uid": PEER_ACCOUNT_ID,
            "profile_a": profile_a,
            "profile_b": profile_b,
        },
    )
    pair_key = f"node-local:{profile_a}|node-local:{profile_b}"
    relationship_id = uuid.uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO direct_message_relationships (id, participant_pair_key) "
            "VALUES (:id, :pair_key)"
        ),
        {"id": relationship_id, "pair_key": pair_key},
    )
    for profile_id in (profile_a, profile_b):
        connection.execute(
            sa.text(
                "INSERT INTO direct_message_relationship_participants "
                "(id, relationship_id, node_id, profile_id) "
                "VALUES (:id, :relationship_id, 'node-local', :profile_id)"
            ),
            {
                "id": uuid.uuid4().hex,
                "relationship_id": relationship_id,
                "profile_id": profile_id,
            },
        )
    conversation_id = uuid.uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO direct_message_conversations "
            "(id, kind, relationship_id) VALUES (:id, 'direct', :relationship_id)"
        ),
        {"id": conversation_id, "relationship_id": relationship_id},
    )
    message_id = uuid.uuid4().hex
    connection.execute(
        sa.text(
            "INSERT INTO direct_messages "
            "(id, conversation_id, sender_node_id, sender_profile_id, "
            "content_type, body, client_message_key) "
            "VALUES (:id, :conversation_id, 'node-local', :profile_id, "
            "'text/plain', 'body', 'key')"
        ),
        {
            "id": message_id,
            "conversation_id": conversation_id,
            "profile_id": profile_b,
        },
    )
    connection.execute(
        sa.text(
            "INSERT INTO direct_message_read_cursors "
            "(conversation_id, profile_id, last_read_message_id) "
            "VALUES (:conversation_id, :profile_id, :message_id)"
        ),
        {
            "conversation_id": conversation_id,
            "profile_id": profile_a,
            "message_id": message_id,
        },
    )
    return conversation_id, message_id


def _consent_record(connection):
    return tuple(
        connection.execute(
            sa.text(
                "SELECT automatic_memory_suggestions, consent_policy_version, "
                "consent_recorded_by_user_id, consent_recorded_at, "
                "consent_updated_at FROM user_settings WHERE user_id=:uid"
            ),
            {"uid": ACCOUNT_ID},
        ).one()
    )


def _enable_consent(connection) -> None:
    connection.execute(
        sa.text(
            "UPDATE user_settings SET automatic_memory_suggestions='enabled', "
            "consent_policy_version='2', consent_recorded_by_user_id=:uid, "
            "consent_recorded_at='2026-01-02 03:04:05+00', "
            "consent_updated_at='2026-01-03 04:05:06+00' WHERE user_id=:uid"
        ),
        {"uid": ACCOUNT_ID},
    )


def test_merge_revision_is_in_the_single_head_ancestry_and_parents_both_branches():
    """The read-state merge stays inside the current single head's ancestry.

    ``3a91d7c4e8b2`` is not the permanent head of the migration graph. A later,
    correctly joined branch may add a mergepoint above it. What must remain
    true is that the graph has exactly one head, that this historical merge is
    reachable from that head, and that it still joins its two original parents
    without rewriting either of them.
    """
    script = _script_directory()
    heads = script.get_heads()
    assert len(heads) == 1, f"expected exactly one head, got {heads}"
    head = heads[0]
    lineage = {
        revision.revision
        for revision in script.walk_revisions(head=head)
    }
    assert MERGE_REVISION in lineage, (
        "the read-state merge revision must stay in the current head's ancestry"
    )
    merge = script.get_revision(MERGE_REVISION)
    assert set(merge.down_revision) == {
        UNIFIED_MAIN_REVISION,
        READ_CURSOR_REVISION,
    }
    # Neither parent is rewritten by the merge.
    assert set(script.get_revision(UNIFIED_MAIN_REVISION).down_revision) == {
        "a6b9d2e4f701",
        CONSENT_REVISION,
    }
    assert script.get_revision(READ_CURSOR_REVISION).down_revision == "a6b9d2e4f701"


def _assert_no_op_body(node: ast.FunctionDef) -> None:
    """Assert a migration function performs no operation.

    A leading docstring is documentation rather than an operation, so it is
    ignored when checking that the body is a single ``pass``.
    """
    body = list(node.body)
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        body = body[1:]
    assert len(body) == 1, f"{node.name} must be a no-op body, got {body}"
    assert isinstance(body[0], ast.Pass), f"{node.name} must be a no-op body"


def test_merge_revision_contains_no_schema_ddl():
    """A graph-only merge must not create, alter or drop anything."""
    path = VERSIONS_DIR / "3a91d7c4e8b2_merge_read_cursor_and_unified_main_heads.py"
    tree = ast.parse(path.read_text())
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"upgrade", "downgrade"}
    }
    assert set(functions) == {"upgrade", "downgrade"}
    for name, node in functions.items():
        _assert_no_op_body(node)
    assert (
        "op." not in path.read_text()
    ), "a graph-only merge must not call Alembic operations"


@pytest.mark.parametrize(
    "starting_point", ["clean", "unified_main", "read_cursor", "both"]
)
def test_merge_upgrade_and_round_trip_preserves_all_three_authorities(
    disposable_postgres, starting_point
):
    config, engine = disposable_postgres

    if starting_point == "clean":
        command.upgrade(config, MERGE_REVISION)
    elif starting_point == "both":
        command.upgrade(config, UNIFIED_MAIN_REVISION)
        command.upgrade(config, READ_CURSOR_REVISION)
        assert _current_heads(engine) == {
            UNIFIED_MAIN_REVISION,
            READ_CURSOR_REVISION,
        }
    elif starting_point == "unified_main":
        command.upgrade(config, UNIFIED_MAIN_REVISION)
    else:
        command.upgrade(config, READ_CURSOR_REVISION)
        command.upgrade(config, CONSENT_REVISION)

    has_widget = starting_point in {"clean", "unified_main", "both"}
    has_cursor = starting_point in {"clean", "read_cursor", "both"}
    has_consent = starting_point in {"clean", "read_cursor", "both"}

    with engine.begin() as connection:
        _seed_account(connection)
        if has_widget:
            _seed_widget(connection)
        if has_cursor:
            conversation_id, message_id = _seed_messaging_and_cursor(connection)
        else:
            conversation_id, message_id = None, None
        if has_consent:
            _enable_consent(connection)
            expected_consent = _consent_record(connection)
        else:
            expected_consent = None

    command.upgrade(config, MERGE_REVISION)

    inspector = sa.inspect(engine)
    for table in (WIDGETS_TABLE, REVISIONS_TABLE, CURSOR_TABLE):
        assert table in inspector.get_table_names(), table

    assert set(inspector.get_pk_constraint(CURSOR_TABLE)["constrained_columns"]) == {
        "conversation_id",
        "profile_id",
    }
    assert "user_settings_automatic_memory_suggestions_check" in {
        c["name"] for c in inspector.get_check_constraints("user_settings")
    }
    assert "saved_widgets_current_revision_check" in {
        c["name"] for c in inspector.get_check_constraints(WIDGETS_TABLE)
    }

    assert _current_heads(engine) == {MERGE_REVISION}

    with engine.begin() as connection:
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent
        else:
            assert _consent_record(connection) == ("unset", "1", None, None, None)
        if not has_widget:
            _seed_widget(connection)
        if not has_cursor:
            conversation_id, message_id = _seed_messaging_and_cursor(connection)
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": WIDGET_ID},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM direct_message_read_cursors "
                    "WHERE conversation_id=:cid"
                ),
                {"cid": conversation_id},
            ).scalar_one()
            == 1
        )
        # The participant-local cursor guard still holds.
        with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
            connection.execute(
                sa.text(
                    "INSERT INTO direct_message_read_cursors "
                    "(conversation_id, profile_id) VALUES (:cid, 'x')"
                ),
                {"cid": conversation_id},
            )

    # A relative -1 is ambiguous at a merge; target one parent explicitly.
    # The merge alone is removed, leaving both branch heads applied.
    command.downgrade(config, UNIFIED_MAIN_REVISION)
    assert _current_heads(engine) == {
        UNIFIED_MAIN_REVISION,
        READ_CURSOR_REVISION,
    }
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": WIDGET_ID},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM direct_message_read_cursors "
                    "WHERE conversation_id=:cid"
                ),
                {"cid": conversation_id},
            ).scalar_one()
            == 1
        )
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent

    command.upgrade(config, MERGE_REVISION)
    assert _current_heads(engine) == {MERGE_REVISION}
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": WIDGET_ID},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM direct_message_read_cursors "
                    "WHERE conversation_id=:cid"
                ),
                {"cid": conversation_id},
            ).scalar_one()
            == 1
        )
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent
