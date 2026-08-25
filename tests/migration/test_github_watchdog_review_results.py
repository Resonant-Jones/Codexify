"""Schema regression tests for GitHub Watchdog review execution results."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from guardian.db.models import GitHubWatchdogReviewResult

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MIGRATION_FILENAME = "5d8e9f0a1b2c_add_github_watchdog_review_results.py"
REVISION = "5d8e9f0a1b2c"
DOWN_REVISION = "4c7d8e9f0a1b"
CURRENT_HEAD = "6e9f0a1b2c3"


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


def test_review_result_migration_is_the_single_new_head() -> None:
    migration_path = VERSIONS_DIR / MIGRATION_FILENAME
    tree = ast.parse(migration_path.read_text())

    assert _literal_assignment(tree, "revision") == REVISION
    assert _literal_assignment(tree, "down_revision") == DOWN_REVISION
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None

    script = ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )
    assert script.get_heads() == [CURRENT_HEAD]


def test_review_result_schema_is_snapshot_bound_and_immutable() -> None:
    columns = set(GitHubWatchdogReviewResult.__table__.columns.keys())
    assert {
        "result_id",
        "review_attempt_id",
        "review_input_snapshot_id",
        "snapshot_sha256",
        "result_state",
        "schema_version",
        "prompt_version",
        "prompt_sha256",
        "invoked_provider_id",
        "invoked_model_id",
        "requested_max_output_tokens",
        "raw_output_text",
        "raw_output_sha256",
        "raw_output_bytes",
        "structured_review_json",
        "provider_input_tokens",
        "provider_output_tokens",
        "provider_total_tokens",
        "provider_request_id",
        "terminal_error_code",
        "started_at",
        "completed_at",
    } <= columns
    assert "provider_api_key" not in columns
    assert "authorization" not in columns
    assert "github_token" not in columns
    assert "cost" not in columns
    assert "chain_of_thought" not in columns

    constraints = {
        constraint.name for constraint in GitHubWatchdogReviewResult.__table__.constraints
    }
    assert "uq_github_watchdog_review_results_review_attempt_id" in constraints
    assert "ck_github_watchdog_review_results_terminal_shape" in constraints
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in GitHubWatchdogReviewResult.__table__.foreign_keys
    }
    assert "github_watchdog_review_attempts.review_attempt_id" in foreign_keys
    assert "github_watchdog_review_input_snapshots.snapshot_id" in foreign_keys

    migration_source = (VERSIONS_DIR / MIGRATION_FILENAME).read_text()
    assert "github_watchdog_review_results" in migration_source
    assert "review_input_snapshot_id" in migration_source
    assert "github_token" not in migration_source
    assert "private_key" not in migration_source
