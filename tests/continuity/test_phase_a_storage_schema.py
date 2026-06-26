"""Schema tests for Continuity Phase A storage migration.

These tests verify that the Phase A continuity tables are correctly
represented in the migration and SQLAlchemy models, and that Phase B
tables, runtime imports, and write paths are not introduced.

No DB connection, Redis, Neo4j, provider, browser, or app startup is required.
"""

from __future__ import annotations

import ast
import inspect
import os

import pytest


# ── A. Metadata / model presence ────────────────────────────────────────────


def test_can_import_db_models():
    """Importing DB models must succeed."""
    from guardian.db import models

    assert models is not None


def test_four_phase_a_tables_in_metadata():
    """All four Phase A table names must be present in SQLAlchemy metadata."""
    from guardian.db.models import Base

    table_names = {table.name for table in Base.metadata.sorted_tables}
    assert "continuity_context_packets" in table_names
    assert "continuity_reality_states" in table_names
    assert "continuity_reality_commits" in table_names
    assert "continuity_state_packet_links" in table_names


def test_phase_b_tables_not_in_metadata():
    """Phase B table names must not be present."""
    from guardian.db.models import Base

    table_names = {table.name for table in Base.metadata.sorted_tables}
    assert "continuity_open_loops" not in table_names
    assert "continuity_rejected_paths" not in table_names
    assert "continuity_decisions" not in table_names
    assert "continuity_compiler_runs" not in table_names
    assert "continuity_project_pulse_snapshots" not in table_names


def test_required_columns_context_packets():
    """ContinuityContextPacket must have key envelope columns."""
    from guardian.db.models import ContinuityContextPacket

    cols = {c.name for c in ContinuityContextPacket.__table__.columns}
    required = {
        "id", "schema_version", "kind", "user_id", "source_system",
        "created_at", "summary", "payload_json", "provenance_json",
        "sensitivity", "retention", "deleted_at",
    }
    assert required <= cols, f"missing columns: {required - cols}"


def test_required_columns_reality_states():
    """ContinuityRealityState must have key columns."""
    from guardian.db.models import ContinuityRealityState

    cols = {c.name for c in ContinuityRealityState.__table__.columns}
    required = {
        "id", "schema_version", "scope", "compiled_at",
        "source_packet_ids_json", "state_json", "provenance_json",
        "confidence", "expires_or_decays_at", "created_at", "deleted_at",
    }
    assert required <= cols, f"missing columns: {required - cols}"


def test_required_columns_reality_commits():
    """ContinuityRealityCommit must have key columns."""
    from guardian.db.models import ContinuityRealityCommit

    cols = {c.name for c in ContinuityRealityCommit.__table__.columns}
    required = {
        "id", "schema_version", "scope", "kind", "trigger",
        "title", "summary", "source_packet_ids_json", "provenance_json",
        "previous_state_id", "new_state_id", "created_at", "deleted_at",
    }
    assert required <= cols, f"missing columns: {required - cols}"


def test_required_columns_state_packet_links():
    """ContinuityStatePacketLink must have key columns and uniqueness."""
    from guardian.db.models import ContinuityStatePacketLink

    cols = {c.name for c in ContinuityStatePacketLink.__table__.columns}
    required = {"id", "state_id", "packet_id", "relationship", "created_at"}
    assert required <= cols, f"missing columns: {required - cols}"

    import sqlalchemy as sa

    uq_found = any(
        isinstance(c, sa.UniqueConstraint)
        for c in ContinuityStatePacketLink.__table_args__
    )
    assert uq_found, "ContinuityStatePacketLink missing UniqueConstraint"


def test_models_import_does_not_pull_runtime():
    """DB models module's own source must not import runtime modules."""
    from guardian.db import models

    source = inspect.getsource(models)
    tree = ast.parse(source)

    runtime_smells = [
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "redis",
        "httpx",
        "requests",
    ]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for smell in runtime_smells:
                    assert alias.name != smell and not alias.name.startswith(
                        smell + "."
                    ), f"models imports runtime module: {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for smell in runtime_smells:
                    assert node.module != smell and not node.module.startswith(
                        smell + "."
                    ), f"models imports-from runtime module: {node.module!r}"


# ── B. Migration structural checks ──────────────────────────────────────────


def _find_migration_file() -> str:
    """Locate the Phase A migration file by revision id."""
    migrations_dir = os.path.join(
        os.path.dirname(__file__),
        "..", "..", "guardian", "db", "migrations", "versions",
    )
    migrations_dir = os.path.abspath(migrations_dir)
    for fname in os.listdir(migrations_dir):
        if fname.startswith("e8d1f2a3b4c5") and fname.endswith(".py"):
            return os.path.join(migrations_dir, fname)
    raise FileNotFoundError(
        "Phase A migration file not found (expected e8d1f2a3b4c5_*.py)"
    )


def test_migration_file_exists():
    path = _find_migration_file()
    assert os.path.isfile(path)


def test_migration_references_four_phase_a_tables():
    path = _find_migration_file()
    with open(path) as f:
        source = f.read()

    assert "continuity_context_packets" in source
    assert "continuity_reality_states" in source
    assert "continuity_reality_commits" in source
    assert "continuity_state_packet_links" in source


def test_migration_does_not_reference_phase_b_tables():
    path = _find_migration_file()
    with open(path) as f:
        source = f.read()

    assert "continuity_open_loops" not in source
    assert "continuity_rejected_paths" not in source
    assert "continuity_decisions" not in source
    assert "continuity_compiler_runs" not in source
    assert "continuity_project_pulse_snapshots" not in source


def test_migration_file_no_runtime_imports():
    """Migration file must not import runtime, route, worker, or provider modules."""
    path = _find_migration_file()
    with open(path) as f:
        source = f.read()

    forbidden = [
        "guardian.routes",
        "guardian.workers",
        "guardian.queue",
        "guardian.context",
        "guardian.vector",
        "guardian.core.ai_router",
        "redis",
        "requests",
        "httpx",
    ]

    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                for f in forbidden:
                    assert alias.name != f and not alias.name.startswith(
                        f + "."
                    ), f"migration imports {alias.name!r}"
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                for f in forbidden:
                    assert node.module != f and not node.module.startswith(
                        f + "."
                    ), f"migration imports-from {node.module!r}"


# ── C. Compile / import safety ──────────────────────────────────────────────


def test_can_import_contracts_and_compiler_with_models():
    """All continuity modules must coexist without runtime dependencies."""
    from guardian.continuity import contracts  # noqa: F401
    from guardian.continuity import compiler  # noqa: F401
    from guardian.db import models  # noqa: F401


# ── D. Schema field expectations ────────────────────────────────────────────


def test_context_packet_envelope_fields():
    """ContextPacket must carry kind, sensitivity, retention, scope, payload."""
    from guardian.db.models import ContinuityContextPacket

    cols = {c.name: c for c in ContinuityContextPacket.__table__.columns}
    assert not cols["kind"].nullable
    assert not cols["sensitivity"].nullable
    assert not cols["retention"].nullable
    assert not cols["payload_json"].nullable
    assert cols["deleted_at"].nullable  # soft-delete


def test_reality_state_json_fields():
    """RealityState must carry state_json, extracted JSON, confidence, decay."""
    from guardian.db.models import ContinuityRealityState

    cols = {c.name: c for c in ContinuityRealityState.__table__.columns}
    assert not cols["state_json"].nullable
    assert not cols["provenance_json"].nullable
    assert cols["confidence"].nullable  # NULL = not assessed
    assert cols["expires_or_decays_at"].nullable


def test_reality_commit_fields():
    """RealityCommit must carry kind, trigger, prev/new state, provenance."""
    from guardian.db.models import ContinuityRealityCommit

    cols = {c.name: c for c in ContinuityRealityCommit.__table__.columns}
    assert not cols["kind"].nullable
    assert not cols["trigger"].nullable
    assert not cols["title"].nullable
    assert cols["previous_state_id"].nullable
    assert cols["new_state_id"].nullable


def test_state_packet_link_uniqueness():
    """Link must enforce uniqueness on state_id, packet_id, relationship."""
    from guardian.db.models import ContinuityStatePacketLink

    import sqlalchemy as sa

    uq = None
    for constraint in ContinuityStatePacketLink.__table__.constraints:
        if isinstance(constraint, sa.UniqueConstraint):
            uq = constraint
            break

    assert uq is not None, "No UniqueConstraint on ContinuityStatePacketLink"
    uq_cols = {c.name for c in uq.columns}
    assert uq_cols == {"state_id", "packet_id", "relationship"}
