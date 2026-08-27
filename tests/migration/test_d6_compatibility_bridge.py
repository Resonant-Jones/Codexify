"""Focused tests for the d6f7a8b9c0d1 compatibility-bridge repair.

These tests are static: they verify blob identity, migration metadata, token
vocabulary, and Alembic graph structure without touching any database. The
disposable-database convergence and data-preservation evidence lives in the
dated proof artifact, not here.
"""

from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from alembic.config import Config
from alembic.script import ScriptDirectory

REPO_ROOT = Path(__file__).resolve().parents[2]
VERSIONS_DIR = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"

D6_REVISION = "d6f7a8b9c0d1"
SIBLING_HEAD = "6e2b9c4a7d1f"
MERGE_REVISION = "8f3c1a7d2e6b"
NORMALIZATION_REVISION = "9d4c2a7e1b6f"
ORIGIN_SYSTEM_REVISION = "1c0a2b3c4d5e"
CANONICAL_HEAD = "9c66e490a42b"

D6_FILENAME = "d6f7a8b9c0d1_add_threadspace_node_membership.py"
MERGE_FILENAME = "8f3c1a7d2e6b_merge_d6f7a8b9c0d1_compatibility.py"
NORMALIZATION_FILENAME = "9d4c2a7e1b6f_normalize_account_observability_schema.py"

EXPECTED_BLOBS: dict[Path, str] = {
    REPO_ROOT
    / "guardian"
    / "threadspace"
    / "__init__.py": ("21d8f08cc06fd74f52c14cee58e2d49648c0e3d6"),
    REPO_ROOT
    / "guardian"
    / "threadspace"
    / "membership_tokens.py": ("8c332eb68dae5c558a0f47a53c48132ab2c2893a"),
    VERSIONS_DIR / D6_FILENAME: "d02f5bfa629948f5e134ef9bb9e827cf2679250b",
}

EXPECTED_TOKENS: dict[str, frozenset[str]] = {
    "NODE_STATUSES": frozenset({"active", "suspended", "archived"}),
    "NODE_MEMBERSHIP_ROLES": frozenset(
        {"node_owner", "node_operator", "node_admin", "member", "guest"}
    ),
    "MEMBERSHIP_LIFECYCLE_STATES": frozenset(
        {"invited", "active", "suspended", "revoked", "expired"}
    ),
    "INVITATION_STATES": frozenset(
        {"pending", "accepted", "declined", "revoked", "expired"}
    ),
}


def _script() -> ScriptDirectory:
    config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
    return ScriptDirectory.from_config(config)


def _git_blob_sha(path: Path) -> str:
    data = path.read_bytes()
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


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


def _function_body_statements(tree: ast.Module, name: str) -> list[ast.stmt]:
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == name:
            statements = node.body
            if (
                statements
                and isinstance(statements[0], ast.Expr)
                and isinstance(statements[0].value, ast.Constant)
                and isinstance(statements[0].value.value, str)
            ):
                statements = statements[1:]
            return statements
    raise AssertionError(f"function {name} not found")


def _ancestor_revisions(script: ScriptDirectory, rev: str) -> set[str]:
    seen: set[str] = set()
    stack = [rev]
    while stack:
        current = stack.pop()
        if current in seen:
            continue
        seen.add(current)
        down = script.get_revision(current).down_revision
        if down is None:
            continue
        if isinstance(down, str):
            stack.append(down)
        else:
            stack.extend(down)
    return seen


def test_restored_historical_blobs_match_pinned_identities() -> None:
    for path, expected in EXPECTED_BLOBS.items():
        assert path.is_file(), f"missing restored file: {path}"
        assert _git_blob_sha(path) == expected, f"blob mismatch for {path}"


def test_d6_migration_metadata_matches_historical_identity() -> None:
    tree = ast.parse((VERSIONS_DIR / D6_FILENAME).read_text())
    assert _literal_assignment(tree, "revision") == D6_REVISION
    assert _literal_assignment(tree, "down_revision") == "c1a2b3c4d5e6"
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None


def test_d6_migration_imports_expected_token_constants() -> None:
    tree = ast.parse((VERSIONS_DIR / D6_FILENAME).read_text())
    imported: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module == "guardian.threadspace.membership_tokens"
        ):
            imported.update(alias.name for alias in node.names)
    assert imported == set(EXPECTED_TOKENS)


def test_d6_module_token_values_match_historical_vocabulary() -> None:
    d6_module = _script().get_revision(D6_REVISION).module
    for name, expected in EXPECTED_TOKENS.items():
        assert getattr(d6_module, name) == expected, name


def test_token_vocabulary_renders_expected_check_constraint_values() -> None:
    from guardian.threadspace import membership_tokens

    def sql_values(values: frozenset[str]) -> str:
        return ",".join(repr(value) for value in sorted(values))

    assert (
        sql_values(membership_tokens.NODE_STATUSES) == "'active','archived','suspended'"
    )
    assert (
        sql_values(membership_tokens.NODE_MEMBERSHIP_ROLES)
        == "'guest','member','node_admin','node_operator','node_owner'"
    )
    assert (
        sql_values(membership_tokens.MEMBERSHIP_LIFECYCLE_STATES)
        == "'active','expired','invited','revoked','suspended'"
    )
    assert (
        sql_values(membership_tokens.INVITATION_STATES)
        == "'accepted','declined','expired','pending','revoked'"
    )


def test_merge_revision_has_exactly_two_intended_parents() -> None:
    merge = _script().get_revision(MERGE_REVISION)
    assert merge.revision == MERGE_REVISION
    down = merge.down_revision
    parents = {down} if isinstance(down, str) else set(down)
    assert parents == {D6_REVISION, SIBLING_HEAD}


def test_merge_revision_metadata_is_minimal() -> None:
    tree = ast.parse((VERSIONS_DIR / MERGE_FILENAME).read_text())
    assert _literal_assignment(tree, "revision") == MERGE_REVISION
    assert _literal_assignment(tree, "down_revision") == (
        D6_REVISION,
        SIBLING_HEAD,
    )
    assert _literal_assignment(tree, "branch_labels") is None
    assert _literal_assignment(tree, "depends_on") is None


def test_merge_revision_is_metadata_only() -> None:
    tree = ast.parse((VERSIONS_DIR / MERGE_FILENAME).read_text())
    for function in ("upgrade", "downgrade"):
        statements = _function_body_statements(tree, function)
        assert len(statements) == 1, f"{function} must be a single no-op"
        assert isinstance(statements[0], ast.Pass), f"{function} must be pass"


def test_final_graph_has_exactly_one_head() -> None:
    assert _script().get_heads() == [CANONICAL_HEAD]


def test_forward_ancestry_from_d6_and_sibling_to_merge_head() -> None:
    script = _script()
    ancestors = _ancestor_revisions(script, MERGE_REVISION)
    assert D6_REVISION in ancestors
    assert SIBLING_HEAD in ancestors


def test_normalization_revision_is_singleton_after_merge() -> None:
    """The account-observability compatibility-normalization revision is the
    sole successor of the metadata-only merge, and inherits the merge's full
    d6 + sibling ancestry.
    """
    script = _script()
    normalization = script.get_revision(NORMALIZATION_REVISION)
    assert normalization is not None
    down = normalization.down_revision
    parents = {down} if isinstance(down, str) else set(down)
    assert parents == {MERGE_REVISION}

    ancestors = _ancestor_revisions(script, NORMALIZATION_REVISION)
    assert MERGE_REVISION in ancestors
    assert D6_REVISION in ancestors
    assert SIBLING_HEAD in ancestors


def test_canonical_head_preserves_origin_system_and_d6_compatibility_ancestry() -> None:
    script = _script()
    origin_system = script.get_revision(ORIGIN_SYSTEM_REVISION)
    assert origin_system is not None
    assert origin_system.down_revision == NORMALIZATION_REVISION
    assert isinstance(origin_system.down_revision, str)

    canonical_head = script.get_revision(CANONICAL_HEAD)
    assert canonical_head is not None

    ancestors = _ancestor_revisions(script, CANONICAL_HEAD)
    assert ORIGIN_SYSTEM_REVISION in ancestors
    assert NORMALIZATION_REVISION in ancestors
    assert MERGE_REVISION in ancestors
    assert D6_REVISION in ancestors
    assert SIBLING_HEAD in ancestors
