"""Rebind DLG canonical node records to a specific repository revision.

The DLG corpus records, per canonical document, a `content_hash` and a
`freshness.verified_commit`. For a long time those two fields were updated
by hand, and they were allowed to drift apart: a hash could be refreshed to
match whatever bytes happened to be in a working tree while the declared
`verified_commit` stayed on an older revision. The node then claimed to be
verified against a revision whose bytes had never been hashed.

This module makes the pairing atomic and revision-scoped:

* the hash is computed from the canonical bytes **at the revision**, read
  from the Git object database;
* `verified_commit` is set to that same revision in the same write;
* a node whose source changed after its verified commit is reported as
  stale rather than silently rehashed.

Rebinding is therefore an explicit, auditable act: "this node's claim is
now bound to this revision." It is never a side effect of running the
validator from a different worktree.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence

NODES_RELATIVE_DIR = Path("docs/knowledge-graph/nodes")
SHA_LENGTH = 40


class RebindError(RuntimeError):
    """A node could not be rebound to the requested revision."""


@dataclass(frozen=True)
class RebindOutcome:
    """The result of rebinding one node."""

    document_id: str
    path: str
    previous_hash: str
    previous_verified_commit: str | None
    new_hash: str
    new_verified_commit: str
    changed: bool
    status: str
    detail: str = ""
    source_changed_since_verified: bool = False

    @property
    def changed_fields(self) -> tuple[str, ...]:
        fields: list[str] = []
        if self.previous_hash != self.new_hash:
            fields.append("content_hash")
        if self.previous_verified_commit != self.new_verified_commit:
            fields.append("freshness.verified_commit")
        return tuple(fields)


def _run_git(repository_root: Path, *args: str) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["git", "-C", str(repository_root), *args],
        capture_output=True,
        check=False,
    )


def _blob_bytes(repository_root: Path, revision: str, path: str) -> bytes | None:
    """Return the bytes of `path` as recorded at `revision`, or None."""
    completed = _run_git(repository_root, "cat-file", "blob", f"{revision}:{path}")
    if completed.returncode != 0:
        return None
    return completed.stdout


def _resolve_commit(repository_root: Path, revision: str) -> str:
    """Resolve `revision` to a full SHA, raising when it cannot be resolved."""
    completed = _run_git(repository_root, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if completed.returncode != 0:
        raise RebindError(f"Cannot resolve revision '{revision}' in this repository.")
    resolved = completed.stdout.decode("utf-8", "replace").strip()
    if len(resolved) != SHA_LENGTH:
        raise RebindError(f"Resolved revision '{revision}' is not a full commit SHA.")
    return resolved


def _write_node(path: Path, node: dict[str, Any]) -> None:
    """Write a node back in place.

    This host denies `unlink(2)` and `rename(2)` for paths under the
    repository, so the usual same-directory atomic replace
    (`os.replace` over a temporary file) cannot be used here. The write is
    therefore a truncate-in-place of the existing file, which preserves the
    inode and its mode. A crash mid-write would leave a partial file, so
    the payload is serialized and validated in full before the file is
    opened.
    """
    payload = json.dumps(node, indent=2, sort_keys=False, ensure_ascii=False) + "\n"
    # Serialize first so a failure cannot leave a half-written node.
    encoded = payload.encode("utf-8")
    json.loads(encoded.decode("utf-8"))

    with open(path, "wb") as handle:
        handle.write(encoded)
        handle.flush()
        os.fsync(handle.fileno())


def rebind_node(
    repository_root: Path,
    node_path: Path,
    *,
    revision: str,
    commit: str,
    dry_run: bool = False,
) -> RebindOutcome:
    """Rebind one node's hash and verified_commit to `revision`.

    The new hash is the hash of the canonical source bytes **at that
    revision**. The node's `freshness.verified_commit` is set to the same
    revision in the same write, so the two can no longer disagree.

    Rebinding is a mechanical act: it records "these bytes, at this
    revision". It is not a claim that a human re-reviewed the document.
    The `freshness.state` field is left untouched, so a node that was
    already marked stale stays stale until a reviewer says otherwise.
    """
    node = json.loads(node_path.read_text(encoding="utf-8"))
    document_id = str(node.get("document_id", ""))
    source_path = str(node.get("path", ""))
    if not source_path:
        raise RebindError(f"Node '{document_id}' does not declare a canonical path.")

    source_bytes = _blob_bytes(repository_root, revision, source_path)
    if source_bytes is None:
        raise RebindError(
            f"Canonical source '{source_path}' does not exist at revision '{commit}'."
        )

    new_hash = hashlib.sha256(source_bytes).hexdigest()
    previous_hash = str(node.get("content_hash", ""))
    freshness = node.get("freshness")
    previous_commit = (
        freshness.get("verified_commit") if isinstance(freshness, dict) else None
    )

    previous_bytes = (
        _blob_bytes(repository_root, previous_commit, source_path)
        if isinstance(previous_commit, str) and previous_commit
        else None
    )
    source_changed_since_verified = (
        previous_bytes is not None and previous_bytes != source_bytes
    )

    if not isinstance(freshness, dict):
        freshness = {}
        node["freshness"] = freshness
    freshness["verified_commit"] = commit
    node["content_hash"] = new_hash

    changed = previous_hash != new_hash or previous_commit != commit
    status = "rebound" if changed else "unchanged"
    detail = ""
    if previous_commit and previous_commit != commit:
        if previous_hash != new_hash:
            detail = (
                f"verified_commit moved from {previous_commit[:9]} to {commit[:9]} "
                "and content_hash was recomputed from the bytes at that revision."
            )
        else:
            detail = (
                f"verified_commit moved from {previous_commit[:9]} to {commit[:9]}; "
                "the source bytes at that revision already matched the recorded hash."
            )
        if source_changed_since_verified:
            detail += (
                " The canonical source changed after the previously recorded "
                "revision, so freshness.state should be reviewed by a human."
            )

    if changed and not dry_run:
        _write_node(node_path, node)

    return RebindOutcome(
        document_id=document_id,
        path=source_path,
        previous_hash=previous_hash,
        previous_verified_commit=previous_commit,
        new_hash=new_hash,
        new_verified_commit=commit,
        changed=changed,
        status=status,
        detail=detail,
        source_changed_since_verified=source_changed_since_verified,
    )


def rebind_corpus(
    repository_root: Path,
    *,
    revision: str,
    node_ids: Iterable[str] | None = None,
    dry_run: bool = False,
) -> list[RebindOutcome]:
    """Rebind every canonical node (or the named subset) to `revision`.

    Nodes whose canonical source does not exist at that revision are
    reported as an error rather than skipped, because a node that cannot
    name its source at the revision it claims is exactly the condition this
    module exists to prevent.
    """
    commit = _resolve_commit(repository_root, revision)
    node_dir = repository_root / NODES_RELATIVE_DIR
    if not node_dir.is_dir():
        raise RebindError(f"Canonical DLG node directory is missing: {NODES_RELATIVE_DIR}")

    wanted = set(node_ids) if node_ids is not None else None
    outcomes: list[RebindOutcome] = []
    for node_file in sorted(node_dir.glob("*.json")):
        node = json.loads(node_file.read_text(encoding="utf-8"))
        document_id = str(node.get("document_id", ""))
        if wanted is not None and document_id not in wanted:
            continue
        outcomes.append(
            rebind_node(
                repository_root,
                node_file,
                revision=commit,
                commit=commit,
                dry_run=dry_run,
            )
        )
    return outcomes


def describe_outcomes(outcomes: Sequence[RebindOutcome]) -> list[str]:
    """Render human-readable lines for a set of rebind outcomes."""
    lines: list[str] = []
    for outcome in outcomes:
        fields = outcome.changed_fields
        if not fields:
            lines.append(f"  unchanged  {outcome.document_id}")
            continue
        lines.append(
            f"  {outcome.status:9s} {outcome.document_id} "
            f"({', '.join(fields)} -> {outcome.new_verified_commit[:9]})"
        )
        if outcome.detail:
            lines.append(f"            {outcome.detail}")
    return lines
