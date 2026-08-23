"""Schema regression tests for GitHub Watchdog delivery receipts."""

from __future__ import annotations

import ast
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

from guardian.db.models import GitHubWatchdogDeliveryReceipt


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"
MIGRATION_FILENAME = "2a6b7c8d9e0f_add_github_watchdog_delivery_receipts.py"
REVISION = "2a6b7c8d9e0f"
DOWN_REVISION = "1c0a2b3c4d5e"


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


def test_watchdog_receipt_migration_descends_from_the_current_head() -> None:
    migration_path = VERSIONS_DIR / MIGRATION_FILENAME
    tree = ast.parse(migration_path.read_text())

    assert _literal_assignment(tree, "revision") == REVISION
    assert _literal_assignment(tree, "down_revision") == DOWN_REVISION
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None

    script = ScriptDirectory.from_config(
        Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    )
    assert script.get_heads() == [REVISION]


def test_watchdog_receipt_schema_is_bounded_and_idempotent() -> None:
    columns = set(GitHubWatchdogDeliveryReceipt.__table__.columns.keys())
    assert {
        "receipt_id",
        "github_delivery_id",
        "idempotency_key",
        "event_name",
        "action",
        "installation_id",
        "repository_id",
        "repository_full_name",
        "trigger_actor_id",
        "trigger_actor_login",
        "pull_request_number",
        "head_sha",
        "payload_sha256",
        "first_received_at",
        "last_received_at",
        "redelivery_count",
    } <= columns
    assert "payload" not in columns
    assert "watchdog_run_id" not in columns

    constraint_names = {
        constraint.name
        for constraint in GitHubWatchdogDeliveryReceipt.__table__.constraints
    }
    assert "uq_github_watchdog_delivery_receipts_idempotency_key" in constraint_names

    migration_source = (VERSIONS_DIR / MIGRATION_FILENAME).read_text()
    assert "github_watchdog_delivery_receipts" in migration_source
    assert "payload_sha256" in migration_source
    assert "raw_payload" not in migration_source
