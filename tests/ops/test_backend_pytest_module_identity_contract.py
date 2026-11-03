"""Contract: backend test modules resolve to distinct Python module identities.

`tests/db/` and `tests/workers/` both contain `test_chat_worker_terminal_authority.py`
and `test_chat_worker_terminal_cleanup.py`. Neither directory was an explicit
Python package, so pytest derived the same top-level module name for both
copies and refused to collect the second one:

    import file mismatch:
    imported module 'test_chat_worker_terminal_authority' has this __file__
    attribute: .../tests/db/test_chat_worker_terminal_authority.py
    which is not the same as the test file we want to collect:
    .../tests/workers/test_chat_worker_terminal_authority.py

The colliding copies were therefore *not* collected, which made the backend
suite report a smaller collection than the repository actually contains.

These tests assert the identity pytest really uses -- the resolved module
object, its dotted name, and the physical file it came from -- rather than the
presence of a marker file. Everything here is import-time and collection-time
only: no Guardian service, database, Redis instance, or cloud model is
contacted.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]

DB_PACKAGE = ROOT / "tests" / "db"
WORKERS_PACKAGE = ROOT / "tests" / "workers"

TERMINAL_AUTHORITY = "test_chat_worker_terminal_authority"
TERMINAL_CLEANUP = "test_chat_worker_terminal_cleanup"

# The four modules that previously collided, with the physical file each must
# resolve to. The dotted suffix is what the module identity must carry: the
# repository root is itself a package (it has an `__init__.py`), so pytest
# prefixes the identity with the checkout directory name, which differs
# between a local worktree and CI.
EXPECTED_MODULES = {
    f"tests.db.{TERMINAL_AUTHORITY}": DB_PACKAGE / f"{TERMINAL_AUTHORITY}.py",
    f"tests.workers.{TERMINAL_AUTHORITY}": WORKERS_PACKAGE / f"{TERMINAL_AUTHORITY}.py",
    f"tests.db.{TERMINAL_CLEANUP}": DB_PACKAGE / f"{TERMINAL_CLEANUP}.py",
    f"tests.workers.{TERMINAL_CLEANUP}": WORKERS_PACKAGE / f"{TERMINAL_CLEANUP}.py",
}

# Helpers the colliding modules import across directories. They must keep
# working unchanged.
CROSS_DIRECTORY_HELPERS = (
    "tests.db.test_chat_completion_attempt_migration",
    "tests.workers.test_chat_worker_streaming_chunks",
)

COLLECT_TARGETS = [
    str(path)
    for path in (
        DB_PACKAGE / f"{TERMINAL_AUTHORITY}.py",
        WORKERS_PACKAGE / f"{TERMINAL_AUTHORITY}.py",
        DB_PACKAGE / f"{TERMINAL_CLEANUP}.py",
        WORKERS_PACKAGE / f"{TERMINAL_CLEANUP}.py",
    )
]

# Runs in a clean interpreter so the resolution under test is this
# repository's, not whatever `tests` package the surrounding session imported.
IMPORT_PROBE = """
import importlib
import importlib.util
import json
import os
import sys

sys.path.insert(0, os.getcwd())

report = {"packages": {}, "modules": {}}

for name in ("tests.db", "tests.workers"):
    spec = importlib.util.find_spec(name)
    report["packages"][name] = {
        "origin": spec.origin,
        "search_locations": [str(entry) for entry in spec.submodule_search_locations],
    }

for name in %(module_names)s:
    module = importlib.import_module(name)
    report["modules"][name] = {
        "file": os.path.realpath(module.__file__),
        "name": module.__name__,
    }

print(json.dumps(report))
"""

# Records the module object pytest assigned to each collected item.
COLLECTION_PLUGIN = """
import json
import os


def pytest_collection_finish(session):
    resolved = []
    for item in session.items:
        module = getattr(item, "module", None)
        if module is None:
            continue
        resolved.append(
            {"name": module.__name__, "file": os.path.realpath(module.__file__)}
        )
    with open(os.environ["MODULE_IDENTITY_OUT"], "w", encoding="utf-8") as handle:
        json.dump(resolved, handle)
"""


def _run_python(source: str, env: dict[str, str] | None = None) -> dict:
    environment = os.environ.copy()
    environment.update(env or {})
    result = subprocess.run(
        [sys.executable, "-c", source],
        cwd=str(ROOT),
        env=environment,
        text=True,
        capture_output=True,
    )
    assert result.returncode == 0, f"probe failed:\n{result.stdout}\n{result.stderr}"
    return json.loads(result.stdout.strip().splitlines()[-1])


def _import_probe() -> dict:
    """Resolve the packages and modules in a clean interpreter.

    `json.dumps` produces the list literal for the probe: `%` formatting
    re-reprs list elements, which would embed the quotes in the module names.
    """
    names = list(EXPECTED_MODULES) + list(CROSS_DIRECTORY_HELPERS)
    return _run_python(IMPORT_PROBE % {"module_names": json.dumps(names)})


def test_db_and_workers_resolve_as_separate_regular_packages() -> None:
    report = _import_probe()

    db = report["packages"]["tests.db"]
    workers = report["packages"]["tests.workers"]

    # A namespace portion has no origin; a regular package does. pytest only
    # derives a dotted module identity for a regular package chain.
    assert db["origin"] is not None, "tests.db must resolve as a regular package"
    assert workers["origin"] is not None, "tests.workers must resolve as a regular package"

    assert db["search_locations"] == [str(DB_PACKAGE)]
    assert workers["search_locations"] == [str(WORKERS_PACKAGE)]
    assert db["search_locations"] != workers["search_locations"]


def test_colliding_modules_resolve_to_distinct_import_identities() -> None:
    report = _import_probe()

    modules = report["modules"]
    for name, expected_path in EXPECTED_MODULES.items():
        assert name in modules, f"{name} must be importable under its own identity"
        assert modules[name]["name"] == name
        assert modules[name]["file"] == os.path.realpath(expected_path), (
            f"{name} must resolve to {expected_path}, not {modules[name]['file']}"
        )

    # No duplicate module may be silently substituted for another.
    resolved_files = [modules[name]["file"] for name in EXPECTED_MODULES]
    assert len(set(resolved_files)) == len(EXPECTED_MODULES)
    assert len(set(EXPECTED_MODULES)) == 4


def test_cross_directory_helper_imports_remain_functional() -> None:
    report = _import_probe()

    for name in CROSS_DIRECTORY_HELPERS:
        assert name in report["modules"], f"{name} must remain importable"
        assert report["modules"][name]["name"] == name


def test_pytest_collects_all_four_modules_under_distinct_identities(tmp_path: Path) -> None:
    plugin_dir = tmp_path / "plugins"
    plugin_dir.mkdir()
    (plugin_dir / "module_identity_probe.py").write_text(COLLECTION_PLUGIN, encoding="utf-8")

    report_path = tmp_path / "module_identity.json"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(plugin_dir)
    environment["MODULE_IDENTITY_OUT"] = str(report_path)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "-q",
            "-p",
            "module_identity_probe",
            *COLLECT_TARGETS,
        ],
        cwd=str(ROOT),
        env=environment,
        text=True,
        capture_output=True,
    )

    assert result.returncode == 0, f"collection failed:\n{result.stdout}\n{result.stderr}"
    assert "import file mismatch" not in result.stdout + result.stderr

    collected = json.loads(report_path.read_text(encoding="utf-8"))

    # The plugin records one entry per collected item, so the same module
    # appears once per test it defines.
    modules = sorted({(entry["name"], entry["file"]) for entry in collected})

    for dotted, expected_path in EXPECTED_MODULES.items():
        realpath = os.path.realpath(expected_path)
        matches = [name for name, path in modules if path == realpath]
        assert matches, f"pytest must collect {expected_path}; it collected {modules}"
        assert len(matches) == 1
        # The identity must carry the package chain, not the bare basename.
        # This is what the pre-fix state lost. The repository root is itself a
        # package, so pytest may prefix the identity with the checkout
        # directory name; the package chain itself is what must be present.
        assert matches[0] == dotted or matches[0].endswith("." + dotted), (
            f"{expected_path} was imported as {matches[0]!r}, "
            f"which does not carry the {dotted!r} package identity"
        )

    # Every one of the four physical files must be collected, under four
    # distinct module identities.
    collected_files = {path for _, path in modules}
    for expected_path in EXPECTED_MODULES.values():
        assert os.path.realpath(expected_path) in collected_files
    assert len(collected_files) == 4

    identities = [name for name, _ in modules]
    assert len(set(identities)) == len(identities)
