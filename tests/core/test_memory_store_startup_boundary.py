"""Regression: importing the supported Guardian dependency/application seam must
not create, schema-initialize, or mutate the legacy SQLite MemoryStore
(``guardian/memory/store.db``).

Provenance
----------
This regression locks the boundary removed by NX-1's first runtime blocker.
The pre-repair behavior — captured in
``docs/architecture/proofs/2026-08-21-current-main-supported-runtime-audit.md``
against audited SHA ``29b01148a774a2e8f0fcacc47f44adf9f36f1e91`` — was:

  importing ``guardian.core.dependencies`` (transitively via the supported
  Compose ``backend`` service image) executed an eager
  ``from guardian.memory.query_memory import memory_store as _memory_store``
  module-global ``memory_store = MemoryStore()`` construction in
  ``guardian/memory/query_memory.py``. That ``MemoryStore.__init__()`` ran
  ``_init_db()`` which performed ``CREATE TABLE IF NOT EXISTS memories(...)``
  and ``CREATE INDEX IF NOT EXISTS idx_timestamp...`` against
  ``sqlite3.connect('guardian/memory/store.db')``.

On the supported-Compose bind mount the schema-init step failed with:

  ``sqlite3.OperationalError: attempt to write a readonly database``

The Compose ``backend`` service exited ``(1)`` before binding port ``8888``.

Post-repair
-----------
The eager import in ``guardian/core/dependencies.py`` has been replaced with
a lazy, default-``None`` ``_memory_store`` slot, and the module-global
construction in ``guardian/memory/query_memory.py`` has been replaced
with a lazy ``get_memory_store()`` accessor. Importing the dependency
seam no longer touches the SQLite subsystem at all. This regression locks
that boundary for future contributors.

How the regression isolates from prior imports
------------------------------------------------
Each parametrized case spawns a fresh subprocess with ``python -E`` (so
PYTHON* env vars do not leak from the developer's shell) and a
controlled ``PYTHONPATH``. The subprocess's cwd is **an ephemeral
``tmp_path``** rather than the real worktree; ``sqlite3.connect`` with a
relative ``db_path`` like ``"guardian/memory/store.db"`` resolves
against cwd, so the database file would be created at
``tmp_path/guardian/memory/store.db`` if and only if the module
performs the eager schema-init.

Pre-repair this test would FAIL with a non-empty
``tmp_path/guardian/memory/store.db`` file.

Post-repair it must PASS with no ``tmp_path/guardian/memory/store.db``
created and no such side effect in the cwd.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]


def _clean_subprocess_env() -> dict[str, str]:
    """Build a strictly minimal subprocess environment.

    Strip PYTHONPATH and PYTHON* env vars so that no developer-shell state
    leaks into the fresh process. PYTHONPATH is set explicitly below.
    """
    env: dict[str, str] = {
        "PATH": os.environ.get("PATH", ""),
        "HOME": os.environ.get("HOME", ""),
        "LANG": "C.UTF-8",
        "LC_ALL": "C.UTF-8",
        "PYTHONIOENCODING": "utf-8",
    }
    env["PYTHONPATH"] = str(REPO_ROOT)
    return env


def _run_isolated_import_check(
    target_module: str,
    *,
    cwd: Path,
    timeout: int = 60,
) -> tuple[bool, bool, str]:
    """Spawn a fresh subprocess that imports ``target_module``.

    Returns ``(probe_report_db_created, store_db_exists, stderr)``.

    ``store_db_exists`` is the filesystem observation:
    ``cwd/guardian/memory/store.db`` exists at exit.
    ``probe_report_db_created`` echoes the in-probe sentinel probe.
    The two are checked independently and must agree that nothing was
    created.
    """
    assert not (cwd / "guardian" / "memory").exists(), (
        f"test precondition violated: {cwd}/guardian/memory must not pre-exist"
    )

    probe = (
        "import os, sys\n"
        f"sys.path.insert(0, {str(REPO_ROOT)!r})\n"
        f"__import__({target_module!r})\n"
        "created = os.path.exists('guardian/memory/store.db')\n"
        "size = os.path.getsize('guardian/memory/store.db') if created else 0\n"
        "sys.stdout.write(f'DB_CREATED={created}\\nDB_SIZE={size}\\n')\n"
        "sys.exit(0)\n"
    )
    result = subprocess.run(
        [sys.executable, "-E", "-c", probe],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        env=_clean_subprocess_env(),
        timeout=timeout,
    )
    last_lines = (result.stdout or "").strip().splitlines()[-2:]
    sentinels = {line.strip() for line in last_lines}
    db_created = "DB_CREATED=True" in sentinels
    store_db_exists_on_disk = (cwd / "guardian" / "memory" / "store.db").exists()
    return db_created, store_db_exists_on_disk, (result.stderr or "").strip()


@pytest.mark.parametrize(
    "target_module",
    [
        # The repaired seam — was the failing import in NX-1.
        "guardian.core.dependencies",
        # The chain nexus.
        "guardian.connectors.google",
        # The application entry.
        "guardian.guardian_api",
    ],
)
def test_import_seam_does_not_create_legacy_sqlite_store_db(
    target_module: str,
    tmp_path: Path,
) -> None:
    """Importing the supported Guardian dependency/application seam must
    not create ``guardian/memory/store.db``.

    The test executes the import in a **fresh subprocess** with:

      * an empty ``cwd`` (verified by the precondition below);
      * a minimal controlled environment (no inherited PYTHONPATH);
      * an explicit ``PYTHONPATH`` containing only the worktree root
        so the import resolution is reproducible.

    The module under test uses ``sqlite3.connect('guardian/memory/store.db')``
    which is a relative path; when the subprocess has cwd=tmp_path, the
    target file would be ``tmp_path/guardian/memory/store.db``. If the
    import side-effect fails the test, ``tmp_path/guardian/memory/store.db``
    exists.

    A passing test is one where neither the in-process sentinel probe nor
    the on-disk observation report a created store.
    """

    # Precondition: no pre-existing ``guardian/memory`` directory under
    # the subprocess cwd. This guarantees the test starts from a clean
    # filesystem state at the cwd level, even if the host worktree's
    # ``guardian/memory/store.db`` already exists (the host artifact is
    # unrelated to the subprocess cwd's filesystem).
    subprocess_cwd = tmp_path
    assert not (subprocess_cwd / "guardian" / "memory").exists()

    db_created, store_db_exists, stderr = _run_isolated_import_check(
        target_module, cwd=subprocess_cwd
    )
    if stderr:
        sys.stderr.write(
            f"[{target_module}] subprocess stderr: {stderr[:2000]}\n"
        )

    assert not store_db_exists, (
        f"importing {target_module} created "
        f"{subprocess_cwd}/guardian/memory/store.db; "
        "the import-time eager-MemoryStore repair was not honored"
    )
    assert not db_created, (
        f"in-probe sentinel for {target_module} reported DB_CREATED=True; "
        "the import-time eager-MemoryStore repair was not honored"
    )


def test_explicit_memory_store_construction_still_works(tmp_path: Path) -> None:
    """The repair must NOT break direct explicit ``MemoryStore(temp_path)``
    construction. This guards spec §3 "Preserve direct MemoryStore behavior"
    and prevents accidental over-removal.

    The test is hermetic — it imports ``MemoryStore`` directly from
    ``guardian.memory.query_memory`` (not via ``dependencies._memory_store``),
    constructs the store against an empty ``tmp_path`` directory, and
    verifies the schema-init DDL ran and that ``_init_db()`` is
    idempotent (CREATE TABLE / CREATE INDEX IF NOT EXISTS).

    This test deliberately avoids ``query_by_time`` / ``query_by_tags``
    / ``query_by_content`` because those are decorated with
    ``@lru_cache_safe(..., expire=...)`` whose ``hash_args`` helper is
    sensitive to bound-MemoryStore ``self``-args (a pre-existing
    unrelated fragility); that fragility is not in scope for this
    boundary regression. The MemoryStore class itself is the subject of
    this test, so we exercise its schema-init contract directly.
    """

    isolated_db = tmp_path / "isolated-store.db"
    probe = (
        "from pathlib import Path\n"
        f"db = Path({str(isolated_db)!r})\n"
        "from guardian.memory.query_memory import MemoryStore\n"
        "store = MemoryStore(str(db))\n"
        "assert db.exists(), 'explicit MemoryStore(temp_path) must create the DB file'\n"
        "assert db.stat().st_size > 0, 'schema-init must produce a non-empty DB'\n"
        # Idempotency: calling _init_db twice must not raise.
        "store._init_db()\n"
        "print('MEMORYSTORE_EXPLICIT_OK')\n"
    )
    result = subprocess.run(
        [sys.executable, "-E", "-c", probe],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        env=_clean_subprocess_env(),
        timeout=60,
    )
    assert result.returncode == 0, (
        f"explicit MemoryStore construction failed: stdout={result.stdout!r} "
        f"stderr={result.stderr!r}"
    )
    assert "MEMORYSTORE_EXPLICIT_OK" in result.stdout
    assert isolated_db.exists()
