"""Bind the canonical current-state migration claim to the Alembic graph."""

from __future__ import annotations

import ast
import configparser
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALEMBIC_CONFIG_PATH = REPO_ROOT / "backend" / "alembic.ini"
CURRENT_STATE_PATH = REPO_ROOT / "docs" / "architecture" / "00-current-state.md"

#: Matches the authoritative migration claim in "## Current phase". The claim
#: is matched on its MEANING — a single Alembic head plus a revision count —
#: rather than on one exact wording, because the weekly current-state override
#: rewrites that sentence's connective prose while keeping the same claim.
#: Both wordings the repository has used are accepted:
#:   "The repository migration graph is a single Alembic head, `<head>` —
#:    verified at this tip by resolving all `<n>` revision files"
#:   "The migration graph is a single Alembic head, `<head>`, across
#:    `<n>` revision files — re-verified at this tip by …"
CURRENT_PHASE_CLAIM = re.compile(
    r"migration graph is a single Alembic head,\s*"
    r"`(?P<head>[0-9a-f]{12})`"
    r"[^.]*?\b(?P<revision_count>\d+)\s+revision files"
)


def _literal_assignment(tree: ast.Module, name: str) -> object:
    """Mirror the migration suite's parser for Alembic graph metadata."""
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


def _migration_metadata() -> list[tuple[str, object]]:
    config = configparser.ConfigParser(interpolation=None)
    config.read(ALEMBIC_CONFIG_PATH)
    configured_location = config.get("alembic", "script_location")
    script_location = Path(
        configured_location.replace("%(here)s", str(ALEMBIC_CONFIG_PATH.parent))
    ).resolve()

    metadata: list[tuple[str, object]] = []
    for path in sorted((script_location / "versions").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        revision = _literal_assignment(tree, "revision")
        down_revision = _literal_assignment(tree, "down_revision")
        assert isinstance(revision, str)
        metadata.append((revision, down_revision))
    return metadata


def _resolved_heads(metadata: list[tuple[str, object]]) -> set[str]:
    revisions = {revision for revision, _ in metadata}
    referenced: set[str] = set()
    for _, down_revision in metadata:
        if isinstance(down_revision, str):
            referenced.add(down_revision)
        elif isinstance(down_revision, (tuple, list)):
            assert all(isinstance(parent, str) for parent in down_revision)
            referenced.update(down_revision)
        else:
            assert down_revision is None
    return revisions - referenced


def _section(document: str, heading: str) -> str:
    match = re.search(
        rf"^{re.escape(heading)}\n(?P<body>.*?)(?=^## |\Z)",
        document,
        flags=re.MULTILINE | re.DOTALL,
    )
    assert match is not None, f"missing authoritative section: {heading}"
    return match.group("body")


def test_current_phase_publishes_the_resolved_migration_head_and_count() -> None:
    """The current claim must advance whenever the Alembic graph advances."""
    revisions = _migration_metadata()
    heads = sorted(_resolved_heads(revisions))
    assert len(heads) == 1, f"expected exactly one Alembic head, got {heads}"

    current_phase = _section(
        CURRENT_STATE_PATH.read_text(encoding="utf-8"), "## Current phase"
    )
    claims = list(CURRENT_PHASE_CLAIM.finditer(current_phase))
    assert len(claims) == 1, (
        "expected exactly one authoritative migration claim in Current phase, "
        f"found {len(claims)}"
    )

    published = claims[0]
    assert published.group("head") == heads[0], (
        f"published migration head {published.group('head')} does not match "
        f"resolved Alembic head {heads[0]}"
    )
    assert int(published.group("revision_count")) == len(revisions), (
        f"published revision count {published.group('revision_count')} does not "
        f"match the {len(revisions)} revisions resolved from Alembic metadata"
    )
