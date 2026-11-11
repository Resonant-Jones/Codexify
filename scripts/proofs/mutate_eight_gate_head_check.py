#!/usr/bin/env python3
"""Mutation check for the eight-gate self-check's migration-head comparison.

The self-check asserts that the harness under test computes the checkout's
single Alembic head from its source. That assertion is only worth anything
if it can fail. This harness proves four things about it:

1. **It catches a wrong head.** Mutating the harness's own
   ``_read_checkout_head`` to return a stale revision must make the
   self-check fail.
2. **It does not go stale.** The expected head is computed from the
   migration source at run time, so adding a revision that supersedes the
   current head moves the expected head with it. A pinned literal would not
   move, which is the regression this replaces.
3. **It fails closed.** A source with two heads has no single head, and the
   computation must report none rather than picking one.
4. **It agrees with Alembic.** The independent source-level computation must
   name the same head Alembic's own revision map names.

Every mutation starts from the pristine file, so one cannot mask or compose
with the next, and every file is restored byte-for-byte whether the mutation
was caught or not.

Run:

    python scripts/proofs/mutate_eight_gate_head_check.py
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
OPS_DIR = REPO_ROOT / "scripts" / "ops"
EVIDENCE = OPS_DIR / "eight_gate_evidence.py"
SELFCHECK = OPS_DIR / "eight_gate_evidence_selfcheck.py"
VERSIONS = REPO_ROOT / "guardian" / "db" / "migrations" / "versions"

STALE_HEAD = "a7d4c9e2f1b3"

FAILURES: list[str] = []
CHECKS = 0


def check(condition: bool, label: str) -> None:
    global CHECKS
    CHECKS += 1
    if not condition:
        FAILURES.append(label)
        print(f"  FAIL  {label}")
    else:
        print(f"  ok    {label}")


def run_selfcheck() -> tuple[int, str]:
    """Run the self-check in a subprocess and return (exit code, output)."""
    completed = subprocess.run(
        [sys.executable, str(SELFCHECK)],
        capture_output=True,
        text=True,
        cwd=str(REPO_ROOT),
        timeout=900,
    )
    return completed.returncode, completed.stdout + completed.stderr


def load_selfcheck_module():
    sys.path.insert(0, str(OPS_DIR))
    try:
        import eight_gate_evidence_selfcheck as sc

        return sc
    finally:
        sys.path.remove(str(OPS_DIR))


def main() -> int:
    originals = {
        EVIDENCE: EVIDENCE.read_bytes(),
        SELFCHECK: SELFCHECK.read_bytes(),
    }

    try:
        # -- 1. the check catches a harness that computes the wrong head ----
        print("mutation 1: the harness computes a stale head")
        mutated = originals[EVIDENCE].decode("utf-8")
        marker = '    return {\n        "head": heads[0] if len(heads) == 1 else None,'
        assert marker in mutated, "the harness's head return was not found"
        mutated = mutated.replace(
            marker,
            '    return {\n        "head": "%s",' % STALE_HEAD,
            1,
        )
        EVIDENCE.write_text(mutated, encoding="utf-8")
        try:
            code, output = run_selfcheck()
        finally:
            EVIDENCE.write_bytes(originals[EVIDENCE])
        check(
            "the evaluated checkout's single head is computed from its source"
            in output
            and "failed:" in output,
            "a harness that computes the wrong head is caught",
        )
        check(
            code != 0,
            "the self-check exits non-zero when the harness computes the wrong head",
        )

        sc = load_selfcheck_module()

        # -- 2. the expected head follows the source ------------------------
        print("mutation 2: a new revision supersedes the current head")
        real = sc._source_level_head()
        check(
            isinstance(real["head"], str) and len(real["head"]) == 12,
            "the real migration source has exactly one head",
        )
        moved = sc._head_from_graph({**{real["head"]: []}, "deadbeefcafe": [real["head"]]})
        check(
            moved["head"] == "deadbeefcafe",
            "a superseding revision moves the expected head with it",
        )
        check(
            moved["revisions"] == 2,
            "the new revision is counted",
        )

        # -- 3. two heads fail closed --------------------------------------
        print("mutation 3: a second head appears in the source")
        two = sc._head_from_graph(
            {
                real["head"]: [],
                "deadbeefcafe": [real["head"]],
                "cafefeeddead": [],
            }
        )
        check(
            two["head"] is None,
            "a source with two heads reports no head rather than picking one",
        )
        check(
            len(two["heads"]) == 2,
            "both heads are reported",
        )

        # -- 4. it agrees with Alembic's own revision map -------------------
        print("baseline: the source-level computation agrees with Alembic")
        try:
            from alembic.config import Config
            from alembic.script import ScriptDirectory

            config = Config(str(REPO_ROOT / "backend" / "alembic.ini"))
            script = ScriptDirectory.from_config(config)
            alembic_heads = list(script.get_heads())
        except Exception as exc:  # pragma: no cover - environment specific
            alembic_heads = None
            print(f"  (alembic unavailable: {exc})")
        if alembic_heads is not None:
            check(
                real["heads"] == sorted(alembic_heads),
                "the independently computed head is the head Alembic names",
            )
            check(
                real["revisions"] == len(list(script.walk_revisions())),
                "the revision count agrees with Alembic's",
            )

        # -- 5. the pristine self-check still passes ------------------------
        print("baseline: the pristine self-check passes")
        code, output = run_selfcheck()
        check(code == 0, "the self-check exits zero")
        check(
            "failed:" not in output,
            "the self-check reports no failed check",
        )
        tally = re.search(r"(\d+)/(\d+) checks passed", output)
        check(
            tally is not None and tally.group(1) == tally.group(2),
            "the self-check reports every check passing",
        )
    finally:
        for path, content in originals.items():
            path.write_bytes(content)

    print()
    print(f"{CHECKS - len(FAILURES)}/{CHECKS} checks passed")
    if FAILURES:
        for failure in FAILURES:
            print(f"  failed: {failure}")
        return 1
    print("PASS: every mutation behaved as the check claims")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
