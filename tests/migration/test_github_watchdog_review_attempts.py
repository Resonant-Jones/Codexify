"""Schema regression tests for GitHub Watchdog review attempts."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from guardian.db.models import GitHubWatchdogReviewAttempt

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MIGRATION_FILENAME = "3b7c8d9e0f1a_add_github_watchdog_review_attempts.py"
REVISION = "3b7c8d9e0f1a"
DOWN_REVISION = "2a6b7c8d9e0f"
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


def test_review_attempt_migration_descends_from_receipt_head() -> None:
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


def test_review_attempt_schema_is_receipt_bound_and_bounded() -> None:
    columns = set(GitHubWatchdogReviewAttempt.__table__.columns.keys())
    assert {
        "review_attempt_id",
        "trigger_receipt_id",
        "github_delivery_id",
        "repository_id",
        "pull_request_number",
        "head_sha",
        "operation",
        "attempt_number",
        "attempt_state",
        "policy_resolution_state",
        "provider_id",
        "model_id",
        "model_selection_source",
        "policy_fingerprint",
        "escalation_mode",
        "superseded_by_attempt_id",
    } <= columns
    assert "raw_payload" not in columns
    assert "model_output" not in columns

    constraints = {
        constraint.name
        for constraint in GitHubWatchdogReviewAttempt.__table__.constraints
    }
    assert "uq_github_watchdog_review_attempts_trigger_receipt_id" in constraints
    foreign_keys = {
        foreign_key.target_fullname
        for foreign_key in GitHubWatchdogReviewAttempt.__table__.foreign_keys
    }
    assert "github_watchdog_delivery_receipts.receipt_id" in foreign_keys

    migration_source = (VERSIONS_DIR / MIGRATION_FILENAME).read_text()
    assert "github_watchdog_review_attempts" in migration_source
    assert "trigger_receipt_id" in migration_source
    assert "raw_payload" not in migration_source
