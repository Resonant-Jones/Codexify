"""Schema regression tests for immutable GitHub Watchdog review-input snapshots."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from guardian.db.models import GitHubWatchdogReviewInputSnapshot

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MIGRATION_FILENAME = "4c7d8e9f0a1b_add_github_watchdog_review_input_snapshots.py"
REVISION = "4c7d8e9f0a1b"
DOWN_REVISION = "3b7c8d9e0f1a"


def _literal_assignment(tree: ast.Module, name: str) -> object:
    for node in tree.body:
        if isinstance(node, ast.AnnAssign):
            target = node.target
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
        else:
            continue
        if isinstance(target, ast.Name) and target.id == name:
            return ast.literal_eval(node.value)
    raise AssertionError(f"missing {name} assignment")


def test_review_input_snapshot_migration_is_the_single_new_head() -> None:
    migration_path = VERSIONS_DIR / MIGRATION_FILENAME
    tree = ast.parse(migration_path.read_text())

    assert _literal_assignment(tree, "revision") == REVISION
    assert _literal_assignment(tree, "down_revision") == DOWN_REVISION
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None

    script = ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )
    assert script.get_heads() == ["5d8e9f0a1b2c"]


def test_review_input_snapshot_schema_is_attempt_bound_and_bounded() -> None:
    columns = set(GitHubWatchdogReviewInputSnapshot.__table__.columns.keys())
    assert {
        "snapshot_id",
        "review_attempt_id",
        "installation_id",
        "repository_id",
        "repository_full_name",
        "pull_request_number",
        "capture_state",
        "expected_head_sha",
        "observed_head_sha",
        "base_sha",
        "observed_base_sha",
        "pull_request_title",
        "pull_request_body",
        "changed_file_count",
        "files_without_patch_count",
        "changed_files_json",
        "captured_patch_bytes",
        "snapshot_sha256",
        "block_error_code",
    } <= columns
    assert "installation_token" not in columns
    assert "app_jwt" not in columns
    assert "model_response" not in columns

    constraint_names = {
        constraint.name
        for constraint in GitHubWatchdogReviewInputSnapshot.__table__.constraints
    }
    assert "uq_github_watchdog_review_input_snapshots_review_attempt_id" in constraint_names
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in GitHubWatchdogReviewInputSnapshot.__table__.foreign_keys
    }
    assert "github_watchdog_review_attempts.review_attempt_id" in foreign_keys

    migration_source = (VERSIONS_DIR / MIGRATION_FILENAME).read_text()
    assert "github_watchdog_review_input_snapshots" in migration_source
    assert "review_attempt_id" in migration_source
    assert "installation_token" not in migration_source
    assert "private_key" not in migration_source
