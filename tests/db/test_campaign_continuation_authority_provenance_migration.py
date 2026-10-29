"""Campaign Continuation Authority provenance: PostgreSQL migration proof.

Proves the ADR-105 provenance discriminator is durably stored per action:
independent approval and revocation provenance on the canonical authority
record, a bounded migration that classifies established historical actions
as legacy without changing any actor id or timestamp, and a reversible
upgrade/downgrade/re-upgrade cycle.

Every test here runs against a uniquely named disposable database built from
the repository's own Alembic migrations. No production data is used, no
existing database is reused, and the database is dropped afterwards.

ADR: docs/architecture/adr/105-operator-actor-identity-and-human-approval-provenance.md
"""

from __future__ import annotations

import os
import pathlib
import uuid
from typing import Any, Iterator

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

from guardian.db.models import Base

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]

AUTHORITIES_TABLE = "campaign_continuation_authorities"

#: The revision that introduced the provenance discriminator.
PROVENANCE_REVISION = "b7e2c4a1d903"

#: The revision immediately before it, which the migration must declare as
#: its parent.
PARENT_REVISION = "3a91d7c4e8b2"

#: The provenance class assigned to every pre-existing action.
LEGACY_PROVENANCE = "legacy_unverified"


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

    def upgrade(self, revision: str = "head") -> None:
        command.upgrade(self.config, revision)

    def downgrade(self, revision: str) -> None:
        command.downgrade(self.config, revision)

    def session(self):
        return self.session_factory()

    def scalar(self, statement: str, **params: Any) -> Any:
        with self.engine.connect() as connection:
            return connection.execute(sa.text(statement), params).scalar()


@pytest.fixture
def disposable_postgres(monkeypatch):
    """A disposable PostgreSQL database at no particular revision.

    The fixture creates the database and points Alembic at it; the test
    decides which revision to upgrade to.
    """
    psycopg = pytest.importorskip("psycopg")
    base_url = os.getenv("TEST_DATABASE_URL")
    if not base_url:
        pytest.skip("TEST_DATABASE_URL required for disposable Postgres proof")

    db_name = f"codexify_authority_provenance_{uuid.uuid4().hex[:12]}"
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
        yield _DisposablePostgres(
            config, engine, sessionmaker(bind=engine), db_name
        )
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


#: The columns the provenance migration does not own. A historical row keeps
#: exactly these values across the migration.
_BASE_COLUMNS = (
    "authority_id",
    "campaign_id",
    "envelope_json",
    "approved_by_actor_id",
    "approved_at",
    "expires_at",
    "revoked_by_actor_id",
    "revoked_at",
    "revocation_reason",
    "created_at",
)


def _authority_columns(db: _DisposablePostgres) -> set[str]:
    """The authority table's live column names at the current revision."""
    inspector = sa.inspect(db.engine)
    return {c["name"] for c in inspector.get_columns(AUTHORITIES_TABLE)}


def _seed_campaign(db: _DisposablePostgres, campaign_id: str) -> None:
    """Create the Campaign (and its goal) an authority row points at."""
    with db.engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO campaign_goals (goal_id, title, summary, status) "
                "VALUES (:goal_id, :title, '', 'active')"
            ),
            {"goal_id": f"goal-{campaign_id}", "title": f"Goal for {campaign_id}"},
        )
        connection.execute(
            sa.text(
                "INSERT INTO campaigns (campaign_id, goal_id, title, summary, status) "
                "VALUES (:campaign_id, :goal_id, :title, '', 'active')"
            ),
            {
                "campaign_id": campaign_id,
                "goal_id": f"goal-{campaign_id}",
                "title": f"Campaign {campaign_id}",
            },
        )


def _seed_historical_authority(
    db: _DisposablePostgres,
    *,
    authority_id: str,
    campaign_id: str,
    approved_by_actor_id: str,
    revoked: bool,
) -> dict[str, Any]:
    """Insert an authority row exactly as the pre-discriminator writer did.

    Raw SQL is used deliberately: the point of this test is that the
    migration classifies rows it never wrote, and that it leaves every
    column it does not own exactly as it found them. The provenance columns
    are supplied only when they already exist, so the same helper can seed
    either side of the migration.
    """
    columns = _authority_columns(db)
    values: dict[str, Any] = {
        "authority_id": authority_id,
        "campaign_id": campaign_id,
        "envelope": '{"schema_version": 1, "campaign_objective": "probe"}',
        "approved_by_actor_id": approved_by_actor_id,
        "approved_at": "2026-10-05T12:00:00+00:00",
        "expires_at": None,
        "revoked_by_actor_id": "operator-session" if revoked else None,
        "revoked_at": "2026-10-06T12:00:00+00:00" if revoked else None,
        "revocation_reason": "operator requested" if revoked else None,
        "created_at": "2026-10-05T12:00:00+00:00",
    }

    selected = list(_BASE_COLUMNS)
    if "approval_provenance" in columns:
        selected.append("approval_provenance")
        values["approval_provenance"] = LEGACY_PROVENANCE
    if "revocation_provenance" in columns:
        selected.append("revocation_provenance")
        values["revocation_provenance"] = LEGACY_PROVENANCE if revoked else None

    # The column list is literal; only the value list carries bind
    # parameters, and the JSONB envelope needs an explicit cast.
    value_expressions = {
        "envelope_json": "CAST(:envelope AS JSONB)",
    }
    value_sql_parts = [
        value_expressions.get(column, f":{column}") for column in selected
    ]

    with db.engine.begin() as connection:
        connection.execute(
            sa.text(
                f"INSERT INTO campaign_continuation_authorities "
                f"({', '.join(selected)}) "
                f"VALUES ({', '.join(value_sql_parts)})"
            ),
            values,
        )
    return {
        "authority_id": authority_id,
        "approved_by_actor_id": approved_by_actor_id,
        "approved_at": "2026-10-05T12:00:00+00:00",
    }


def _authority_snapshot(db: _DisposablePostgres) -> list[dict[str, Any]]:
    """Read back every authority row with the columns the migration owns."""
    columns = _authority_columns(db)
    selected = [column for column in _BASE_COLUMNS if column in columns]
    for provenance_column in ("approval_provenance", "revocation_provenance"):
        if provenance_column in columns:
            selected.append(provenance_column)
    with db.engine.connect() as connection:
        rows = connection.execute(
            sa.text(
                "SELECT "
                + ", ".join(selected)
                + f" FROM {AUTHORITIES_TABLE} ORDER BY authority_id"
            )
        ).mappings()
        return [dict(row) for row in rows]


def _assert_column_parity(inspector) -> None:
    """The migrated schema and the ORM metadata must describe the same table."""
    dialect = postgresql.dialect()
    db_columns = {
        c["name"]: c for c in inspector.get_columns(AUTHORITIES_TABLE)
    }
    meta_table = Base.metadata.tables[AUTHORITIES_TABLE]
    assert set(db_columns) == set(meta_table.columns.keys())
    for name, meta_column in meta_table.columns.items():
        db_type = db_columns[name]["type"].compile(dialect=dialect)
        meta_type = meta_column.type.dialect_impl(dialect).compile(dialect=dialect)
        assert db_type == meta_type, f"{name}: {db_type} != {meta_type}"
        assert db_columns[name]["nullable"] == meta_column.nullable, (
            f"{name}: nullability differs"
        )


def _assert_constraint_parity(inspector) -> None:
    """Constraint and index names must match the ORM metadata."""
    meta_table = Base.metadata.tables[AUTHORITIES_TABLE]

    db_checks = {
        c["name"] for c in inspector.get_check_constraints(AUTHORITIES_TABLE)
    }
    meta_checks = {
        c.name
        for c in meta_table.constraints
        if isinstance(c, sa.CheckConstraint) and c.name
    }
    assert meta_checks <= db_checks, "missing check constraints"

    db_indexes = {i["name"] for i in inspector.get_indexes(AUTHORITIES_TABLE)}
    meta_indexes = {i.name for i in meta_table.indexes}
    assert meta_indexes <= db_indexes, "missing indexes"


# ---------------------------------------------------------------------------
# Migration identity
# ---------------------------------------------------------------------------


def test_the_migration_declares_the_verified_parent(disposable_postgres) -> None:
    """The new revision extends the previously verified head."""
    module = __import__(
        "guardian.db.migrations.versions."
        "b7e2c4a1d903_add_campaign_continuation_authority_provenance",
        fromlist=["revision", "down_revision"],
    )
    assert module.revision == PROVENANCE_REVISION
    assert module.down_revision == PARENT_REVISION


def test_the_migration_is_the_single_head(disposable_postgres) -> None:
    """There is exactly one head, and this revision is in its ancestry."""
    script = ScriptDirectory.from_config(disposable_postgres.config)
    heads = tuple(script.get_heads())
    assert len(heads) == 1

    lineage = {
        revision.revision for revision in script.walk_revisions(head=heads[0])
    }
    assert PROVENANCE_REVISION in lineage


# ---------------------------------------------------------------------------
# Fresh database
# ---------------------------------------------------------------------------


def test_fresh_upgrade_creates_the_provenance_columns(
    disposable_postgres,
) -> None:
    """Upgrading an empty database to head adds both provenance columns."""
    disposable_postgres.upgrade("head")

    inspector = sa.inspect(disposable_postgres.engine)
    columns = {
        c["name"]: c for c in inspector.get_columns(AUTHORITIES_TABLE)
    }
    assert "approval_provenance" in columns
    assert "revocation_provenance" in columns

    # Approval provenance is mandatory; revocation provenance is present only
    # on a revoked row.
    assert columns["approval_provenance"]["nullable"] is False
    assert columns["revocation_provenance"]["nullable"] is True

    # The new columns carry no server default, so an insert that omits the
    # approval provenance fails closed instead of silently inheriting a class.
    assert columns["approval_provenance"].get("default") is None

    assert disposable_postgres.scalar(
        f"SELECT count(*) FROM {AUTHORITIES_TABLE}"
    ) == 0


def test_the_migrated_schema_enforces_the_expected_constraints(
    disposable_postgres,
) -> None:
    """The provenance vocabulary and the revocation coupling are enforced."""
    disposable_postgres.upgrade("head")
    inspector = sa.inspect(disposable_postgres.engine)

    checks = {
        c["name"]: c["sqltext"]
        for c in inspector.get_check_constraints(AUTHORITIES_TABLE)
    }
    assert "campaign_continuation_authorities_approval_provenance_check" in checks
    assert "campaign_continuation_authorities_revocation_provenance_check" in checks

    approval_check = checks[
        "campaign_continuation_authorities_approval_provenance_check"
    ]
    for value in ("legacy_unverified", "operator_deployment", "account_admin"):
        assert value in approval_check


def test_the_orm_metadata_agrees_with_the_migrated_schema(
    disposable_postgres,
) -> None:
    """The ORM models and the migration describe the same schema."""
    disposable_postgres.upgrade("head")
    inspector = sa.inspect(disposable_postgres.engine)
    _assert_column_parity(inspector)
    _assert_constraint_parity(inspector)


def test_an_unknown_provenance_class_is_rejected(disposable_postgres) -> None:
    """A class outside the canonical vocabulary cannot be stored."""
    disposable_postgres.upgrade("head")
    _seed_campaign(disposable_postgres, "campaign-unknown-provenance")

    with pytest.raises(sa.exc.IntegrityError):
        with disposable_postgres.engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO campaign_continuation_authorities "
                    "(authority_id, campaign_id, envelope_json, "
                    " approved_by_actor_id, approved_at, approval_provenance) "
                    "VALUES ('cauth-unknown', 'campaign-unknown-provenance', "
                    "        CAST('{\"schema_version\": 1}' AS JSONB), "
                    "        'admin-1', now(), 'human_admin')"
                )
            )


def test_a_revoked_row_without_revocation_provenance_is_rejected(
    disposable_postgres,
) -> None:
    """A revoked row must carry its revocation provenance."""
    disposable_postgres.upgrade("head")
    _seed_campaign(disposable_postgres, "campaign-missing-revocation")

    with pytest.raises(sa.exc.IntegrityError):
        with disposable_postgres.engine.begin() as connection:
            connection.execute(
                sa.text(
                    "INSERT INTO campaign_continuation_authorities "
                    "(authority_id, campaign_id, envelope_json, "
                    " approved_by_actor_id, approved_at, revoked_by_actor_id, "
                    " revoked_at, revocation_reason, approval_provenance) "
                    "VALUES ('cauth-missing-revocation', "
                    "        'campaign-missing-revocation', "
                    "        CAST('{\"schema_version\": 1}' AS JSONB), "
                    "        'admin-1', now(), 'admin-1', now(), 'reason', "
                    "        'account_admin')"
                )
            )


# ---------------------------------------------------------------------------
# Existing-instance upgrade
# ---------------------------------------------------------------------------


def test_upgrade_classifies_historical_actions_as_legacy_without_rewriting(
    disposable_postgres,
) -> None:
    """Established historical actions become legacy; nothing else moves."""
    disposable_postgres.upgrade(PARENT_REVISION)

    inspector_before = sa.inspect(disposable_postgres.engine)
    columns_before = {
        c["name"] for c in inspector_before.get_columns(AUTHORITIES_TABLE)
    }
    assert "approval_provenance" not in columns_before
    assert "revocation_provenance" not in columns_before

    _seed_campaign(disposable_postgres, "campaign-historical")
    _seed_historical_authority(
        disposable_postgres,
        authority_id="cauth-unrevoked",
        campaign_id="campaign-historical",
        approved_by_actor_id="local",
        revoked=False,
    )
    _seed_historical_authority(
        disposable_postgres,
        authority_id="cauth-revoked",
        campaign_id="campaign-historical",
        approved_by_actor_id="local",
        revoked=True,
    )

    before = {
        row["authority_id"]: row
        for row in _authority_snapshot(disposable_postgres)
    }

    disposable_postgres.upgrade("head")

    after = {
        row["authority_id"]: row
        for row in _authority_snapshot(disposable_postgres)
    }
    assert set(after) == set(before)

    for authority_id, row in after.items():
        # Every pre-existing approval is legacy/unverified human provenance.
        assert row["approval_provenance"] == LEGACY_PROVENANCE

        # The actor id and every timestamp are exactly as they were.
        assert row["approved_by_actor_id"] == before[authority_id][
            "approved_by_actor_id"
        ]
        assert row["approved_at"] == before[authority_id]["approved_at"]
        assert row["created_at"] == before[authority_id]["created_at"]
        assert row["revoked_at"] == before[authority_id]["revoked_at"]
        assert row["revoked_by_actor_id"] == before[authority_id][
            "revoked_by_actor_id"
        ]
        assert row["revocation_reason"] == before[authority_id][
            "revocation_reason"
        ]

    # An unrevoked historical row carries no revocation provenance.
    assert after["cauth-unrevoked"]["revocation_provenance"] is None

    # A revoked historical row is classified as legacy too.
    assert after["cauth-revoked"]["revocation_provenance"] == LEGACY_PROVENANCE


def test_an_unrevoked_legacy_row_is_not_read_as_a_human_approval(
    disposable_postgres,
) -> None:
    """Matching actor bytes do not make a legacy row human approved.

    This is the collision ADR-105 exists to prevent: a historical row whose
    actor id happens to equal a canonical administrator's ``User.id`` must
    still classify as legacy, because classification is read from the
    durable discriminator and never inferred from the actor string.
    """
    disposable_postgres.upgrade(PARENT_REVISION)
    _seed_campaign(disposable_postgres, "campaign-collision")
    _seed_historical_authority(
        disposable_postgres,
        authority_id="cauth-collision",
        campaign_id="campaign-collision",
        approved_by_actor_id="admin-collision-id",
        revoked=False,
    )

    disposable_postgres.upgrade("head")

    provenance = disposable_postgres.scalar(
        "SELECT approval_provenance FROM campaign_continuation_authorities "
        "WHERE authority_id = 'cauth-collision'"
    )
    assert provenance == LEGACY_PROVENANCE
    assert provenance != "account_admin"


# ---------------------------------------------------------------------------
# Downgrade and re-upgrade
# ---------------------------------------------------------------------------


def test_downgrade_removes_the_provenance_columns_and_preserves_rows(
    disposable_postgres,
) -> None:
    """The downgrade is clean and reversible, and touches nothing else."""
    disposable_postgres.upgrade("head")
    _seed_campaign(disposable_postgres, "campaign-downgrade")
    _seed_historical_authority(
        disposable_postgres,
        authority_id="cauth-downgrade",
        campaign_id="campaign-downgrade",
        approved_by_actor_id="local",
        revoked=False,
    )

    before = {
        row["authority_id"]: row
        for row in _authority_snapshot(disposable_postgres)
    }

    disposable_postgres.downgrade(PARENT_REVISION)

    inspector = sa.inspect(disposable_postgres.engine)
    columns = {
        c["name"] for c in inspector.get_columns(AUTHORITIES_TABLE)
    }
    assert "approval_provenance" not in columns
    assert "revocation_provenance" not in columns

    # The row itself, and every column the migration does not own, survives.
    after = {
        row["authority_id"]: row
        for row in _authority_snapshot(disposable_postgres)
    }
    assert set(after) == set(before)
    for authority_id, row in after.items():
        assert row["approved_by_actor_id"] == before[authority_id][
            "approved_by_actor_id"
        ]
        assert row["approved_at"] == before[authority_id]["approved_at"]
        assert row["created_at"] == before[authority_id]["created_at"]


def test_re_upgrade_restores_the_provenance_schema(disposable_postgres) -> None:
    """A downgrade and re-upgrade cycle leaves the table usable again."""
    disposable_postgres.upgrade("head")
    _seed_campaign(disposable_postgres, "campaign-reupgrade")
    _seed_historical_authority(
        disposable_postgres,
        authority_id="cauth-reupgrade",
        campaign_id="campaign-reupgrade",
        approved_by_actor_id="local",
        revoked=False,
    )

    disposable_postgres.downgrade(PARENT_REVISION)
    disposable_postgres.upgrade("head")

    inspector = sa.inspect(disposable_postgres.engine)
    columns = {
        c["name"] for c in inspector.get_columns(AUTHORITIES_TABLE)
    }
    assert "approval_provenance" in columns
    assert "revocation_provenance" in columns

    # The row is still there and is still classified as legacy.
    rows = _authority_snapshot(disposable_postgres)
    assert len(rows) == 1
    assert rows[0]["authority_id"] == "cauth-reupgrade"
    assert rows[0]["approval_provenance"] == LEGACY_PROVENANCE
    assert rows[0]["approved_by_actor_id"] == "local"

    # A new row can now be written with an explicit class. It uses a second
    # Campaign because only one unrevoked authority may exist per Campaign.
    _seed_campaign(disposable_postgres, "campaign-fresh")
    with disposable_postgres.engine.begin() as connection:
        connection.execute(
            sa.text(
                "INSERT INTO campaign_continuation_authorities "
                "(authority_id, campaign_id, envelope_json, "
                " approved_by_actor_id, approved_at, approval_provenance) "
                "VALUES ('cauth-fresh', 'campaign-fresh', "
                "        CAST('{\"schema_version\": 1}' AS JSONB), "
                "        'local', now(), 'operator_deployment')"
            )
        )
    assert disposable_postgres.scalar(
        "SELECT approval_provenance FROM campaign_continuation_authorities "
        "WHERE authority_id = 'cauth-fresh'"
    ) == "operator_deployment"
