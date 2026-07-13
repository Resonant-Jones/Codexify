"""Tests for static, secret-safe canonical runtime identity collection."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.audit.collect_canonical_runtime_identity import (
    RuntimeIdentityError,
    collect_runtime_identity,
)


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts/audit/collect_canonical_runtime_identity.py"


PROFILE = """name: v1-local-core-web-mcp
version: 1
surface: local-docker-compose-webui
required_services:
  - backend
  - db
optional_services:
  - redis
extension_posture:
  public: []
  internal: []
route_posture:
  enabled: []
  internal_only: []
  quarantined: []
provider_contract: {}
criticality:
  tier0:
    services: [backend, db]
    routes: []
"""


def _migration(revision: str, down_revision: str | None = None) -> str:
    return f'''"""fixture migration."""
revision = "{revision}"
down_revision = {down_revision!r}
'''


def make_fixture(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "repo"
    profile_dir = root / "config" / "supported_profiles"
    migration_dir = root / "guardian" / "db" / "migrations" / "versions"
    profile_dir.mkdir(parents=True)
    migration_dir.mkdir(parents=True)
    (profile_dir / "v1-local-core-web-mcp.yaml").write_text(PROFILE, encoding="utf-8")
    compose = root / "docker-compose.yml"
    compose.write_text(
        "name: codexify\nservices:\n  backend: {}\n  db: {}\n  redis: {}\n",
        encoding="utf-8",
    )
    override = root / "docker-compose.override.yml"
    override.write_text("services:\n  worker: {}\n", encoding="utf-8")
    (migration_dir / "a_revision.py").write_text(_migration("head-a"), encoding="utf-8")
    return {
        "root": root,
        "profile_dir": profile_dir,
        "migration_dir": migration_dir,
        "compose": compose,
        "override": override,
    }


def collect(fixture: dict[str, Path], **kwargs: object) -> dict:
    return collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.yml"],
        audit_project="codexify-audit",
        migration_dir=fixture["migration_dir"],
        **kwargs,
    )


def test_clean_static_identity_is_deterministic_and_non_docker(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    first = collect(fixture, serving_project="codexify")
    second = collect(fixture, serving_project="codexify")
    assert first == second
    assert first["observation_complete"] is True
    assert first["eligibility"]["canonical_runtime_candidate"] is True
    assert first["runtime"]["supported_profile"] == "v1-local-core-web-mcp"
    assert first["runtime"]["migration_head"] == "head-a"
    assert first["runtime"]["service_identities"] == ["backend", "db", "redis"]
    assert len(first["runtime"]["effective_config_hash"]) == 64
    assert str(fixture["root"]) not in json.dumps(first)


def test_compose_order_and_bytes_change_effective_identity(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    first = collect(fixture, serving_project="codexify")
    ordered = collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.override.yml", "docker-compose.yml"],
        audit_project="codexify-audit",
        serving_project="codexify",
        migration_dir=fixture["migration_dir"],
    )
    reversed_order = collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.yml", "docker-compose.override.yml"],
        audit_project="codexify-audit",
        serving_project="codexify",
        migration_dir=fixture["migration_dir"],
    )
    assert ordered["runtime"]["effective_config_hash"] != first["runtime"]["effective_config_hash"]
    assert ordered["runtime"]["effective_config_hash"] != reversed_order["runtime"]["effective_config_hash"]
    before = first["runtime"]["profile_identity"]["sha256"]
    (fixture["profile_dir"] / "v1-local-core-web-mcp.yaml").write_text(PROFILE + "\n", encoding="utf-8")
    changed = collect(fixture, serving_project="codexify")
    assert changed["runtime"]["profile_identity"]["sha256"] != before
    assert changed["runtime"]["effective_config_hash"] != first["runtime"]["effective_config_hash"]


def test_missing_required_service_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    fixture["compose"].write_text("name: codexify\nservices:\n  backend: {}\n", encoding="utf-8")
    result = collect(fixture)
    assert result["observation_complete"] is False
    assert result["eligibility"]["compose_identity_complete"] is False
    assert result["eligibility"]["canonical_runtime_candidate"] is False
    assert "required_service_missing" in result["eligibility"]["reason_codes"]


@pytest.mark.parametrize(
    ("compose_files", "code"),
    [
        (["/tmp/compose.yml"], "compose_path_absolute"),
        (["../compose.yml"], "compose_path_parent_traversal"),
        (["docker-compose.yml", "./docker-compose.yml"], "compose_file_duplicate"),
        (["missing.yml"], "compose_file_missing"),
    ],
)
def test_compose_path_safety_reason_codes(tmp_path: Path, compose_files: list[str], code: str) -> None:
    fixture = make_fixture(tmp_path)
    result = collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=compose_files,
        audit_project="codexify-audit",
        migration_dir=fixture["migration_dir"],
    )
    assert code in result["eligibility"]["reason_codes"]
    assert result["observation_complete"] is False


def test_project_collision_and_secret_input_are_safe(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    collision = collect(fixture, serving_project="codexify-audit")
    assert "serving_audit_project_identity_collision" in collision["eligibility"]["reason_codes"]
    secret = collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.yml"],
        audit_project="postgres://user:super-secret@example.invalid/db",
        migration_dir=fixture["migration_dir"],
    )
    encoded = json.dumps(secret)
    assert "forbidden_secret_input" in secret["eligibility"]["reason_codes"]
    assert "super-secret" not in encoded
    assert "postgres://" not in encoded


def test_multiple_migration_heads_fail_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    (fixture["migration_dir"] / "b_revision.py").write_text(_migration("head-b"), encoding="utf-8")
    result = collect(fixture)
    assert "migration_head_multiple" in result["eligibility"]["reason_codes"]
    assert result["runtime"]["migration_head"] is None
    assert result["observation_complete"] is False


def test_dangling_migration_parent_fails_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    (fixture["migration_dir"] / "a_revision.py").write_text(
        _migration("head-a", "missing-parent"), encoding="utf-8"
    )
    result = collect(fixture)
    assert "migration_identity_incomplete" in result["eligibility"]["reason_codes"]
    assert result["eligibility"]["migration_identity_complete"] is False
    assert result["eligibility"]["runtime_identity_complete"] is False
    assert result["eligibility"]["canonical_runtime_candidate"] is False
    assert result["runtime"]["migration_head"] is None


def test_profile_and_service_identity_fail_closed(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    (fixture["profile_dir"] / "v1-local-core-web-mcp.yaml").write_text("name: broken\n", encoding="utf-8")
    result = collect(fixture)
    assert "supported_profile_invalid" in result["eligibility"]["reason_codes"]
    compose = fixture["root"] / "docker-compose.yml"
    compose.write_text("name: codexify\nservices:\n  Backend: {}\n  backend: {}\n  db: {}\n", encoding="utf-8")
    result = collect(fixture)
    assert "service_identity_conflict" in result["eligibility"]["reason_codes"]


def test_no_project_input_is_provisional_incomplete(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    result = collect_runtime_identity(
        fixture["root"],
        profiles_dir=fixture["profile_dir"],
        compose_files=["docker-compose.yml"],
        migration_dir=fixture["migration_dir"],
    )
    assert result["runtime"]["compose_project"] == "codexify"
    assert result["eligibility"]["canonical_runtime_candidate"] is False
    assert "compose_project_identity_ambiguous" not in result["eligibility"]["reason_codes"]


def test_cli_is_deterministic_and_returns_complete_static_observation(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    args = [
        sys.executable,
        str(SCRIPT),
        "--repo",
        str(fixture["root"]),
        "--profiles-dir",
        str(fixture["profile_dir"]),
        "--compose-file",
        "docker-compose.yml",
        "--audit-project",
        "codexify-audit",
        "--serving-project",
        "codexify",
        "--migration-dir",
        str(fixture["migration_dir"]),
    ]
    first = subprocess.run(args, check=False, capture_output=True, text=True)
    second = subprocess.run(args, check=False, capture_output=True, text=True)
    assert first.returncode == second.returncode == 0
    assert first.stdout == second.stdout
    assert str(fixture["root"]) not in first.stdout
    assert "postgres://" not in first.stdout
    assert json.loads(first.stdout)["eligibility"]["canonical_runtime_candidate"] is True


def test_collector_does_not_mutate_fixture_files(tmp_path: Path) -> None:
    fixture = make_fixture(tmp_path)
    tracked = [fixture["compose"], fixture["override"], fixture["profile_dir"] / "v1-local-core-web-mcp.yaml"]
    before = {path: path.read_bytes() for path in tracked}
    collect(fixture)
    assert {path: path.read_bytes() for path in tracked} == before


def test_invalid_root_is_fail_closed(tmp_path: Path) -> None:
    with pytest.raises(RuntimeIdentityError) as error:
        collect_runtime_identity(tmp_path / "missing", compose_files=["docker-compose.yml"])
    assert error.value.code == "runtime_identity_incomplete"
