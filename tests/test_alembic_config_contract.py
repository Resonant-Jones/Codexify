"""Guardrails for Alembic config pathing used in runtime containers."""

from __future__ import annotations

import configparser
from pathlib import Path


def test_backend_alembic_points_to_canonical_migrations_dir() -> None:
    repo_root = Path(__file__).resolve().parents[1]
    cfg_path = repo_root / "backend" / "alembic.ini"
    assert cfg_path.is_file(), "backend/alembic.ini must exist"

    parser = configparser.RawConfigParser()
    parser.read(cfg_path)
    script_location = parser.get("alembic", "script_location", fallback="")
    assert (
        script_location
    ), "backend/alembic.ini must define [alembic] script_location"

    expected = (repo_root / "guardian" / "db" / "migrations").resolve()
    resolved = Path(
        script_location.replace("%(here)s", str(cfg_path.parent))
    ).resolve()

    assert (
        resolved == expected
    ), "backend/alembic.ini script_location must resolve to guardian/db/migrations"
    assert (
        resolved / "env.py"
    ).is_file(), "Alembic env.py missing in migrations dir"
    assert (
        resolved / "versions"
    ).is_dir(), "Alembic versions dir missing in migrations dir"
