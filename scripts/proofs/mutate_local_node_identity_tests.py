"""Mutation-check the local-node identity tests.

Each mutation breaks exactly one property that a named test claims to
pin.  The check passes only if every mutation is caught by the test that
names it -- and it restores every file it touches from a byte-verified
backup, whether the mutation was caught or not.

Run it from the repository root:

    python scripts/proofs/mutate_local_node_identity_tests.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SERVICE = REPO_ROOT / "guardian" / "messaging" / "service.py"
MODELS = REPO_ROOT / "guardian" / "db" / "models.py"
TEST = "tests/routes/test_local_node_identity.py"

# Each mutation: (name, file, find, replace, test that must fail).
MUTATIONS: list[tuple[str, Path, str, str, str]] = [
    (
        "the resolver infers the local node from row age again",
        SERVICE,
        """    node = session.scalar(
        select(ThreadSpaceNode)
        .where(ThreadSpaceNode.is_local.is_(True))
        .limit(1)
    )
    if node is not None:
        return node

    name = (os.getenv(_LOCAL_NODE_NAME_ENV) or "").strip() or (_DEFAULT_LOCAL_NODE_NAME)""",
        """    node = session.scalar(
        select(ThreadSpaceNode)
        .order_by(ThreadSpaceNode.created_at.asc(), ThreadSpaceNode.node_id.asc())
        .limit(1)
    )
    if node is not None:
        return node

    name = (os.getenv(_LOCAL_NODE_NAME_ENV) or "").strip() or (_DEFAULT_LOCAL_NODE_NAME)""",
        "test_a_foreign_row_in_the_same_tick_is_never_adopted",
    ),
    (
        "the resolver stops marking the node it mints as local",
        SERVICE,
        """        status="active",
        is_local=True,
    )""",
        """        status="active",
        is_local=False,
    )""",
        "test_the_resolver_mints_exactly_one_local_node",
    ),
    (
        "the database no longer refuses a second local node",
        MODELS,
        """        Index(
            "threadspace_nodes_one_local_idx",
            "is_local",
            unique=True,
            sqlite_where=text("is_local = 1"),
            postgresql_where=text("is_local IS true"),
        ),""",
        "",
        "test_the_database_refuses_a_second_local_node",
    ),
    (
        "the resolver adopts an existing foreign row instead of minting one",
        SERVICE,
        """    node = session.scalar(
        select(ThreadSpaceNode)
        .where(ThreadSpaceNode.is_local.is_(True))
        .limit(1)
    )
    if node is not None:
        return node""",
        """    node = session.scalar(
        select(ThreadSpaceNode)
        .where(ThreadSpaceNode.is_local.is_(False))
        .limit(1)
    )
    if node is not None:
        return node""",
        "test_a_foreign_row_is_never_minted_as_local",
    ),
]


def _run(test_name: str) -> tuple[bool, str]:
    """Run one test; return (failed, output tail)."""
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "-q",
            "--disable-warnings",
            "-p",
            "no:cacheprovider",
            f"{TEST}::{test_name}",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    return completed.returncode != 0, (completed.stdout or "")[-800:]


def main() -> int:
    backups: dict[Path, bytes] = {}
    results: list[tuple[str, str, bool]] = []

    try:
        for name, path, find, replace, test_name in MUTATIONS:
            original = backups.setdefault(path, path.read_bytes())
            text = original.decode()
            if find not in text:
                print(f"SKIP  {name}: the pattern is not present")
                results.append((name, test_name, False))
                continue

            # Each mutation starts from the pristine file, so one mutation
            # cannot mask or compose with the next.
            path.write_text(text.replace(find, replace, 1), encoding="utf-8")
            failed, output = _run(test_name)
            caught = failed
            results.append((name, test_name, caught))
            verdict = "caught" if caught else "NOT CAUGHT"
            print(f"{verdict:>9}  {name}  ->  {test_name}")
            if not caught:
                print(output)
    finally:
        for path, original in backups.items():
            path.write_bytes(original)
            restored = path.read_bytes()
            assert restored == original, f"failed to restore {path} byte-for-byte"
        if backups:
            print(f"\nrestored {len(backups)} file(s) byte-for-byte")

    print()
    print("MUTATION CHECK")
    print("---------------")
    for name, test_name, caught in results:
        print(f"{'PASS' if caught else 'FAIL'}  {test_name}  <-  {name}")

    uncaught = [n for n, _, c in results if not c]
    if uncaught:
        print(f"\n{len(uncaught)} mutation(s) were not caught")
        return 1
    print(f"\nPASS: every mutation was caught by the test that names it ({len(results)}/{len(results)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
