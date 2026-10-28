"""Guardian coding worker — durable claim and heartbeat schema merge contract.

The durable-acceptance slice gave an accepted Guardian coding run a canonical
``running`` state. The ownership slice added a durable record of *which*
coding-worker instance took the claim, and the heartbeat slice added the last
durable liveness observation reported by that owner. Both live on
``agent_runs``.

This contract covers the **schema only**: that the two feature migrations and
one explicit mergepoint join the mainline migration graph into a single head,
that the resulting database enforces the ownership pairing, claim uniqueness,
and heartbeat-requires-ownership rules, and that historical ownership-unknown
rows stay valid.

**What this contract deliberately does not claim.** Nothing here proves worker
execution, liveness, retry, recovery, takeover, or account authority. A
persisted owner is not proof that the worker is still alive; a claim id is
durable correlation material, not retry authority; a heartbeat is subordinate
execution *evidence*, never authorization; and an absent or stale heartbeat is
not proof that the worker died. Those behaviours remain separate, dependent
slices and are proven by the feature branch's own worker-execution contract
suites, which this schema-only contract does not duplicate.
"""

from __future__ import annotations

import hashlib
import os
import pathlib
import uuid
from typing import Any

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.engine import make_url
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import sessionmaker

from guardian.db.models import AgentRun, Base

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

#: The mergepoint that joins the mainline head to the coding-worker head.
MERGE_REVISION = "c8e42a91d307"
#: The head the mainline carried before this integration.
MAIN_HEAD = "3a91d7c4e8b2"
#: The head the feature branch carried.
CODING_HEAD = "d86f2a4b1c90"
#: The two original feature migrations.
OWNERSHIP_REVISION = "e42c7d0b9135"
HEARTBEAT_REVISION = "d86f2a4b1c90"
#: The historical parent both feature migrations descend from.
SHARED_PARENT = "f0d7c4b2a198"

#: sha256 of the two original migration files, so their historical identity is
#: self-contained: the files must stay byte-identical to the feature branch's
#: originals and must not be reparented, renamed, squashed, or regenerated.
ORIGINAL_MIGRATION_DIGESTS = {
    "e42c7d0b9135_coding_run_worker_ownership.py":
        "8b5415399ea57194638aa0c287535098bbdfe05bdf9e223a801889f0552694a5",
    "d86f2a4b1c90_coding_run_claim_heartbeat.py":
        "e2bdc837e37b90c405072e3cb9d0891d45e7669b7fb2d7713b4ec53c68ee67e6",
}

#: The three columns this integration adds to ``agent_runs``.
NEW_COLUMNS = (
    "coding_worker_instance_id",
    "coding_worker_claim_id",
    "coding_worker_last_heartbeat_at",
)

#: ``agent_runs`` as mainline declared it before this integration. Used as the
#: oracle for "no unrelated declaration changed".
MAIN_BASELINE_COLUMNS = (
    "id",
    "run_id",
    "deployment_id",
    "account_origin_user_id",
    "thread_id",
    "status",
    "runtime_target",
    "rollback_mode",
    "rollback_applied",
    "rollback_reason",
    "worktree_id",
    "worktree_path",
    "error",
    "created_at",
    "started_at",
    "ended_at",
)

MAIN_BASELINE_CONSTRAINTS = (
    "agent_runs_status_check",
    "agent_runs_runtime_target_check",
    "agent_runs_rollback_mode_check",
)

#: The three constraints this integration adds.
NEW_CONSTRAINTS = (
    "agent_runs_coding_worker_ownership_check",
    "agent_runs_coding_worker_heartbeat_ownership_check",
    "uq_agent_runs_coding_worker_claim_id",
)

#: Mainline revisions that must still be reachable from the single head.
PRESERVED_MAINLINE_REVISIONS = (
    "7f2c9e1a4b63",  # Saved Widget / consent mergepoint
    "3a91d7c4e8b2",  # read-cursor mergepoint (previous mainline head)
    "b3c8d1e5f7a2",  # direct-message read cursor
    "a6b9d2e4f701",  # Saved Widget identity and revisions
    "c59e4d1a28f0",  # automatic memory-suggestions consent
    "f0d7c4b2a198",  # shared parent
    "2e865c4a9b10",  # historical branchpoint
)


def _script_directory() -> ScriptDirectory:
    return ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )


def _lineage(head: str) -> set[str]:
    script = _script_directory()
    return {revision.revision for revision in script.walk_revisions(head=head)}


# ---------------------------------------------------------------------------
# Migration graph
# ---------------------------------------------------------------------------


def test_the_graph_has_exactly_one_head() -> None:
    """The mergepoint leaves the graph with a single head."""
    heads = tuple(_script_directory().get_heads())
    assert heads == (MERGE_REVISION,), f"expected one head, got {heads}"


def test_both_original_branches_are_ancestors_of_the_head() -> None:
    """Both the mainline head and the coding-worker head reach the mergepoint."""
    lineage = _lineage(MERGE_REVISION)
    assert MAIN_HEAD in lineage, "mainline head is not an ancestor"
    assert CODING_HEAD in lineage, "coding-worker head is not an ancestor"
    assert OWNERSHIP_REVISION in lineage
    assert HEARTBEAT_REVISION in lineage
    assert SHARED_PARENT in lineage


def test_the_original_migrations_retain_their_historical_identities() -> None:
    """The two feature migrations are unchanged, byte for byte."""
    versions = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
    for name, digest in ORIGINAL_MIGRATION_DIGESTS.items():
        path = versions / name
        assert path.is_file(), f"missing original migration {name}"
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        assert actual == digest, f"{name} was modified: {actual} != {digest}"

    ownership = __import__(
        "guardian.db.migrations.versions."
        "e42c7d0b9135_coding_run_worker_ownership",
        fromlist=["revision", "down_revision"],
    )
    heartbeat = __import__(
        "guardian.db.migrations.versions."
        "d86f2a4b1c90_coding_run_claim_heartbeat",
        fromlist=["revision", "down_revision"],
    )
    assert ownership.revision == OWNERSHIP_REVISION
    assert ownership.down_revision == SHARED_PARENT
    assert heartbeat.revision == HEARTBEAT_REVISION
    assert heartbeat.down_revision == OWNERSHIP_REVISION


def test_existing_mainline_migration_history_is_preserved() -> None:
    """No mainline revision was dropped or rewritten by the integration."""
    lineage = _lineage(MERGE_REVISION)
    for revision in PRESERVED_MAINLINE_REVISIONS:
        assert revision in lineage, f"mainline revision {revision} was lost"

    merge = _script_directory().get_revision(MERGE_REVISION)
    assert merge.down_revision == (MAIN_HEAD, CODING_HEAD)

    # The mergepoint is graph-only: it adds no schema operation of its own.
    source = (REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
              / "c8e42a91d307_merge_guardian_coding_claim_and_main_heads.py")
    body = source.read_text()
    for operation in ("op.add_column", "op.create_table", "op.create_index",
                      "op.create_check_constraint", "op.create_unique_constraint",
                      "op.drop_column", "op.drop_table"):
        assert operation not in body, f"merge revision contains {operation}"


# ---------------------------------------------------------------------------
# ORM declaration
# ---------------------------------------------------------------------------


def test_agent_run_exposes_the_expected_new_columns() -> None:
    """The ORM declares the three columns and nothing else changed."""
    table = AgentRun.__table__
    columns = {column.name for column in table.columns}
    for column in NEW_COLUMNS:
        assert column in columns, f"AgentRun is missing {column}"

    assert set(MAIN_BASELINE_COLUMNS) | set(NEW_COLUMNS) == columns, (
        "agent_runs columns differ from mainline baseline plus the three new "
        f"columns: {sorted(columns)}"
    )

    for column in NEW_COLUMNS:
        assert table.columns[column].nullable, f"{column} must stay nullable"


def test_no_new_retry_recovery_or_account_authority_is_introduced() -> None:
    """The new fields are execution evidence, never authority."""
    table = AgentRun.__table__

    constraint_names = {c.name for c in table.constraints if c.name}
    assert constraint_names == set(MAIN_BASELINE_CONSTRAINTS) | set(NEW_CONSTRAINTS)

    for name in NEW_CONSTRAINTS:
        assert not any(
            token in name
            for token in ("lease", "expiry", "expire", "takeover", "retry",
                          "recovery", "reclaim", "account", "principal")
        ), f"constraint {name} encodes authority beyond execution evidence"

    # The three columns are plain strings/timestamps. They are not foreign
    # keys, so they cannot become an account, principal, or credential
    # authority, and they cannot carry an expiry or takeover decision.
    for column in NEW_COLUMNS:
        assert not table.columns[column].foreign_keys, (
            f"{column} must not be a foreign key"
        )
    assert str(table.columns["coding_worker_instance_id"].type) == "VARCHAR(64)"
    assert str(table.columns["coding_worker_claim_id"].type) == "VARCHAR(64)"


# ---------------------------------------------------------------------------
# Database behaviour
# ---------------------------------------------------------------------------


class _DisposablePostgres:
    """A disposable PostgreSQL database migrated to the combined head."""

    def __init__(self, config: Config, engine: sa.Engine, db_name: str) -> None:
        self.config = config
        self.engine = engine
        self.db_name = db_name

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self.config, revision)

    def execute(self, statement: str, **params: Any) -> Any:
        """Run one statement in its own committed transaction."""
        with self.engine.begin() as connection:
            return connection.execute(sa.text(statement), params)

    def scalar(self, statement: str, **params: Any) -> Any:
        with self.engine.begin() as connection:
            return connection.execute(sa.text(statement), params).scalar()


@pytest.fixture
def disposable_postgres(monkeypatch):
    """A disposable PostgreSQL database at the combined head."""
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_coding_claim_{uuid.uuid4().hex[:12]}"
    base = make_url(base_url)
    admin_url = base.set(drivername="postgresql", database="postgres")
    test_url = base.set(drivername="postgresql+psycopg", database=db_name)

    with psycopg.connect(
        admin_url.render_as_string(hide_password=False), autocommit=True
    ) as connection:
        connection.execute(f'CREATE DATABASE "{db_name}"')

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
        disposable = _DisposablePostgres(config, engine, db_name)
        disposable.upgrade("head")
        yield disposable
        engine.dispose()
    finally:
        with psycopg.connect(
            admin_url.render_as_string(hide_password=False), autocommit=True
        ) as connection:
            connection.execute(
                "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                "WHERE datname = %s",
                (db_name,),
            )
            connection.execute(f'DROP DATABASE IF EXISTS "{db_name}"')


def _expect_violation(
    db: _DisposablePostgres,
    statement: str,
    expected_constraint: str,
    **params: Any,
) -> None:
    """Assert the database refuses a statement for the *named* reason.

    The constraint name is asserted, not just the exception type: an
    IntegrityError raised by some other constraint would otherwise let these
    tests pass without proving the intended rule.
    """
    with pytest.raises(IntegrityError) as excinfo:
        db.execute(statement, **params)
    message = str(excinfo.value)
    assert expected_constraint in message, (
        f"expected {expected_constraint} to reject the statement, got: {message}"
    )


def _seed_deployment(db: _DisposablePostgres, suffix: str) -> int:
    """Create one agent deployment and return its primary key."""
    return db.scalar(
        "INSERT INTO agent_deployments (deployment_id, flow_id, spec_hash) "
        "VALUES (:deployment_id, :flow_id, :spec_hash) RETURNING id",
        deployment_id=f"dep-{suffix}",
        flow_id=f"flow-{suffix}",
        spec_hash=f"hash-{suffix}",
    )


def _insert_run(
    db: _DisposablePostgres,
    suffix: str,
    deployment_id: int,
    *,
    instance_id: str | None = None,
    claim_id: str | None = None,
    heartbeat_at: str | None = None,
) -> None:
    db.execute(
        "INSERT INTO agent_runs (run_id, deployment_id, status, runtime_target, "
        "rollback_mode, coding_worker_instance_id, coding_worker_claim_id, "
        "coding_worker_last_heartbeat_at) "
        "VALUES (:run_id, :deployment_id, 'running', 'container', 'manual', "
        ":instance_id, :claim_id, :heartbeat_at)",
        run_id=f"run-{suffix}",
        deployment_id=deployment_id,
        instance_id=instance_id,
        claim_id=claim_id,
        heartbeat_at=heartbeat_at,
    )


def test_ownership_fields_must_be_present_together_or_both_absent(
    disposable_postgres: _DisposablePostgres,
) -> None:
    """Half an ownership record is rejected by the database."""
    deployment_id = _seed_deployment(disposable_postgres, "paired")

    _expect_violation(
        disposable_postgres,
        "INSERT INTO agent_runs (run_id, deployment_id, status, "
        "runtime_target, rollback_mode, coding_worker_instance_id) "
        "VALUES ('run-instance-only', :deployment_id, 'running', "
        "'container', 'manual', 'worker-a')",
        "agent_runs_coding_worker_ownership_check",
        deployment_id=deployment_id,
    )

    _expect_violation(
        disposable_postgres,
        "INSERT INTO agent_runs (run_id, deployment_id, status, "
        "runtime_target, rollback_mode, coding_worker_claim_id) "
        "VALUES ('run-claim-only', :deployment_id, 'running', "
        "'container', 'manual', 'claim-a')",
        "agent_runs_coding_worker_ownership_check",
        deployment_id=deployment_id,
    )

    # Both present is accepted.
    _insert_run(
        disposable_postgres,
        "paired-ok",
        deployment_id,
        instance_id="worker-a",
        claim_id="claim-a",
    )


def test_duplicate_non_null_claim_ids_are_rejected(
    disposable_postgres: _DisposablePostgres,
) -> None:
    """One claim id identifies exactly one acceptance."""
    deployment_id = _seed_deployment(disposable_postgres, "unique")

    _insert_run(
        disposable_postgres,
        "claim-first",
        deployment_id,
        instance_id="worker-a",
        claim_id="claim-shared",
    )

    _expect_violation(
        disposable_postgres,
        "INSERT INTO agent_runs (run_id, deployment_id, status, "
        "runtime_target, rollback_mode, coding_worker_instance_id, "
        "coding_worker_claim_id) VALUES ('run-claim-duplicate', "
        ":deployment_id, 'running', 'container', 'manual', "
        "'worker-b', 'claim-shared')",
        "uq_agent_runs_coding_worker_claim_id",
        deployment_id=deployment_id,
    )

    # NULL claim ids stay distinct, so ownership-unknown rows are unaffected.
    _insert_run(disposable_postgres, "claim-null-1", deployment_id)
    _insert_run(disposable_postgres, "claim-null-2", deployment_id)


def test_a_heartbeat_without_ownership_is_rejected(
    disposable_postgres: _DisposablePostgres,
) -> None:
    """A heartbeat is evidence about an owner, so it requires one."""
    deployment_id = _seed_deployment(disposable_postgres, "heartbeat")

    _expect_violation(
        disposable_postgres,
        "INSERT INTO agent_runs (run_id, deployment_id, status, "
        "runtime_target, rollback_mode, coding_worker_last_heartbeat_at) "
        "VALUES ('run-heartbeat-only', :deployment_id, 'running', "
        "'container', 'manual', now())",
        "agent_runs_coding_worker_heartbeat_ownership_check",
        deployment_id=deployment_id,
    )

    # With an owner present, the same heartbeat is accepted.
    _insert_run(
        disposable_postgres,
        "heartbeat-ok",
        deployment_id,
        instance_id="worker-a",
        claim_id="claim-heartbeat",
        heartbeat_at="2026-10-28 12:00:00+00",
    )


def test_historical_rows_without_ownership_remain_valid(
    disposable_postgres: _DisposablePostgres,
) -> None:
    """Rows accepted before these migrations stay valid and untouched."""
    deployment_id = _seed_deployment(disposable_postgres, "historical")

    _insert_run(disposable_postgres, "historical-1", deployment_id)
    _insert_run(disposable_postgres, "historical-2", deployment_id)

    count = disposable_postgres.scalar(
        "SELECT count(*) FROM agent_runs WHERE deployment_id = :deployment_id "
        "AND coding_worker_instance_id IS NULL "
        "AND coding_worker_claim_id IS NULL "
        "AND coding_worker_last_heartbeat_at IS NULL",
        deployment_id=deployment_id,
    )
    assert count == 2, "historical ownership-unknown rows must remain valid"


def test_the_existing_schema_families_survive_the_merge(
    disposable_postgres: _DisposablePostgres,
) -> None:
    """The integration adds coding-claim evidence and disturbs nothing else."""
    tables = {
        row[0]
        for row in disposable_postgres.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'public'"
        ).all()
    }
    assert {"saved_widgets", "saved_widget_revisions"} <= tables
    assert "direct_message_read_cursors" in tables
    assert "agent_runs" in tables

    consent = disposable_postgres.scalar(
        "SELECT count(*) FROM information_schema.columns WHERE "
        "table_name = 'user_settings' AND "
        "column_name = 'automatic_memory_suggestions'"
    )
    assert consent == 1, "the consent column must survive"
