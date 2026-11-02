#!/usr/bin/env python3
"""Generate the Codexify qualification registry from repository evidence.

`docs/qualification/registry.json` is the dashboard-facing projection of
qualification status. The `docs/qualification/README.md` contract requires
that projection to summarize evidence rather than be hand-maintained, so this
script derives it from the rubrics and run receipts in the repository.

Two modes are supported:

* default — write the projected registry to `docs/qualification/registry.json`.
* `--check` — project the registry and compare it against the committed file
  without writing. A non-zero exit means the committed registry has drifted
  from the evidence it claims to summarize. This is the CI gate.

The generator never edits rubrics, run receipts, or any other evidence. It
only projects them.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
QUALIFICATION_DIR = Path("docs/qualification")
REGISTRY_PATH = QUALIFICATION_DIR / "registry.json"

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_INPUT_ERROR = 2

if str(DEFAULT_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(DEFAULT_REPO_ROOT))

from scripts.qualification.lib.freshness import GitHistory  # noqa: E402
from scripts.qualification.lib.parsing import QualificationParseError  # noqa: E402
from scripts.qualification.lib.projection import (  # noqa: E402
    build_registry,
    discover_receipts,
    discover_rubrics,
)


def _relative_to_root(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except (OSError, ValueError):
        return path.name


def generate(
    repo_root: Path,
    *,
    tip_ref: str = "HEAD",
) -> tuple[dict, tuple[str, ...], str]:
    """Project the registry for the repository at `repo_root`.

    Returns the projected registry, any warnings, and the tip SHA the
    projection describes.
    """
    qualification_dir = repo_root / QUALIFICATION_DIR
    rubrics_dir = qualification_dir / "rubrics"
    runs_dir = qualification_dir / "runs"

    if not rubrics_dir.is_dir():
        raise QualificationParseError(
            "rubrics_directory_missing",
            f"expected a rubrics directory at {rubrics_dir}",
        )

    history = GitHistory(repo_root)
    tip_sha = history.resolve_commit(tip_ref)
    if tip_sha is None:
        raise QualificationParseError(
            "tip_revision_unresolvable",
            f"could not resolve revision '{tip_ref}' in the repository",
        )

    rubrics = discover_rubrics(rubrics_dir, repo_root)
    receipts = discover_receipts(runs_dir, repo_root)
    result = build_registry(
        rubrics, receipts, repo_root=repo_root, tip_sha=tip_sha, history=history
    )
    return result.registry, result.warnings, tip_sha


def _serialize(registry: dict) -> str:
    """Serialize the registry the way it is stored on disk."""
    return json.dumps(registry, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the Codexify qualification registry from repository evidence."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail when the committed registry has drifted from the projection",
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="repository root to project from",
    )
    parser.add_argument(
        "--tip-ref",
        default="HEAD",
        help="revision the registry should describe (default: HEAD)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit the projected registry to stdout instead of writing it",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    registry_path = repo_root / REGISTRY_PATH

    try:
        registry, warnings, tip_sha = generate(repo_root, tip_ref=args.tip_ref)
    except QualificationParseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    for warning in warnings:
        print(f"WARNING: {warning}", file=sys.stderr)

    serialized = _serialize(registry)

    if args.as_json:
        print(serialized, end="")
        return EXIT_OK

    if args.check:
        if not registry_path.is_file():
            print(
                f"DRIFT: {REGISTRY_PATH} does not exist but the repository "
                "projects a qualification registry.",
                file=sys.stderr,
            )
            return EXIT_DRIFT
        committed = registry_path.read_text(encoding="utf-8")
        if committed != serialized:
            print(
                f"DRIFT: {_relative_to_root(registry_path, repo_root)} does not "
                f"match the registry projected from repository evidence "
                f"(tip {tip_sha}).",
                file=sys.stderr,
            )
            print(
                "Run scripts/qualification/generate_registry.py and commit the "
                "result.",
                file=sys.stderr,
            )
            return EXIT_DRIFT
        print(
            f"OK: {_relative_to_root(registry_path, repo_root)} matches the "
            f"projection at tip {tip_sha}."
        )
        return EXIT_OK

    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(serialized, encoding="utf-8")
    print(
        f"Wrote {_relative_to_root(registry_path, repo_root)} "
        f"({len(registry['qualifications'])} qualification surface(s), "
        f"tip {tip_sha})."
    )
    return EXIT_OK


if __name__ == "__main__":
    sys.exit(main())
