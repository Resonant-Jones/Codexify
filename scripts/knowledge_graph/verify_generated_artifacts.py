#!/usr/bin/env python3
"""Verify that the committed DLG projections and ARP packets are current.

The generated artifacts under `docs/knowledge-graph/generated/` are
*derived* projections: the DLG contract calls them "reconstructable" and
"disposable". They are pinned to a calibration revision, and the pinned
revision and timestamp are recorded in the artifacts themselves rather
than restated here.

This script reads those recorded values and asks the generators whether
regenerating at that same revision and timestamp reproduces the committed
bytes exactly. That is the question a reader of a projection needs answered:
*does this artifact still correspond to the corpus it claims to describe?*

A drift means one of two things, and both are worth failing the build for:

* the artifact was hand-edited, or the generator changed without the
  artifact being regenerated; or
* the corpus changed under the pinned revision and the projection no
  longer describes it.

Nothing here mutates the repository. It validates and reports.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]

DLG_GRAPH_PATH = Path("docs/knowledge-graph/generated/document-graph.json")
ARP_PACKET_DIR = Path("docs/knowledge-graph/generated/agent-reading-packets")
ARP_GRAPH_SOURCE = Path("docs/knowledge-graph/generated/document-graph.json")

EXIT_OK = 0
EXIT_DRIFT = 1
EXIT_INPUT_ERROR = 2


class VerificationError(RuntimeError):
    """The verification could not be performed."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise VerificationError(f"Cannot read {path}: {exc}") from exc
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise VerificationError(f"{path} is not valid JSON: {exc}") from exc
    if not isinstance(parsed, dict):
        raise VerificationError(f"{path} must contain a JSON object")
    return parsed


def _run_git(repo_root: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", "-C", str(repo_root), *args],
        capture_output=True,
        check=False,
        text=True,
    )


def _resolve_revision(repo_root: Path, revision: str) -> str:
    """Resolve a revision to a full SHA, requiring it to exist locally."""
    completed = _run_git(repo_root, "rev-parse", "--verify", f"{revision}^{{commit}}")
    if completed.returncode != 0:
        raise VerificationError(
            f"Pinned calibration revision {revision} does not resolve to a commit "
            "in this checkout. The projections pin a revision that the "
            "repository no longer contains, so they cannot be verified."
        )
    return completed.stdout.strip()


def _summarize_generator_output(output: str) -> list[str]:
    """Extract the salient failure lines from a generator's JSON output.

    The generators emit a full validation report. Only the error lines
    matter for a build log, so the report is reduced to them.
    """
    lines: list[str] = []
    try:
        payload = json.loads(output)
    except (json.JSONDecodeError, TypeError):
        return [line for line in output.splitlines() if line.strip()][-40:]

    errors = payload.get("errors")
    if isinstance(errors, list):
        for issue in errors:
            if not isinstance(issue, dict):
                continue
            if issue.get("severity") != "error":
                continue
            lines.append(
                f"{issue.get('code', 'error')}: {issue.get('message', '')}"
                + (f" [{issue.get('path')}]" if issue.get("path") else "")
            )
    if not lines:
        # The generator may fail without an errors array (for example the
        # ARP calibration guards, which raise a plain message).
        for key in ("message", "error", "detail"):
            value = payload.get(key)
            if isinstance(value, str) and value.strip():
                lines.append(value.strip())
                break
    if not lines:
        lines = [line for line in output.splitlines() if line.strip()][-20:]
    return lines


def _run_generator(
    repo_root: Path, script: str, args: list[str]
) -> subprocess.CompletedProcess[str]:
    """Run a generator or checker as a script, from the repository root."""
    return subprocess.run(
        [sys.executable, str(repo_root / script), *args],
        cwd=repo_root,
        capture_output=True,
        check=False,
        text=True,
    )


def verify_dlg_projections(repo_root: Path) -> list[str]:
    """Check that the DLG projections regenerate byte-identically."""
    graph_path = repo_root / DLG_GRAPH_PATH
    if not graph_path.is_file():
        raise VerificationError(f"Missing DLG projection: {DLG_GRAPH_PATH}")
    graph = _read_json(graph_path)

    revision = graph.get("repository_revision")
    generated_at = graph.get("generated_at")
    if not isinstance(revision, str) or not isinstance(generated_at, str):
        raise VerificationError(
            f"{DLG_GRAPH_PATH} does not record repository_revision and "
            "generated_at, so the calibration cannot be verified."
        )
    _resolve_revision(repo_root, revision)

    completed = _run_generator(
        repo_root,
        "scripts/knowledge_graph/validate_and_generate_dlg.py",
        [
            "check-generated",
            "--repository-root",
            str(repo_root),
            "--repository-revision",
            revision,
            "--generated-at",
            generated_at,
        ],
    )
    if completed.returncode != 0:
        return [
            f"DLG projections drifted from the corpus at calibration revision "
            f"{revision[:9]}:",
            *_summarize_generator_output(completed.stdout or completed.stderr),
            "Regenerate with:",
            "  python scripts/knowledge_graph/validate_and_generate_dlg.py "
            f"generate --repository-revision {revision} --generated-at "
            f"'{generated_at}'",
        ]
    return []


def verify_arp_packets(repo_root: Path) -> list[str]:
    """Check that the ARP packets regenerate byte-identically."""
    packet_dir = repo_root / ARP_PACKET_DIR
    if not packet_dir.is_dir():
        raise VerificationError(f"Missing ARP packet directory: {ARP_PACKET_DIR}")
    packets = sorted(path for path in packet_dir.glob("*.json"))
    if not packets:
        raise VerificationError(f"No ARP packets found under {ARP_PACKET_DIR}")

    graph_path = repo_root / ARP_GRAPH_SOURCE
    if not graph_path.is_file():
        raise VerificationError(f"Missing DLG projection: {ARP_GRAPH_SOURCE}")
    graph = _read_json(graph_path)
    created_at = graph.get("generated_at")
    # The ARP packets carry their own created_at, which differs from the
    # projection's generated_at by the calibration run order.
    for packet in packets:
        payload = _read_json(packet)
        if isinstance(payload.get("created_at"), str):
            created_at = payload["created_at"]
            break
    if not isinstance(created_at, str):
        raise VerificationError(
            "No ARP packet records created_at, so the calibration cannot be "
            "verified."
        )

    completed = _run_generator(
        repo_root,
        "scripts/knowledge_graph/generate_representative_arps.py",
        [
            "check-generated",
            "--repository-root",
            str(repo_root),
            "--created-at",
            created_at,
        ],
    )
    if completed.returncode != 0:
        return [
            f"ARP packets drifted from the corpus at calibration revision "
            f"{str(graph.get('repository_revision'))[:9]}:",
            *_summarize_generator_output(completed.stdout or completed.stderr),
            "Regenerate with:",
            "  python scripts/knowledge_graph/generate_representative_arps.py "
            f"generate --created-at '{created_at}'",
        ]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Verify that the committed DLG projections and ARP packets still "
            "correspond to the corpus they claim to describe."
        )
    )
    parser.add_argument(
        "--repo-root",
        default=str(DEFAULT_REPO_ROOT),
        help="repository root to verify",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="emit a machine-readable result",
    )
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    problems: list[str] = []
    try:
        problems.extend(verify_dlg_projections(repo_root))
        problems.extend(verify_arp_packets(repo_root))
    except VerificationError as exc:
        if args.as_json:
            print(
                json.dumps(
                    {
                        "result": "error",
                        "message": str(exc),
                    },
                    indent=2,
                    sort_keys=True,
                )
            )
        else:
            print(f"ERROR: {exc}", file=sys.stderr)
        return EXIT_INPUT_ERROR

    if args.as_json:
        print(
            json.dumps(
                {
                    "result": "pass" if not problems else "fail",
                    "problem_count": len(problems),
                    "problems": problems,
                },
                indent=2,
                sort_keys=True,
            )
        )
    elif problems:
        for problem in problems:
            print(problem, file=sys.stderr)
    else:
        print(
            "OK: DLG projections and ARP packets are current with the corpus "
            "at their recorded calibration revision."
        )
    return EXIT_OK if not problems else EXIT_DRIFT


if __name__ == "__main__":
    sys.exit(main())
