from __future__ import annotations

import configparser
import hashlib
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from common import clear_python_caches, dump_dir_tree, log, run


# Set by the stock Compose contract to point at this checkout's migration
# source. When it is present the migrator proves that the migration source it
# is about to execute describes the same checkout the application serves.
# When it is absent (for example the disposable packaged-image migration
# proof, which intentionally runs with no source mounts) no comparison is made.
SOURCE_MIGRATIONS_DIR_ENV = "CODEXIFY_SOURCE_MIGRATIONS_DIR"

VERSIONS_DIRNAME = "versions"
REVISION_SUFFIX = ".py"


class MigrationSourceError(RuntimeError):
    """The migration source could not be proven coherent, or did not apply."""


@dataclass(frozen=True)
class MigrationSourceComparison:
    """Difference between the effective migration source and the checkout's."""

    effective_revisions: int
    source_revisions: int
    missing_from_source: tuple[str, ...]
    extra_in_source: tuple[str, ...]
    content_mismatches: tuple[str, ...]
    errors: tuple[str, ...]

    @property
    def coherent(self) -> bool:
        return not (
            self.errors
            or self.missing_from_source
            or self.extra_in_source
            or self.content_mismatches
        )

    def summary(self) -> str:
        return (
            f"effective_revisions={self.effective_revisions}, "
            f"source_revisions={self.source_revisions}, "
            f"missing_from_source={list(self.missing_from_source)}, "
            f"extra_in_source={list(self.extra_in_source)}, "
            f"content_mismatches={list(self.content_mismatches)}, "
            f"errors={list(self.errors)}"
        )


def resolve_alembic_config() -> Path:
    candidates: list[Path] = []

    env_cfg = os.environ.get("ALEMBIC_CONFIG")
    if env_cfg:
        candidates.append(Path(env_cfg))

    candidates.append(Path("/app/backend/alembic.ini"))
    candidates.append(Path("/app/backend/alembic/alembic.ini"))

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    log("Migrator", "ERROR: no alembic config found")
    dump_dir_tree(["/app", "/app/backend"])
    raise SystemExit(1)


def print_script_location(cfg_path: Path) -> None:
    parser = configparser.RawConfigParser()
    parser.read(cfg_path)
    script_location = parser.get("alembic", "script_location", fallback="")

    if script_location:
        log("Migrator", f"alembic.ini script_location={script_location}")
        return

    log(
        "Migrator",
        "script_location missing in ini, falling back to `alembic current`",
    )
    run(alembic_cmd(["-c", str(cfg_path), "current"]), check=False)


def alembic_cmd(args: list[str]) -> list[str]:
    from shutil import which

    if which("alembic"):
        return ["alembic", *args]
    return [sys.executable, "-m", "alembic", *args]


def resolve_migration_context(cfg_path: Path) -> tuple[Path, list[str]]:
    """Return the effective migration directory and the Alembic heads."""
    from alembic.config import Config
    from alembic.script import ScriptDirectory

    config = Config(str(cfg_path))
    script_dir = ScriptDirectory.from_config(config)
    return Path(script_dir.dir).resolve(), list(script_dir.get_heads())


def require_single_head(heads: list[str], script_dir: Path) -> str:
    """Fail closed unless the migration source has exactly one head."""
    if not heads:
        raise MigrationSourceError(f"no Alembic head found under {script_dir}")
    if len(heads) > 1:
        raise MigrationSourceError(
            f"multiple Alembic heads under {script_dir}: {sorted(heads)}"
        )
    return heads[0]


def revision_digests(migrations_dir: Path) -> tuple[dict[str, str], list[str]]:
    """Return {revision filename: sha256} for a migration tree, plus read errors."""
    digests: dict[str, str] = {}
    errors: list[str] = []
    versions_dir = migrations_dir / VERSIONS_DIRNAME

    try:
        entries = sorted(versions_dir.iterdir())
    except OSError as exc:
        return {}, [f"cannot list {versions_dir}: {exc}"]

    for entry in entries:
        if entry.suffix != REVISION_SUFFIX or entry.name.startswith("."):
            continue
        try:
            digests[entry.name] = hashlib.sha256(entry.read_bytes()).hexdigest()
        except OSError as exc:
            errors.append(f"cannot read {entry}: {exc}")
    return digests, errors


def compare_migration_sources(
    effective_dir: Path, source_dir: Path
) -> MigrationSourceComparison:
    """Compare the effective migration source against the checkout's."""
    effective, effective_errors = revision_digests(effective_dir)
    source, source_errors = revision_digests(source_dir)

    missing = tuple(sorted(set(effective) - set(source)))
    extra = tuple(sorted(set(source) - set(effective)))
    mismatched = tuple(
        sorted(
            name
            for name in set(effective) & set(source)
            if effective[name] != source[name]
        )
    )

    return MigrationSourceComparison(
        effective_revisions=len(effective),
        source_revisions=len(source),
        missing_from_source=missing,
        extra_in_source=extra,
        content_mismatches=mismatched,
        errors=tuple(effective_errors + source_errors),
    )


def require_coherent_migration_source(
    comparison: MigrationSourceComparison, source_dir: Path
) -> None:
    """Fail closed unless the effective migration source describes the checkout."""
    if comparison.errors:
        raise MigrationSourceError(
            "the migration source could not be read: " + "; ".join(comparison.errors)
        )
    if comparison.source_revisions == 0:
        raise MigrationSourceError(
            f"no migration revisions found in the checkout's migration source {source_dir}"
        )
    if not comparison.coherent:
        raise MigrationSourceError(
            "the migration source does not describe this checkout "
            f"({comparison.summary()}); rebuild the backend image from this "
            "checkout before starting the stack"
        )


def normalize_dsn(dsn: str) -> str:
    """Strip SQLAlchemy driver selectors so a plain DBAPI can connect."""
    for prefix in ("postgresql+psycopg2", "postgresql+psycopg", "postgres+psycopg2"):
        if dsn.startswith(f"{prefix}://"):
            return dsn.replace(f"{prefix}://", "postgresql://", 1)
    return dsn


def read_alembic_versions(dsn: str) -> list[str]:
    """Read the applied revision(s) straight out of PostgreSQL."""
    normalized = normalize_dsn(dsn)
    try:
        import psycopg  # type: ignore
    except ImportError:
        import psycopg2  # type: ignore

        conn = psycopg2.connect(normalized)
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version_num FROM alembic_version")
                return [row[0] for row in cur.fetchall()]
        finally:
            conn.close()

    with psycopg.connect(normalized) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT version_num FROM alembic_version")
            return [row[0] for row in cur.fetchall()]


def require_database_head(expected_head: str, dsn: str) -> None:
    """Fail closed unless the database actually holds the expected revision."""
    rows = sorted(read_alembic_versions(dsn))
    if rows != [expected_head]:
        raise MigrationSourceError(
            f"alembic_version readback {rows} does not match the expected head "
            f"{expected_head}"
        )


def main() -> int:
    cfg_path = resolve_alembic_config()
    log("Migrator", f"Using Alembic config: {cfg_path}")

    removed_dirs, removed_files = clear_python_caches("/app/backend")
    log(
        "Migrator",
        f"Cleared Python caches under /app/backend: dirs={removed_dirs}, files={removed_files}",
    )

    # Also clean the guardian migrations dir, which the stock contract
    # compares against this checkout, and which may carry stale host .pyc
    # files that confuse Alembic.
    g_dirs, g_files = clear_python_caches("/app/guardian/db/migrations")
    if g_dirs or g_files:
        log(
            "Migrator",
            f"Cleared guardian migration caches: dirs={g_dirs}, files={g_files}",
        )

    print_script_location(cfg_path)

    try:
        script_dir, heads = resolve_migration_context(cfg_path)
    except Exception as exc:  # noqa: BLE001
        log("Migrator", f"ERROR: could not resolve the Alembic migration source: {exc}")
        return 1

    log("Migrator", f"Effective migration source: {script_dir}")
    log("Migrator", f"Alembic heads: {sorted(heads)}")

    try:
        head = require_single_head(heads, script_dir)
    except MigrationSourceError as exc:
        log("Migrator", f"ERROR: {exc}")
        return 1

    source_dir_env = os.environ.get(SOURCE_MIGRATIONS_DIR_ENV, "").strip()
    if source_dir_env:
        source_dir = Path(source_dir_env)
        log("Migrator", f"Comparing the migration source against {source_dir}")
        comparison = compare_migration_sources(script_dir, source_dir)
        try:
            require_coherent_migration_source(comparison, source_dir)
        except MigrationSourceError as exc:
            log("Migrator", f"ERROR: {exc}")
            return 1
        log(
            "Migrator",
            f"Migration source is coherent ({comparison.effective_revisions} revisions)",
        )
    else:
        log(
            "Migrator",
            f"{SOURCE_MIGRATIONS_DIR_ENV} is not set; no checkout comparison is made",
        )

    try:
        run(
            alembic_cmd(["--raiseerr", "-c", str(cfg_path), "upgrade", "heads"])
        )
    except Exception as exc:  # noqa: BLE001
        log("Migrator", f"ERROR: alembic upgrade failed: {exc}")
        cfg_dir = str(cfg_path.parent)
        dump_dir_tree(
            [
                "/app/backend",
                "/app/backend/migrations",
                "/app/backend/alembic",
                cfg_dir,
            ]
        )
        return 1

    dsn = os.environ.get("DATABASE_URL", "").strip()
    if not dsn:
        log("Migrator", "ERROR: DATABASE_URL is not set; cannot verify the schema")
        return 1
    try:
        require_database_head(head, dsn)
    except Exception as exc:  # noqa: BLE001
        log("Migrator", f"ERROR: schema verification failed: {exc}")
        return 1
    log("Migrator", f"Verified alembic_version == {head}")

    log("Migrator", "Running seed defaults")
    run([sys.executable, "/app/backend/scripts/seed_defaults.py"])

    log("Migrator", "Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
