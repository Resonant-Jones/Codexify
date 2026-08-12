"""Regression tests for the canonical Alembic revision graph."""

from __future__ import annotations

import ast
from collections import defaultdict
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory


REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"


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

    raise AssertionError(f"{name} assignment missing")


def _migration_metadata() -> dict[str, dict[str, object]]:
    metadata: dict[str, dict[str, object]] = {}
    for path in sorted(VERSIONS_DIR.glob("*.py")):
        tree = ast.parse(path.read_text())
        revision = _literal_assignment(tree, "revision")
        down_revision = _literal_assignment(tree, "down_revision")
        assert isinstance(revision, str)
        metadata[path.name] = {
            "revision": revision,
            "down_revision": down_revision,
        }
    return metadata


def test_alembic_revision_ids_are_unique_and_hosted_room_lineage_is_preserved():
    metadata = _migration_metadata()
    by_revision: defaultdict[str, list[str]] = defaultdict(list)
    for filename, values in metadata.items():
        by_revision[values["revision"]].append(filename)

    duplicates = {
        revision: filenames
        for revision, filenames in by_revision.items()
        if len(filenames) > 1
    }
    assert duplicates == {}

    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    script = ScriptDirectory.from_config(config)

    hosted_provenance = script.get_revision("7a91c4e2f6b8")
    hosted_actor = script.get_revision("8b02d5f3a7c9")
    browser_audit = script.get_revision("c3d4e5f6a7b8")
    delegation = script.get_revision("d4e5f6a7b8c9")
    email_login_alias = script.get_revision("c1a2b3c4d5e6")
    repository_bindings = script.get_revision("6e2b9c4a7d1f")

    hosted_foundation = script.get_revision("b2c3d4e5f6a8")

    assert hosted_foundation.down_revision == "b2c3d4e5f6a7"
    assert hosted_provenance.down_revision == "b2c3d4e5f6a8"
    assert hosted_actor.down_revision == "7a91c4e2f6b8"
    assert (
        Path(browser_audit.path).name
        == "c3d4e5f6a7b8_add_browser_audit_log_table.py"
    )
    assert (
        Path(delegation.path).name
        == "d4e5f6a7b8c9_add_delegation_tables.py"
    )

    assert metadata["f4e7c1a2b3d4_add_channel_tables.py"]["down_revision"] == (
        "c3d4e5f6a7b8"
    )
    assert metadata[
        "e3f2a1b4c5d6_add_authenticated_principals_table.py"
    ]["down_revision"] == ("4c9d1e2f3a5b", "d4e5f6a7b8c9")
    assert email_login_alias.down_revision == "d0e1f2a3b4c6"

    assert repository_bindings is not None
    assert repository_bindings.down_revision == "c1a2b3c4d5e6"
    assert isinstance(repository_bindings.down_revision, str)

    heads = script.get_heads()
    assert heads == ["6e2b9c4a7d1f"]
    assert script.get_revision("d0e1f2a3b4c6").down_revision == (
        "8c4d2e7f1a9b",
        "c8d9e0f1a2b3",
    )
