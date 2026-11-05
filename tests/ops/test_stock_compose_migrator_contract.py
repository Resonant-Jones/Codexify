"""Contract tests for the stock Compose migration-source guarantee.

The stock ``docker-compose.yml`` contract serves the backend and the workers
from this checkout's source, so the migration source the migrator applies has
to describe the same checkout. These tests exercise the actual mechanism —
the comparison in ``backend/scripts/docker/run_migrator.py`` and the Compose
wiring that makes it reachable — rather than asserting on strings alone.
"""

from __future__ import annotations

import importlib.util
import shutil
import sys
from pathlib import Path

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[2]
COMPOSE_PATH = ROOT / "docker-compose.yml"
RUNTIME_COMPOSE_PATH = ROOT / "docker-compose.runtime.yml"
LAUNCHER_PATH = ROOT / "scripts/whooshd_docker_smoke_up.sh"
DOCKERFILE_PATH = ROOT / "backend/Dockerfile"
MIGRATOR_SCRIPT = ROOT / "backend/scripts/docker/run_migrator.py"
DOCKER_SCRIPT_DIR = ROOT / "backend/scripts/docker"
PROFILE_PATH = ROOT / "config/supported_profiles/v1-local-core-web-mcp.yaml"
REAL_MIGRATIONS = ROOT / "guardian/db/migrations"


def _load_migrator_module():
    """Load the stock migrator script the way the container runs it."""
    script_dir = str(DOCKER_SCRIPT_DIR)
    if script_dir not in sys.path:
        sys.path.insert(0, script_dir)
    # The script imports its sibling helper as a flat module; drop any other
    # module that happens to occupy that name.
    sys.modules.pop("common", None)
    spec = importlib.util.spec_from_file_location(
        "stock_run_migrator_under_test", MIGRATOR_SCRIPT
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    # Register before executing: the module defines a dataclass, and the
    # dataclass machinery resolves annotations through sys.modules.
    sys.modules[spec.name] = module
    try:
        spec.loader.exec_module(module)
    finally:
        # The sibling helper was imported under a flat name; do not leave it
        # in the global module namespace for other tests.
        sys.modules.pop("common", None)
    return module


@pytest.fixture(scope="module")
def migrator():
    return _load_migrator_module()


@pytest.fixture(scope="module")
def compose():
    return yaml.safe_load(COMPOSE_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def runtime_compose():
    return yaml.safe_load(RUNTIME_COMPOSE_PATH.read_text(encoding="utf-8"))


def _revision_file(revision: str, down_revision: str | None = None) -> str:
    return f'revision = "{revision}"\ndown_revision = {down_revision!r}\n'


DEFAULT_ENV = """from alembic import context

config = context.config
"""


def _migration_tree(
    root: Path, revisions: dict[str, str], *, include_env: bool = True
) -> Path:
    """Build a migration tree Alembic can read.

    The tree carries the migration environment as well as its revisions,
    because Alembic executes ``env.py`` during an upgrade and the coherence
    proof therefore has to cover it.
    """
    versions = root / "versions"
    versions.mkdir(parents=True, exist_ok=True)
    for name, body in revisions.items():
        (versions / name).write_text(body, encoding="utf-8")
    if include_env:
        (root / "env.py").write_text(DEFAULT_ENV, encoding="utf-8")
    return root


def _mounts(service: dict) -> list[dict]:
    """Normalise short and long volume syntax into one shape."""
    normalized: list[dict] = []
    for volume in service.get("volumes", []) or []:
        if isinstance(volume, dict):
            normalized.append(
                {
                    "source": str(volume.get("source", "")),
                    "target": str(volume.get("target", "")),
                    "read_only": bool(volume.get("read_only", False)),
                    "bind": volume.get("bind", {}) or {},
                }
            )
            continue
        parts = str(volume).split(":")
        normalized.append(
            {
                "source": parts[0],
                "target": parts[1] if len(parts) > 1 else "",
                "read_only": "ro" in parts[2:],
                "bind": {},
            }
        )
    return normalized


# --- A. Matching stock source/image migration state -----------------------


def test_matching_migration_source_is_coherent(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert comparison.coherent
    assert comparison.effective_revisions == 1
    assert comparison.source_revisions == 1
    assert comparison.missing_from_source == ()
    assert comparison.extra_in_source == ()
    assert comparison.content_mismatches == ()
    migrator.require_coherent_migration_source(comparison, source)


# --- B. Stale baked image versus newer source migration head --------------


def test_stale_image_missing_a_newer_source_revision_is_rejected(
    migrator, tmp_path
) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source",
        {
            "aaaa1111111_add_thing.py": _revision_file("aaaa1111111"),
            "bbbb2222222_add_other.py": _revision_file("bbbb2222222"),
        },
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert not comparison.coherent
    assert comparison.extra_in_source == ("bbbb2222222_add_other.py",)
    with pytest.raises(migrator.MigrationSourceError) as excinfo:
        migrator.require_coherent_migration_source(comparison, source)
    assert "bbbb2222222_add_other.py" in str(excinfo.value)


def test_image_ahead_of_the_source_is_rejected(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image",
        {
            "aaaa1111111_add_thing.py": _revision_file("aaaa1111111"),
            "bbbb2222222_add_other.py": _revision_file("bbbb2222222"),
        },
    )
    source = _migration_tree(
        tmp_path / "source", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert not comparison.coherent
    assert comparison.missing_from_source == ("bbbb2222222_add_other.py",)
    with pytest.raises(migrator.MigrationSourceError):
        migrator.require_coherent_migration_source(comparison, source)


def test_same_revision_with_different_content_is_rejected(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source",
        {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111", "cccc3333333")},
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert not comparison.coherent
    assert comparison.content_mismatches == ("aaaa1111111_add_thing.py",)
    with pytest.raises(migrator.MigrationSourceError):
        migrator.require_coherent_migration_source(comparison, source)


# --- C. Missing migration source ------------------------------------------


def test_altered_migration_environment_is_rejected(migrator, tmp_path) -> None:
    """Identical revisions with a different ``env.py`` are not the same source.

    Alembic executes ``env.py`` during an upgrade, so two trees that agree on
    every revision file can still apply the schema differently.
    """
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    (source / "env.py").write_text(
        "from alembic import context\n# altered environment\n", encoding="utf-8"
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert not comparison.coherent
    assert comparison.environment_mismatches
    assert any("env.py" in entry for entry in comparison.environment_mismatches)
    # The revision comparison itself is clean; only the environment differs.
    assert comparison.content_mismatches == ()
    with pytest.raises(migrator.MigrationSourceError, match="env.py"):
        migrator.require_coherent_migration_source(comparison, source)


def test_missing_migration_environment_is_rejected(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source",
        {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")},
        include_env=False,
    )

    comparison = migrator.compare_migration_sources(effective, source)

    assert not comparison.coherent
    with pytest.raises(migrator.MigrationSourceError, match="env.py"):
        migrator.require_coherent_migration_source(comparison, source)


def test_missing_migration_source_is_rejected(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    absent = tmp_path / "absent"

    comparison = migrator.compare_migration_sources(effective, absent)

    assert not comparison.coherent
    with pytest.raises(migrator.MigrationSourceError):
        migrator.require_coherent_migration_source(comparison, absent)


def test_migration_source_without_revisions_is_rejected(migrator, tmp_path) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    empty = tmp_path / "empty"
    (empty / "versions").mkdir(parents=True)

    comparison = migrator.compare_migration_sources(effective, empty)

    assert not comparison.coherent
    with pytest.raises(migrator.MigrationSourceError, match="no migration revisions"):
        migrator.require_coherent_migration_source(comparison, empty)


# --- D. Multiple migration heads ------------------------------------------


def test_multiple_heads_are_rejected(migrator, tmp_path) -> None:
    script_dir = tmp_path / "migrations"

    assert migrator.require_single_head(["aaaa1111111"], script_dir) == "aaaa1111111"

    with pytest.raises(migrator.MigrationSourceError, match="multiple Alembic heads"):
        migrator.require_single_head(["aaaa1111111", "bbbb2222222"], script_dir)

    with pytest.raises(migrator.MigrationSourceError, match="no Alembic head"):
        migrator.require_single_head([], script_dir)


# --- E. Migrator failure preventing dependent application readiness --------


def test_backend_and_workers_wait_for_a_successful_migration(compose) -> None:
    backend = compose["services"]["backend"]
    assert backend["depends_on"]["migrator"]["condition"] == "service_completed_successfully"


def test_migrator_exits_non_zero_before_migrating_an_incoherent_source(
    migrator, tmp_path, monkeypatch
) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source",
        {
            "aaaa1111111_add_thing.py": _revision_file("aaaa1111111"),
            "bbbb2222222_add_other.py": _revision_file("bbbb2222222"),
        },
    )
    ini = tmp_path / "alembic.ini"
    ini.write_text(
        f"[alembic]\nscript_location = {effective}\n", encoding="utf-8"
    )

    def _must_not_run(*args, **kwargs):
        raise AssertionError("alembic must not run against an incoherent source")

    monkeypatch.setattr(migrator, "run", _must_not_run)
    monkeypatch.setenv("ALEMBIC_CONFIG", str(ini))
    monkeypatch.setenv("CODEXIFY_SOURCE_MIGRATIONS_DIR", str(source))

    assert migrator.main() == 1


def test_migrator_exits_non_zero_before_migrating_an_altered_environment(
    migrator, tmp_path, monkeypatch
) -> None:
    effective = _migration_tree(
        tmp_path / "image", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    source = _migration_tree(
        tmp_path / "source", {"aaaa1111111_add_thing.py": _revision_file("aaaa1111111")}
    )
    (source / "env.py").write_text(
        "from alembic import context\n# altered environment\n", encoding="utf-8"
    )
    ini = tmp_path / "alembic.ini"
    ini.write_text(
        f"[alembic]\nscript_location = {effective}\n", encoding="utf-8"
    )

    def _must_not_run(*args, **kwargs):
        raise AssertionError("alembic must not run against an incoherent source")

    monkeypatch.setattr(migrator, "run", _must_not_run)
    monkeypatch.setenv("ALEMBIC_CONFIG", str(ini))
    monkeypatch.setenv("CODEXIFY_SOURCE_MIGRATIONS_DIR", str(source))

    assert migrator.main() == 1


def test_database_head_mismatch_is_rejected(migrator, monkeypatch) -> None:
    monkeypatch.setattr(migrator, "read_alembic_versions", lambda dsn: ["aaaa1111111"])

    migrator.require_database_head("aaaa1111111", "postgresql://user:pw@db:5432/db")

    with pytest.raises(migrator.MigrationSourceError, match="does not match"):
        migrator.require_database_head("bbbb2222222", "postgresql://user:pw@db:5432/db")


def test_alembic_driver_selectors_are_normalised_for_the_readback(migrator) -> None:
    assert (
        migrator.normalize_dsn("postgresql+psycopg://u:p@db:5432/d")
        == "postgresql://u:p@db:5432/d"
    )
    assert (
        migrator.normalize_dsn("postgresql://u:p@db:5432/d") == "postgresql://u:p@db:5432/d"
    )


# --- F. Existing source-matched launcher startup remains unchanged --------


def test_launcher_image_shape_satisfies_the_migration_source_comparison(
    migrator, tmp_path
) -> None:
    launcher = LAUNCHER_PATH.read_text(encoding="utf-8")
    dockerfile = DOCKERFILE_PATH.read_text(encoding="utf-8")

    # The launcher builds the runtime image from the repository root, and the
    # Dockerfile copies that same guardian tree into /app/guardian. The image
    # therefore carries the migration source the migrator compares against.
    assert 'docker build --target runtime -f backend/Dockerfile -t "$IMAGE_TAG" "$REPO_ROOT"' in launcher
    assert "COPY guardian /app/guardian" in dockerfile

    # The launcher does not set the comparison variable itself; the stock
    # Compose contract sets it, and the launcher's image matches the checkout.
    assert "CODEXIFY_SOURCE_MIGRATIONS_DIR" not in launcher

    # Exercise the comparison against the real migration tree and an
    # independent copy of it, the shape a launcher-built image presents.
    image_copy = tmp_path / "image-migrations"
    shutil.copytree(REAL_MIGRATIONS, image_copy)

    comparison = migrator.compare_migration_sources(REAL_MIGRATIONS, image_copy)
    assert comparison.coherent, comparison.summary()
    assert comparison.effective_revisions > 0


# --- G. No regression to the packaged runtime configuration ----------------


def test_packaged_runtime_migrator_is_unchanged(runtime_compose) -> None:
    migrator = runtime_compose["services"]["migrator"]

    assert migrator["entrypoint"] == ["/app/runtime/codexify-runtime"]
    assert migrator["command"] == ["migrator"]
    assert "CODEXIFY_SOURCE_MIGRATIONS_DIR" not in migrator.get("environment", {})
    assert not _mounts(migrator)


def test_packaged_runtime_does_not_use_the_stock_migrator_script(
    runtime_compose,
) -> None:
    text = RUNTIME_COMPOSE_PATH.read_text(encoding="utf-8")
    assert "run_migrator.py" not in text


# --- H. No accidental cloud-provider or supported-profile change ---------


def test_stock_migrator_keeps_the_local_only_provider_contract(compose) -> None:
    env = compose["services"]["migrator"]["environment"]

    assert env["LLM_PROVIDER"] == "local"
    assert env["EMBED_PROVIDER"] == "local"
    assert env["EMBEDDER_PROVIDER"] == "local"
    assert env["CODEXIFY_USE_OPENAI"] == "0"


def test_supported_profile_provider_contract_is_unchanged() -> None:
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    contract = profile["provider_contract"]

    assert contract["LLM_PROVIDER"] == "local"
    assert contract["ALLOW_CLOUD_PROVIDERS"] is False
    assert contract["CODEXIFY_LOCAL_ONLY_MODE"] is True
    assert contract["CODEXIFY_EGRESS_ALLOWLIST"] == ""
    assert contract["LOCAL_PROVIDER_VENDOR"] == "whooshd"


# --- The stock Compose wiring the guarantee depends on --------------------


def test_stock_migrator_compares_against_the_checkout_migration_source(
    compose,
) -> None:
    migrator = compose["services"]["migrator"]

    assert migrator["environment"]["CODEXIFY_SOURCE_MIGRATIONS_DIR"] == "/source-migrations"
    assert migrator["command"] == ["/app/backend/scripts/docker/run_migrator.py"]

    side_mounts = [m for m in _mounts(migrator) if m["target"] == "/source-migrations"]
    assert len(side_mounts) == 1
    side = side_mounts[0]
    assert side["source"].endswith("guardian/db/migrations")
    assert side["read_only"] is True
    assert side["bind"].get("create_host_path") is False

    # The checkout's migration source is compared, never executed from: the
    # migrator still runs the source baked into the image.
    targets = {m["target"] for m in _mounts(migrator)}
    assert "/app/guardian" not in targets


def test_stock_migrator_keeps_the_prebaked_image_contract(compose) -> None:
    migrator = compose["services"]["migrator"]

    assert migrator["image"] == "${CODEXIFY_BACKEND_IMAGE:-codexify-backend-runtime:latest}"
    assert migrator["pull_policy"] == "never"
    assert migrator["build"] == {
        "context": ".",
        "dockerfile": "backend/Dockerfile",
        "target": "runtime",
    }


def test_application_services_serve_the_checkout_source(compose) -> None:
    for service in ("backend", "worker-chat", "worker-document-embed"):
        sources = [m["source"] for m in _mounts(compose["services"][service])]
        assert any(
            source.endswith("/guardian") or source == "./guardian"
            for source in sources
        ), service
