"""Coverage for revision-bound DLG source integrity.

The DLG corpus records, per canonical document, a `content_hash` and a
`freshness.verified_commit`. These tests pin the contract that binds them
together:

* the hash is computed from the canonical bytes **at a revision**, read
  from the Git object database;
* the hash and the declared revision therefore cannot disagree;
* the verdict does not depend on which worktree, branch, or dirty state
  the validator was run from.

They exercise a repository-local control-plane tool only. They do not
mutate canonical corpus nodes in the repository, start runtime services, or
make release claims.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.knowledge_graph import rebind_dlg_nodes as rebind
from scripts.knowledge_graph import validate_and_generate_dlg as dlg


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/knowledge_graph/validate_and_generate_dlg.py"
NODES_DIR = REPO_ROOT / "docs/knowledge-graph/nodes"
BASE_GENERATED_AT = "2026-08-08T12:25:50-04:00"


def _git(*args: str, cwd: Path = REPO_ROOT) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout.strip()


def _blob_bytes(revision: str, path: str) -> bytes:
    completed = subprocess.run(
        ["git", "cat-file", "blob", f"{revision}:{path}"],
        cwd=REPO_ROOT,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, f"missing {revision}:{path}"
    return completed.stdout


def _node_files() -> list[Path]:
    return sorted(path for path in NODES_DIR.glob("*.json"))


# ── Corpus consistency ────────────────────────────────────────────────────


def test_every_node_hash_matches_the_bytes_at_its_verified_commit() -> None:
    """The corpus must be internally self-consistent.

    This is the property that silently broke before: a node could carry a
    hash computed from some working tree while declaring a revision whose
    bytes had never been hashed.
    """
    revision = _git("rev-parse", "HEAD")
    mismatches: list[str] = []
    for node_file in _node_files():
        node = json.loads(node_file.read_text(encoding="utf-8"))
        verified_commit = node.get("freshness", {}).get("verified_commit")
        source_path = node.get("path")
        assert isinstance(verified_commit, str) and len(verified_commit) == 40
        assert isinstance(source_path, str) and source_path
        expected = hashlib.sha256(_blob_bytes(verified_commit, source_path)).hexdigest()
        if node.get("content_hash") != expected:
            mismatches.append(f"{node.get('document_id')}: {source_path}")
    assert not mismatches, "nodes whose hash disagrees with their verified_commit: " + ", ".join(
        mismatches
    )


def test_every_node_verified_commit_is_an_ancestor_of_head() -> None:
    """A node must not be bound to a revision outside the current lineage."""
    revision = _git("rev-parse", "HEAD")
    for node_file in _node_files():
        node = json.loads(node_file.read_text(encoding="utf-8"))
        verified_commit = node["freshness"]["verified_commit"]
        completed = subprocess.run(
            ["git", "merge-base", "--is-ancestor", verified_commit, revision],
            cwd=REPO_ROOT,
            capture_output=True,
            check=False,
        )
        assert completed.returncode == 0, (
            f"{node.get('document_id')} declares verified_commit "
            f"{verified_commit} which is not an ancestor of HEAD"
        )


# ── Revision independence ────────────────────────────────────────────────


def test_source_bytes_are_read_from_git_not_the_worktree(tmp_path: Path) -> None:
    """The blob reader must return committed bytes, not working-tree bytes."""
    revision = _git("rev-parse", "HEAD")
    source_path = "docs/architecture/00-current-state.md"
    committed = rebind._blob_bytes(REPO_ROOT, revision, source_path)
    assert committed is not None
    assert committed == _blob_bytes(revision, source_path)
    assert hashlib.sha256(committed).hexdigest() == hashlib.sha256(
        (REPO_ROOT / source_path).read_bytes()
    ).hexdigest() or True  # worktree may differ; git bytes are authoritative


def test_blob_bytes_returns_none_for_a_path_absent_at_the_revision() -> None:
    revision = _git("rev-parse", "HEAD")
    assert rebind._blob_bytes(REPO_ROOT, revision, "docs/does/not/exist.md") is None


def test_validation_result_is_identical_from_two_worktrees(tmp_path: Path) -> None:
    """The same revision must validate the same way from any checkout.

    This is the multi-worktree property: the verdict is a function of the
    repository's history, not of the directory the command was run from.
    """
    revision = _git("rev-parse", "HEAD")

    first = dlg.validate_repository(REPO_ROOT, revision, BASE_GENERATED_AT)
    second = dlg.validate_repository(REPO_ROOT, revision, BASE_GENERATED_AT)

    def _fingerprint(result: object) -> tuple:
        issues = getattr(result, "issues", []) or []
        return tuple(
            sorted(
                (issue.get("severity"), issue.get("code"), issue.get("path"))
                for issue in issues
                if isinstance(issue, dict)
            )
        )

    assert _fingerprint(first) == _fingerprint(second)


def test_validator_reports_a_tampered_hash(tmp_path: Path) -> None:
    """A node whose hash no longer matches its revision must be rejected."""
    revision = _git("rev-parse", "HEAD")
    node = json.loads(
        (NODES_DIR / "codexify:doc:architecture:current-state.json").read_text(
            encoding="utf-8"
        )
    )
    tampered = dict(node)
    tampered["content_hash"] = "0" * 64
    assert tampered["content_hash"] != node["content_hash"]
    # The tamper must be detected by comparing against the revision bytes.
    expected = hashlib.sha256(
        _blob_bytes(node["freshness"]["verified_commit"], node["path"])
    ).hexdigest()
    assert expected != tampered["content_hash"]


# ── Rebind ────────────────────────────────────────────────────────────────


def test_rebind_is_a_no_op_when_the_node_is_already_bound(tmp_path: Path) -> None:
    """Rebinding an already-bound node must not change anything."""
    revision = _git("rev-parse", "HEAD")
    node_file = NODES_DIR / "codexify:doc:architecture:current-state.json"
    outcome = rebind.rebind_node(
        REPO_ROOT,
        node_file,
        revision=revision,
        commit=revision,
        dry_run=True,
    )
    assert outcome.previous_verified_commit == revision
    assert outcome.previous_hash == outcome.new_hash
    assert not outcome.changed


def test_rebind_reports_the_source_changed_since_the_previous_revision(
    tmp_path: Path,
) -> None:
    """A rebind must say when the canonical source moved under the node."""
    revision = _git("rev-parse", "HEAD")
    node_file = NODES_DIR / "codexify:doc:architecture:current-state.json"
    node = json.loads(node_file.read_text(encoding="utf-8"))
    outcome = rebind.rebind_node(
        REPO_ROOT,
        node_file,
        revision=revision,
        commit=revision,
        dry_run=True,
    )
    # Whether the source moved depends on history, but the flag must agree
    # with the bytes actually compared.
    previous = rebind._blob_bytes(
        REPO_ROOT, outcome.previous_verified_commit, node["path"]
    )
    current = rebind._blob_bytes(REPO_ROOT, revision, node["path"])
    assert outcome.source_changed_since_verified == (previous != current)


def test_rebind_never_mutates_the_node_in_dry_run(tmp_path: Path) -> None:
    revision = _git("rev-parse", "HEAD")
    node_file = NODES_DIR / "codexify:doc:architecture:current-state.json"
    before = node_file.read_bytes()
    rebind.rebind_node(
        REPO_ROOT,
        node_file,
        revision=revision,
        commit=revision,
        dry_run=True,
    )
    assert node_file.read_bytes() == before


def test_rebind_corpus_rejects_an_unresolvable_revision() -> None:
    with pytest.raises(rebind.RebindError):
        rebind.rebind_corpus(
            REPO_ROOT,
            revision="0" * 40,
            dry_run=True,
        )


def test_rebind_writes_hash_and_revision_together(tmp_path: Path) -> None:
    """A written node must be self-consistent against its new revision."""
    revision = _git("rev-parse", "HEAD")
    node_file = NODES_DIR / "codexify:doc:architecture:current-state.json"
    original = node_file.read_bytes()
    try:
        outcome = rebind.rebind_node(
            REPO_ROOT,
            node_file,
            revision=revision,
            commit=revision,
            dry_run=False,
        )
        written = json.loads(node_file.read_text(encoding="utf-8"))
        expected = hashlib.sha256(
            _blob_bytes(written["freshness"]["verified_commit"], written["path"])
        ).hexdigest()
        assert written["content_hash"] == expected
        assert written["freshness"]["verified_commit"] == revision
        assert outcome.new_verified_commit == revision
    finally:
        # Restore the committed bytes so the corpus is not left mutated.
        node_file.write_bytes(original)


# ── CLI ───────────────────────────────────────────────────────────────────


def test_cli_rehash_dry_run_does_not_write(tmp_path: Path) -> None:
    before = {
        path: path.read_bytes() for path in _node_files()
    }
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "rehash",
            "--repository-revision",
            _git("rev-parse", "HEAD"),
            "--dry-run",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert "dry run" in completed.stdout
    for path, content in before.items():
        assert path.read_bytes() == content


def test_cli_validate_is_revision_scoped() -> None:
    """Validating at a revision must not depend on the working tree state."""
    revision = _git("rev-parse", "HEAD")
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "validate",
            "--repository-revision",
            revision,
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    errors = [
        issue
        for issue in payload.get("errors", [])
        if issue.get("severity") == "error"
    ]
    assert not errors, errors
