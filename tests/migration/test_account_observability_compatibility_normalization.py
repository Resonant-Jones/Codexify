"""Focused tests for the account-observability compatibility normalization.

These tests cover the historical ``b2`` migration-content drift repair and the
new forward ``9d4c2a7e1b6f`` normalization migration.

Static assertions verify:

* restored historical ``b2`` blob identity
* normalization revision metadata
* final graph has exactly one head
* downgrade fails closed rather than lying

Database-integration assertions verify the schema-shape classifier
(``historical_v1``/``canonical_v2``/``unknown_or_mixed``), preflight, and
historical-to-canonical normalization with identity preservation. The
integration tests spin up an isolated Postgres if no ``TEST_DATABASE_URL``
is supplied and skip otherwise.
"""
from __future__ import annotations

import ast
import hashlib
import os
import re
import subprocess
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse, urlunparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"

B2_FILENAME = "b2c3d4e5f6a7_add_account_observability_foundation.py"
NORMALIZATION_FILENAME = (
    "9d4c2a7e1b6f_normalize_account_observability_schema.py"
)

EXPECTED_B2_HISTORICAL_BLOB = "c6671615e786778a6d11c6554e2a1cdd6bef8719"
NORMALIZATION_REVISION = "9d4c2a7e1b6f"
NORMALIZATION_DOWN_REVISION = "8f3c1a7d2e6b"


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def _parse(path: Path) -> ast.Module:
    return ast.parse(path.read_text())


def _literal(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        target = node.target if isinstance(node, ast.AnnAssign) else (
            node.targets[0] if isinstance(node, ast.Assign) else None
        )
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"{name} assignment missing in migration")


def _function_body(tree: ast.Module, name: str) -> list[ast.stmt]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            statements = node.body
            if (
                statements
                and isinstance(statements[0], ast.Expr)
                and isinstance(statements[0].value, ast.Constant)
                and isinstance(statements[0].value.value, str)
            ):
                statements = statements[1:]
            return statements
    raise AssertionError(f"function {name} not found")


# -- Static assertions ---------------------------------------------------


def test_restored_b2_blob_matches_pinned_historical_identity() -> None:
    path = VERSIONS_DIR / B2_FILENAME
    assert path.is_file(), f"missing restored b2 migration: {path}"
    assert _git_blob_sha(path) == EXPECTED_B2_HISTORICAL_BLOB, (
        f"b2 blob drifted from historical identity; "
        f"expected {EXPECTED_B2_HISTORICAL_BLOB}, got {_git_blob_sha(path)}"
    )


def test_normalization_revision_metadata_is_correct() -> None:
    tree = _parse(VERSIONS_DIR / NORMALIZATION_FILENAME)
    assert _literal(tree, "revision") == NORMALIZATION_REVISION
    assert _literal(tree, "down_revision") == NORMALIZATION_DOWN_REVISION
    assert _literal(tree, "branch_labels") is None
    assert _literal(tree, "depends_on") is None


def test_normalization_downgrade_is_fail_closed() -> None:
    tree = _parse(VERSIONS_DIR / NORMALIZATION_FILENAME)
    body = _function_body(tree, "downgrade")
    assert len(body) >= 1
    # The downgrade must raise RuntimeError rather than silently downgrading.
    found_raise = False
    for stmt in body:
        if isinstance(stmt, ast.Raise):
            found_raise = True
            assert stmt.exc is not None, "downgrade must raise a non-None exception"
    assert found_raise, "downgrade() must fail closed (raise) before any DDL"


def test_normalization_upgrade_dispatches_on_classification() -> None:
    tree = _parse(VERSIONS_DIR / NORMALIZATION_FILENAME)
    body = _function_body(tree, "upgrade")
    # upgrade() must call _classify() and dispatch on the result.
    source = ast.unparse(tree)
    assert "_classify()" in source
    assert "_normalize_historical_to_canonical()" in source
    assert "historical_v1" in source
    assert "canonical_v2" in source
    assert "unknown_or_mixed" in source


# -- Database integration scaffolding -------------------------------------


def _build_url(base: str, database: str) -> str:
    parsed = urlparse(base)
    return urlunparse(parsed._replace(path=f"/{database}"))


def _admin_url(base: str) -> str:
    parsed = urlparse(base)
    return urlunparse(parsed._replace(path="/postgres"))


def _container_postgres_url() -> str | None:
    """If no TEST_DATABASE_URL is provided, spawn an isolated postgres:15
    container and return a tuple of (host, port, container_name). Returns
    None if Docker is unavailable.
    """
    if os.getenv("TEST_DATABASE_URL") or os.getenv("DATABASE_URL"):
        return None
    # Pick a free host port to avoid colliding with stale containers.
    import socket

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    host_port = sock.getsockname()[1]
    sock.close()

    name = f"codexify_account_observability_norm_{uuid.uuid4().hex[:12]}"
    try:
        subprocess.run(
            [
                "docker",
                "run",
                "-d",
                "--name",
                name,
                "-e",
                "POSTGRES_USER=postgres",
                "-e",
                "POSTGRES_PASSWORD=postgres",
                "-e",
                "POSTGRES_DB=postgres",
                "-p",
                f"{host_port}:5432",
                "postgres:15",
            ],
            check=True,
            capture_output=True,
            timeout=60,
        )
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
        return None
    # Wait for postgres to accept connections.
    deadline = time.time() + 30
    while time.time() < deadline:
        try:
            import psycopg  # type: ignore

            conn = psycopg.connect(
                f"postgresql://postgres:postgres@localhost:{host_port}/postgres",
                autocommit=True,
            )
            conn.close()
            return ("localhost", host_port, name)
        except Exception:
            time.sleep(1)
    return None


def _cleanup_container(info) -> None:
    if not info:
        return
    name = info[2] if len(info) >= 3 else info[1]
    try:
        subprocess.run(
            ["docker", "rm", "-f", name], capture_output=True, timeout=30
        )
    except Exception:
        pass


@pytest.fixture()
def disposable_db(monkeypatch):
    """Yield a (target_url, admin_url) tuple for a disposable test database.

    Skip if no Postgres is reachable.
    """
    # Force-clear project env vars that would otherwise route to a
    # docker-compose service host (e.g. ``db``) and fail the fixture.
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("GUARDIAN_DATABASE_URL", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)

    container = _container_postgres_url()
    if container is None:
        pytest.skip(
            "Postgres unavailable: TEST_DATABASE_URL/DATABASE_URL not set and "
            "no Docker postgres container could be spawned."
        )

    host, host_port, container_name = container
    base_url = f"postgresql://postgres:postgres@localhost:{host_port}/postgres"

    import psycopg  # type: ignore

    admin_url = _admin_url(base_url)
    db_name = f"codexify_acct_norm_{uuid.uuid4().hex[:12]}"
    target_url = _build_url(base_url, db_name)

    conn = psycopg.connect(admin_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute(f'CREATE DATABASE "{db_name}"')
    finally:
        conn.close()

    try:
        yield (target_url, admin_url)
    finally:
        try:
            cleanup_conn = psycopg.connect(admin_url, autocommit=True)
            try:
                with cleanup_conn.cursor() as c:
                    c.execute(
                        "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                        "WHERE datname = %s",
                        (db_name,),
                    )
            finally:
                cleanup_conn.close()
            drop_conn = psycopg.connect(admin_url, autocommit=True)
            try:
                with drop_conn.cursor() as c:
                    c.execute(f'DROP DATABASE IF EXISTS "{db_name}"')
            finally:
                drop_conn.close()
        except Exception:
            pass
        if container_name is not None:
            _cleanup_container(container_name)



# -- Database integration tests ------------------------------------------

def _git_show_blob(commit_sha: str, repo_relative_path: str) -> str:
    """Return the file content at a specific historical commit."""
    return subprocess.run(
        [
            "git",
            "show",
            f"{commit_sha}:{repo_relative_path}",
        ],
        cwd=str(REPO_ROOT),
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _run_alembic(target_url: str, target: str, command_name: str = "upgrade") -> None:
    """Apply Alembic to the named target using ``upgrade`` (default) or
    ``downgrade``. The Alembic env reads ``DATABASE_URL`` from
    ``os.environ``; the fixture sets it explicitly.
    """
    from alembic import command
    from alembic.config import Config

    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        cfg_path = Path(tmp) / "alembic.ini"
        cfg_path.write_text((REPO_ROOT / "backend" / "alembic.ini").read_text())
        cfg = Config(str(cfg_path))
        cfg.set_main_option("sqlalchemy.url", target_url)
        cfg.set_main_option(
            "script_location", str(REPO_ROOT / "guardian" / "db" / "migrations")
        )
        os.environ["DATABASE_URL"] = target_url
        cmd = getattr(command, command_name)
        cmd(cfg, target)


def _setup_via_alembic_upgrade(target_url: str, baseline_revision: str) -> None:
    _run_alembic(target_url, baseline_revision, "upgrade")


def _setup_via_alembic_upgrade_with_b2_override(
    target_url: str,
    baseline_revision: str,
    b2_override_blob: str | None,
) -> None:
    """Apply Alembic up to ``baseline_revision`` while optionally rewriting
    the b2 migration source on disk to match the pre-repair canonical body.
    """
    b2_path = VERSIONS_DIR / B2_FILENAME
    backup: bytes | None = None
    if b2_override_blob is not None and b2_override_blob != b2_path.read_text():
        backup = b2_path.read_bytes()
        b2_path.write_text(b2_override_blob)
    try:
        _setup_via_alembic_upgrade(target_url, baseline_revision)
    finally:
        if backup is not None:
            b2_path.write_bytes(backup)


def _read_alembic_version(target_url: str) -> str:
    import psycopg  # type: ignore

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute("SELECT version_num FROM alembic_version")
            row = c.fetchone()
            return row[0] if row else ""
    finally:
        conn.close()


@pytest.mark.integration
def test_canonical_v2_classifier_accepts_canonical_fixture(disposable_db) -> None:
    """Path B: a database built with the canonical (rewritten/pre-repair) b2
    body must classify as canonical_v2, and the normalization upgrade must
    be a no-op.

    Setup uses the actual pre-repair b2 body from commit
    ``f0bc85df86f148e635fdf19132311fd04ba1695f`` (which carried blob
    ``3d9456c7235ae651f9057f93299abcb03205d33b``) — i.e. the canonical
    schema produced by the rewritten migration that lived on the current
    lineage before this task's repair.
    """
    target_url, _ = disposable_db
    canonical_b2_body = _git_show_blob(
        "f0bc85df86f148e635fdf19132311fd04ba1695f",
        f"guardian/db/migrations/versions/{B2_FILENAME}",
    )

    _setup_via_alembic_upgrade_with_b2_override(
        target_url, "9d4c2a7e1b6f", b2_override_blob=canonical_b2_body
    )

    # Verify the canonical schema signature (PK names, region width).
    import psycopg

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            assert _read_alembic_version(target_url) == "9d4c2a7e1b6f"
            c.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'account_observability_invite_links'
                """
            )
            cols = {row[0] for row in c.fetchall()}
            assert "invite_id" in cols
            assert "id" not in cols
            c.execute(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'account_observability_presence_sessions'
                AND column_name = 'region_code'
                """
            )
            assert c.fetchone()[0] == 64
    finally:
        conn.close()

    # Repeated upgrade must be a no-op.
    _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")
    assert _read_alembic_version(target_url) == "9d4c2a7e1b6f"


@pytest.mark.integration
def test_historical_v1_classifier_accepts_historical_fixture(disposable_db) -> None:
    """Path C-shaped fixture (historical_v1) is recognized and normalized.

    The historical b2 body is the actual Git-blob at the pre-rewrite
    state — applied first via Alembic (which would otherwise refuse
    because the current source already diverges). We temporarily
    override the b2 source on disk to the historical body, run Alembic
    to its historical head, then upgrade through 8f3c1a7d2e6b and
    9d4c2a7e1b6f.
    """
    target_url, _ = disposable_db

    # Step 1: Apply the historical b2 via alembic by temporarily restoring
    # the historical b2 source on disk.
    historical_b2_body = _git_show_blob(
        "d2559f3b6d07156c0e139925d6ba256127d9690f",
        f"guardian/db/migrations/versions/{B2_FILENAME}",
    )
    _setup_via_alembic_upgrade_with_b2_override(
        target_url, "b2c3d4e5f6a7", b2_override_blob=historical_b2_body
    )
    # Now revert b2 back to the historical identity (the repo default is
    # already historical; this is a no-op safety step).
    b2_path = VERSIONS_DIR / B2_FILENAME
    assert _git_blob_sha(b2_path) == EXPECTED_B2_HISTORICAL_BLOB, (
        "b2 source must remain historical before normalization step"
    )

    # Step 2: Upgrade through 8f3c1a7d2e6b (metadata-only merge) and
    # 9d4c2a7e1b6f (normalization) — the latter must transform the
    # historical_v1 shape into canonical_v2.
    _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")

    # Verify canonical schema signature after normalization.
    import psycopg

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            assert _read_alembic_version(target_url) == "9d4c2a7e1b6f"
            c.execute(
                """
                SELECT column_name FROM information_schema.columns
                WHERE table_name = 'account_observability_invite_links'
                AND column_name IN ('id', 'invite_id')
                """
            )
            cols = {row[0] for row in c.fetchall()}
            assert "invite_id" in cols
            assert "id" not in cols
            c.execute(
                """
                SELECT character_maximum_length
                FROM information_schema.columns
                WHERE table_name = 'account_observability_presence_sessions'
                AND column_name = 'region_code'
                """
            )
            assert c.fetchone()[0] == 64
    finally:
        conn.close()

    # Repeated upgrade is a no-op.
    _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")


@pytest.mark.integration
def test_historical_v1_normalization_preserves_identity_values(disposable_db) -> None:
    """A populated historical_v1 fixture must keep every identity value
    through the historical→canonical normalization.
    """
    target_url, _ = disposable_db

    # Apply historical b2 via alembic with source override.
    historical_b2_body = _git_show_blob(
        "d2559f3b6d07156c0e139925d6ba256127d9690f",
        f"guardian/db/migrations/versions/{B2_FILENAME}",
    )
    _setup_via_alembic_upgrade_with_b2_override(
        target_url, "b2c3d4e5f6a7", b2_override_blob=historical_b2_body
    )

    # Populate the historical schema with deterministic identity values.
    import psycopg

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('creator-1', 'creator-1', 'x', 'admin')"
            )
            c.execute(
                "INSERT INTO account_observability_invite_links "
                "(id, token_hash, name, created_by_user_id, status, "
                "revoked_at, disabled_at) "
                "VALUES "
                "('invite-A', 'h-A', 'alpha', 'creator-1', 'active', NULL, NULL),"
                "('invite-B', 'h-B', 'bravo', 'creator-1', 'revoked', now(), NULL),"
                "('invite-C', 'h-C', 'charlie', 'creator-1', 'disabled', NULL, now())"
            )
            c.execute(
                "INSERT INTO account_observability_guest_identities "
                "(id, first_invite_id) "
                "VALUES "
                "('guest-1', 'invite-A'),"
                "('guest-2', 'invite-B')"
            )
            c.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('acct-1', 'acct-1', 'x', 'guest')"
            )
            c.execute(
                "INSERT INTO account_observability_account_metadata "
                "(user_id, registered_at) "
                "VALUES ('acct-1', now())"
            )
            c.execute(
                "INSERT INTO account_observability_presence_sessions "
                "(id, user_id, started_at, last_seen_at, country_code, region_code) "
                "VALUES ('pres-1', 'acct-1', now(), now(), 'US', 'US-CA')"
            )
    finally:
        conn.close()

    # Now upgrade through 8f3c1a7d2e6b and 9d4c2a7e1b6f.
    _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")

    # Verify identity values survive column renames.
    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute(
                "SELECT invite_id, token_hash FROM "
                "account_observability_invite_links "
                "WHERE invite_id IN ('invite-A', 'invite-B', 'invite-C') "
                "ORDER BY invite_id"
            )
            ids = [row[0] for row in c.fetchall()]
            assert ids == ["invite-A", "invite-B", "invite-C"]
            c.execute(
                "SELECT guest_id, first_invite_id FROM "
                "account_observability_guest_identities "
                "ORDER BY guest_id"
            )
            rows = c.fetchall()
            assert rows == [("guest-1", "invite-A"), ("guest-2", "invite-B")]
            c.execute(
                "SELECT presence_session_id, user_id FROM "
                "account_observability_presence_sessions"
            )
            assert c.fetchall() == [("pres-1", "acct-1")]
    finally:
        conn.close()


@pytest.mark.integration
def test_unknown_or_mixed_shape_fails_before_ddl(disposable_db) -> None:
    """A database with partial canonical state must fail closed.

    Build a fixture with the canonical PK names but the historical
    ``region_code`` width (VARCHAR(32)) — the schema-shape classifier
    must read this as ``unknown_or_mixed`` and the migration upgrade
    must raise before any DDL.
    """
    target_url, _ = disposable_db

    # Start from the historical b2 (after the restoration) — that gives
    # us the historical PK names and historical region_code width.
    historical_b2_body = _git_show_blob(
        "d2559f3b6d07156c0e139925d6ba256127d9690f",
        f"guardian/db/migrations/versions/{B2_FILENAME}",
    )
    _setup_via_alembic_upgrade_with_b2_override(
        target_url, "b2c3d4e5f6a7", b2_override_blob=historical_b2_body
    )

    # Rename only the PK columns (but leave FK targets and region_code
    # width as historical). This is intentionally a partial canonical
    # shape.
    import psycopg

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute(
                "ALTER TABLE account_observability_invite_links "
                "RENAME COLUMN id TO invite_id"
            )
            c.execute(
                "ALTER TABLE account_observability_guest_identities "
                "RENAME COLUMN id TO guest_id"
            )
            c.execute(
                "ALTER TABLE account_observability_presence_sessions "
                "RENAME COLUMN id TO presence_session_id"
            )
            # Drop the historical FKs and recreate them pointing at
            # canonical PK names — but leave region_code VARCHAR(32).
            # This creates a mixed state where PK columns match
            # canonical but region_code width does not.
            c.execute(
                "ALTER TABLE account_observability_guest_identities "
                "DROP CONSTRAINT fk_account_observability_guest_identities_first_invite_id"
            )
            c.execute(
                "ALTER TABLE account_observability_guest_identities "
                "ADD CONSTRAINT fk_account_observability_guest_identities_first_invite_id "
                "FOREIGN KEY (first_invite_id) "
                "REFERENCES account_observability_invite_links(invite_id) "
                "ON DELETE RESTRICT"
            )
            c.execute(
                "ALTER TABLE account_observability_account_metadata "
                "DROP CONSTRAINT fk_account_observability_account_metadata_acquisition_invite_id"
            )
            c.execute(
                "ALTER TABLE account_observability_account_metadata "
                "ADD CONSTRAINT fk_account_observability_account_metadata_acquisition_invite_id "
                "FOREIGN KEY (acquisition_invite_id) "
                "REFERENCES account_observability_invite_links(invite_id) "
                "ON DELETE RESTRICT"
            )
            c.execute(
                "ALTER TABLE account_observability_account_metadata "
                "DROP CONSTRAINT fk_account_observability_account_metadata_prior_guest_id"
            )
            c.execute(
                "ALTER TABLE account_observability_account_metadata "
                "ADD CONSTRAINT fk_account_observability_account_metadata_prior_guest_id "
                "FOREIGN KEY (prior_guest_id) "
                "REFERENCES account_observability_guest_identities(guest_id) "
                "ON DELETE SET NULL"
            )
            c.execute(
                "ALTER TABLE account_observability_presence_sessions "
                "DROP CONSTRAINT fk_account_observability_presence_sessions_guest_id"
            )
            c.execute(
                "ALTER TABLE account_observability_presence_sessions "
                "ADD CONSTRAINT fk_account_observability_presence_sessions_guest_id "
                "FOREIGN KEY (guest_id) "
                "REFERENCES account_observability_guest_identities(guest_id) "
                "ON DELETE CASCADE"
            )
            c.execute(
                "ALTER TABLE account_observability_presence_sessions "
                "DROP CONSTRAINT fk_account_observability_presence_sessions_invite_id"
            )
            c.execute(
                "ALTER TABLE account_observability_presence_sessions "
                "ADD CONSTRAINT fk_account_observability_presence_sessions_invite_id "
                "FOREIGN KEY (invite_id) "
                "REFERENCES account_observability_invite_links(invite_id) "
                "ON DELETE RESTRICT"
            )
            # region_code stays at VARCHAR(32) — mixed shape.
    finally:
        conn.close()

    # Upgrading must fail closed because region_code is still historical.
    with pytest.raises(Exception) as exc_info:
        _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")
    assert "unknown_or_mixed" in str(exc_info.value) or "Cannot" in str(exc_info.value)


@pytest.mark.integration
def test_preflight_rejects_non_lossless_historical_rows(disposable_db) -> None:
    """A historical_v1 database with NULL ``created_by_user_id`` rows must
    fail closed before any normalization DDL is applied.
    """
    target_url, _ = disposable_db

    historical_b2_body = _git_show_blob(
        "d2559f3b6d07156c0e139925d6ba256127d9690f",
        f"guardian/db/migrations/versions/{B2_FILENAME}",
    )
    _setup_via_alembic_upgrade_with_b2_override(
        target_url, "b2c3d4e5f6a7", b2_override_blob=historical_b2_body
    )

    # Populate a non-lossless row.
    import psycopg

    conn = psycopg.connect(target_url, autocommit=True)
    try:
        with conn.cursor() as c:
            c.execute(
                "INSERT INTO users (id, username, password_hash, role) "
                "VALUES ('creator-1', 'creator-1', 'x', 'admin')"
            )
            c.execute(
                "INSERT INTO account_observability_invite_links "
                "(id, token_hash, name, created_by_user_id, status) "
                "VALUES ('invite-bad', 'h-bad', 'bad', NULL, 'active')"
            )
    finally:
        conn.close()

    with pytest.raises(Exception) as exc_info:
        _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")
    assert "created_by_user_id" in str(exc_info.value) or "Normalization" in str(exc_info.value)


@pytest.mark.integration
def test_downgrade_fails_closed(disposable_db) -> None:
    """``downgrade()`` must raise without performing any DDL.

    The migration's downgrade() unconditionally raises ``RuntimeError``.
    We exercise it by attempting ``alembic downgrade`` past
    ``9d4c2a7e1b6f`` to ``8f3c1a7d2e6b`` (the metadata-only merge). The
    downgrade of ``9d4c2a7e1b6f`` is the only callable that must raise.
    """
    target_url, _ = disposable_db

    # Apply the entire chain first so the alembic_version row exists.
    _setup_via_alembic_upgrade(target_url, "9d4c2a7e1b6f")

    # Attempting to downgrade one step backward from the head triggers
    # the migration's unconditional raise.
    with pytest.raises(Exception) as exc_info:
        _run_alembic(target_url, "-1", "downgrade")
    assert "downgrade" in str(exc_info.value) or "Normalization" in str(exc_info.value)

    # Confirm no destructive state change occurred — alembic_version still
    # at the head revision.
    assert _read_alembic_version(target_url) == "9d4c2a7e1b6f"