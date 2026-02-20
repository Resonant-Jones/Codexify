from __future__ import annotations

import configparser
import os
import sys
from pathlib import Path

from common import clear_python_caches, dump_dir_tree, log, run


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


def main() -> int:
    cfg_path = resolve_alembic_config()
    log("Migrator", f"Using Alembic config: {cfg_path}")

    removed_dirs, removed_files = clear_python_caches("/app/backend")
    log(
        "Migrator",
        f"Cleared Python caches under /app/backend: dirs={removed_dirs}, files={removed_files}",
    )

    print_script_location(cfg_path)

    try:
        run(alembic_cmd(["--raiseerr", "-c", str(cfg_path), "upgrade", "head"]))
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

    log("Migrator", "Running seed defaults")
    run([sys.executable, "/app/backend/scripts/seed_defaults.py"])

    log("Migrator", "Done")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
