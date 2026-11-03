"""Migration proof for the Saved Widget / consent head merge.

The mainline carried two independent Alembic heads: the canonical Saved
Widget identity and immutable revision storage (``a6b9d2e4f701``) and the
account-owned automatic-collection consent (``c59e4d1a28f0``).  This module
proves that the graph-only merge revision ``7f2c9e1a4b63`` joins them into a
single head without changing the schema, without rewriting either parent, and
without disturbing Saved Widget identities, immutable revision snapshots, or
account consent values.

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

MERGE_REVISION = "7f2c9e1a4b63"
SAVED_WIDGET_REVISION = "a6b9d2e4f701"
CONSENT_REVISION = "c59e4d1a28f0"

WIDGETS_TABLE = "saved_widgets"
REVISIONS_TABLE = "saved_widget_revisions"

CONSENT_COLUMNS = {
    "automatic_memory_suggestions",
    "consent_policy_version",
    "consent_recorded_by_user_id",
    "consent_recorded_at",
    "consent_updated_at",
}
CONSENT_CHECK = "user_settings_automatic_memory_suggestions_check"

ACCOUNT_ID = "merge-proof-account"


class _DisposablePostgres:
    """A disposable PostgreSQL database plus its Alembic configuration."""

    def __init__(
        self,
        config: Config,
        engine: sa.Engine,
        session_factory: Any,
        db_name: str,
    ) -> None:
        self.config = config
        self.engine = engine
        self.session_factory = session_factory
        self.db_name = db_name


@pytest.fixture
def disposable_postgres(monkeypatch) -> Iterator[_DisposablePostgres]:
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_head_merge_{uuid.uuid4().hex[:12]}"
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
        yield _DisposablePostgres(config, engine, sessionmaker(bind=engine), db_name)
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


def _sole_head_lineage(script: ScriptDirectory) -> set[str]:
    """The revisions reachable from the single Alembic head.

    The Saved Widget/consent merge may sit directly at the head, or below a
    further merge revision added on top of it later. The invariant this file
    protects is therefore stated as an ancestry relation rather than as a
    literal head identifier: exactly one head exists, and the merge revision is
    on its lineage.
    """
    heads = script.get_heads()
    assert len(heads) == 1, f"expected exactly one Alembic head, found {heads}"
    return {
        revision.revision for revision in script.iterate_revisions(heads[0], "base")
    }


def _assert_single_head_on_merge_lineage(engine: sa.Engine) -> None:
    """Assert the applied database head is unique and descends from the merge."""
    db_heads = _current_heads(engine)
    assert len(db_heads) == 1, f"expected exactly one Alembic head, found {db_heads}"
    db_head = next(iter(db_heads))
    lineage = {
        revision.revision
        for revision in _script_directory().iterate_revisions(db_head, "base")
    }
    assert MERGE_REVISION in lineage, (
        f"applied head {db_head} does not descend from the Saved Widget/consent "
        f"merge {MERGE_REVISION}"
    )


def _seed_account(connection) -> None:
    """Seed the account the Saved Widget is owned by, plus its settings row."""
    connection.execute(
        sa.text(
            "INSERT INTO users (id, username, password_hash, role) VALUES "
            "(:uid, 'merge-proof-user', 'not-a-real-hash', 'guest')"
        ),
        {"uid": ACCOUNT_ID},
    )
    connection.execute(
        sa.text(
            "INSERT INTO user_settings (user_id, memory_mode) VALUES (:uid, 'light')"
        ),
        {"uid": ACCOUNT_ID},
    )


def _seed_widget(connection, widget_id: str) -> None:
    """Seed one Saved Widget and its first immutable revision.

    The widget row is written first: its current-revision pointer is a
    deferrable composite foreign key, so it is only checked at commit.  The
    revision row's own foreign key to the widget is immediate.
    """
    connection.execute(
        sa.text(
            "INSERT INTO saved_widgets "
            "(widget_id, owner_user_id, name, current_revision) "
            "VALUES (:widget_id, :uid, 'Merge Proof Widget', 1)"
        ),
        {"widget_id": widget_id, "uid": ACCOUNT_ID},
    )
    connection.execute(
        sa.text(
            "INSERT INTO saved_widget_revisions "
            "(widget_id, revision, artifact_snapshot, provenance_snapshot, "
            "creation_context) VALUES "
            "(:widget_id, 1, '{}'::jsonb, '{}'::jsonb, '{}'::jsonb)"
        ),
        {"widget_id": widget_id},
    )


def _seed_account_and_widget(engine: sa.Engine) -> tuple[str, str]:
    """Seed one account, one Saved Widget and its first immutable revision."""
    widget_id = "widget-merge-proof"
    with engine.begin() as connection:
        _seed_account(connection)
        _seed_widget(connection, widget_id)
    return widget_id, ACCOUNT_ID


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


def test_merge_revision_is_the_only_head_and_parents_both_branches():
    script = _script_directory()
    assert MERGE_REVISION in _sole_head_lineage(script)
    merge = script.get_revision(MERGE_REVISION)
    assert set(merge.down_revision) == {SAVED_WIDGET_REVISION, CONSENT_REVISION}
    # The parents are untouched by the merge.
    assert script.get_revision(SAVED_WIDGET_REVISION).down_revision == ("f0d7c4b2a198")
    assert script.get_revision(CONSENT_REVISION).down_revision == "f0d7c4b2a198"


def _revision_module_path(revision_id: str):
    """Locate the migration module that declares ``revision_id``.

    The file name is not part of the migration contract — only the revision
    identifier is — so the module is resolved by reading each module's
    ``revision`` assignment rather than by a hard-coded path. The assignment is
    read from the parsed module so that the declaration style (single or double
    quotes, annotated or plain) does not matter.
    """
    matches = []
    for candidate in sorted(VERSIONS_DIR.glob("*.py")):
        tree = ast.parse(candidate.read_text())
        for node in tree.body:
            if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                if node.target.id == "revision":
                    value = ast.literal_eval(node.value)
            elif isinstance(node, ast.Assign):
                names = [t.id for t in node.targets if isinstance(t, ast.Name)]
                if "revision" in names:
                    value = ast.literal_eval(node.value)
            else:
                continue
            if value == revision_id:
                matches.append(candidate)
                break
    assert len(matches) == 1, (
        f"expected exactly one module declaring {revision_id}, found {matches}"
    )
    return matches[0]


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
    path = _revision_module_path(MERGE_REVISION)
    tree = ast.parse(path.read_text())
    functions = {
        node.name: node
        for node in tree.body
        if isinstance(node, ast.FunctionDef) and node.name in {"upgrade", "downgrade"}
    }
    assert set(functions) == {"upgrade", "downgrade"}
    for name, node in functions.items():
        _assert_no_op_body(node)
    source = path.read_text()
    assert "op." not in source, "a graph-only merge must not call Alembic operations"


@pytest.mark.parametrize("starting_point", ["clean", "saved_widget", "consent", "both"])
def test_merge_upgrade_and_round_trip_preserves_both_authorities(
    disposable_postgres, starting_point
):
    config = disposable_postgres.config
    engine = disposable_postgres.engine

    if starting_point == "clean":
        command.upgrade(config, "head")
    elif starting_point == "both":
        command.upgrade(config, SAVED_WIDGET_REVISION)
        command.upgrade(config, CONSENT_REVISION)
        assert _current_heads(engine) == {SAVED_WIDGET_REVISION, CONSENT_REVISION}
    else:
        command.upgrade(
            config,
            (
                SAVED_WIDGET_REVISION
                if starting_point == "saved_widget"
                else CONSENT_REVISION
            ),
        )

    has_widget = starting_point in {"clean", "saved_widget", "both"}
    has_consent = starting_point in {"clean", "consent", "both"}

    widget_id = "widget-merge-proof"
    if has_widget:
        widget_id, _ = _seed_account_and_widget(engine)
    else:
        # The account and its settings row exist regardless of which branch
        # installed the schema; the widget is what the Saved Widget branch
        # owns.
        with engine.begin() as connection:
            _seed_account(connection)

    with engine.begin() as connection:
        if has_consent:
            _enable_consent(connection)
            expected_consent = _consent_record(connection)
        else:
            expected_consent = None

    command.upgrade(config, "head")

    inspector = sa.inspect(engine)
    assert WIDGETS_TABLE in inspector.get_table_names()
    assert REVISIONS_TABLE in inspector.get_table_names()
    assert set(inspector.get_pk_constraint(WIDGETS_TABLE)["constrained_columns"]) == {
        "widget_id"
    }
    assert set(inspector.get_pk_constraint(REVISIONS_TABLE)["constrained_columns"]) == {
        "widget_id",
        "revision",
    }

    widget_constraints = {
        c["name"] for c in inspector.get_check_constraints(WIDGETS_TABLE)
    }
    assert "saved_widgets_lifecycle_state_check" in widget_constraints
    assert "saved_widgets_current_revision_check" in widget_constraints
    revision_constraints = {
        c["name"] for c in inspector.get_check_constraints(REVISIONS_TABLE)
    }
    assert "saved_widget_revisions_revision_check" in revision_constraints

    settings_columns = {c["name"] for c in inspector.get_columns("user_settings")}
    assert CONSENT_COLUMNS <= settings_columns
    assert CONSENT_CHECK in {
        c["name"] for c in inspector.get_check_constraints("user_settings")
    }

    _assert_single_head_on_merge_lineage(engine)

    with engine.begin() as connection:
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent
        else:
            # The consent branch was not installed before the merge, so the
            # added columns carry their denying defaults.
            assert _consent_record(connection) == (
                "unset",
                "1",
                None,
                None,
                None,
            )
        if not has_widget:
            # The Saved Widget branch was not installed before the merge, so
            # the widget is written now, against the merged schema.
            _seed_widget(connection, widget_id)
        # The Saved Widget identity and its immutable revision are intact.
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM saved_widget_revisions "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            ).scalar_one()
            == 1
        )
        # The consent state domain and the Saved Widget guard still hold.
        with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
            connection.execute(
                sa.text(
                    "UPDATE user_settings SET automatic_memory_suggestions='bogus' "
                    "WHERE user_id=:uid"
                ),
                {"uid": ACCOUNT_ID},
            )
        with pytest.raises(sa.exc.IntegrityError), connection.begin_nested():
            connection.execute(
                sa.text(
                    "UPDATE saved_widgets SET current_revision=0 "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            )

    # A relative -1 is ambiguous at a merge; target one parent explicitly.
    # The merge alone is removed, leaving both branch heads applied. Other
    # branches may also survive that downgrade — the Guardian Coding
    # integration adds a third — so the invariant is that both authorities
    # are present, not that they are the only heads.
    command.downgrade(config, SAVED_WIDGET_REVISION)
    assert {SAVED_WIDGET_REVISION, CONSENT_REVISION} <= _current_heads(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            ).scalar_one()
            == 1
        )
        assert (
            connection.execute(
                sa.text(
                    "SELECT count(*) FROM saved_widget_revisions "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            ).scalar_one()
            == 1
        )
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent

    command.upgrade(config, "head")
    _assert_single_head_on_merge_lineage(engine)
    with engine.connect() as connection:
        assert (
            connection.execute(
                sa.text(
                    "SELECT current_revision FROM saved_widgets "
                    "WHERE widget_id=:widget_id"
                ),
                {"widget_id": widget_id},
            ).scalar_one()
            == 1
        )
        if expected_consent is not None:
            assert _consent_record(connection) == expected_consent
