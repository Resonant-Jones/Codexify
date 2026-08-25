"""Schema regression tests for durable GitHub Watchdog review dispatches."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from guardian.db.models import GitHubWatchdogReviewDispatch

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MIGRATION_FILENAME = "6e9f0a1b2c3_add_github_watchdog_review_dispatches.py"
REVISION = "6e9f0a1b2c3"
DOWN_REVISION = "5d8e9f0a1b2c"


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


def test_review_dispatch_migration_is_the_single_new_head() -> None:
    migration_path = VERSIONS_DIR / MIGRATION_FILENAME
    tree = ast.parse(migration_path.read_text())

    assert _literal_assignment(tree, "revision") == REVISION
    assert _literal_assignment(tree, "down_revision") == DOWN_REVISION
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None

    script = ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )
    assert script.get_heads() == ["9c66e490a42b"]


def test_review_dispatch_schema_keeps_transport_separate_from_result_content() -> None:
    columns = set(GitHubWatchdogReviewDispatch.__table__.columns.keys())
    assert {
        "dispatch_id",
        "review_attempt_id",
        "review_input_snapshot_id",
        "snapshot_sha256",
        "head_sha",
        "dispatch_state",
        "queue_task_id",
        "enqueue_count",
        "last_enqueue_at",
        "worker_id",
        "started_at",
        "completed_at",
        "review_result_id",
        "terminal_error_code",
        "created_at",
        "updated_at",
    } <= columns
    assert "structured_review_json" not in columns
    assert "raw_output_text" not in columns
    assert "provider_api_key" not in columns
    assert "github_token" not in columns

    constraints = {
        constraint.name for constraint in GitHubWatchdogReviewDispatch.__table__.constraints
    }
    assert "uq_github_watchdog_review_dispatches_review_attempt_id" in constraints
    assert "ck_github_watchdog_review_dispatches_terminal_shape" in constraints
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in GitHubWatchdogReviewDispatch.__table__.foreign_keys
    }
    assert "github_watchdog_review_attempts.review_attempt_id" in foreign_keys
    assert "github_watchdog_review_input_snapshots.snapshot_id" in foreign_keys
    assert "github_watchdog_review_results.result_id" in foreign_keys

    source = (VERSIONS_DIR / MIGRATION_FILENAME).read_text()
    assert "github_watchdog_review_dispatches" in source
    assert "structured_review_json" not in source
    assert "private_key" not in source
    assert "installation_token" not in source
