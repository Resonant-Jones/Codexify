#!/usr/bin/env python3
"""Warn when runtime diagram sources drift without review marker updates.

Optional automation:
- auto-regenerate diagrams when runtime source files changed
- watch runtime source files and trigger regeneration on each save
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

RUNTIME_SOURCE_SET = {
    "docs/architecture/00-current-state.md",
    "docs/architecture/README.md",
    "docs/architecture/system-overview.md",
    "docs/architecture/flows.md",
    "docs/architecture/data-and-storage.md",
    "docs/architecture/config-and-ops.md",
    "docs/architecture/modules-and-ownership.md",
}

MARKER_FILES = {
    "docs/architecture/diagram-governance.md",
    "docs/architecture/module-diagram-coverage-matrix.md",
}

MARKER_PREFIX = "Diagram Review Marker:"
DEFAULT_MATRIX = "docs/architecture/module-diagram-coverage-matrix.md"
REGENERATE_CMD_ENV = "CODEXIFY_DIAGRAM_REGENERATE_CMD"


class CheckWarning(Exception):
    """Raised when a warning should be emitted."""


def run_git(*args: str) -> str:
    cmd = ["git", "-C", str(ROOT), *args]
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        stderr = result.stderr.strip()
        raise RuntimeError(f"git command failed: {' '.join(cmd)}\n{stderr}")
    return result.stdout


def parse_changed_file_list(output: str) -> set[str]:
    changed: set[str] = set()
    for line in output.splitlines():
        path = line.strip()
        if path:
            changed.add(path)
    return changed


def get_changed_files(
    base_ref: str | None, head_ref: str, manual: list[str]
) -> set[str]:
    if manual:
        return {p.strip() for p in manual if p.strip()}

    if base_ref:
        diff_output = run_git(
            "diff",
            "--name-only",
            "--diff-filter=ACMR",
            f"{base_ref}...{head_ref}",
            "--",
        )
        return parse_changed_file_list(diff_output)

    changed: set[str] = set()
    changed |= parse_changed_file_list(
        run_git("diff", "--name-only", "--diff-filter=ACMR", "HEAD", "--")
    )
    changed |= parse_changed_file_list(
        run_git("diff", "--name-only", "--cached", "--diff-filter=ACMR", "--")
    )
    changed |= parse_changed_file_list(
        run_git("ls-files", "--others", "--exclude-standard")
    )
    return changed


def marker_update_detected(
    changed_files: set[str],
    base_ref: str | None,
    head_ref: str,
    manual_mode: bool,
) -> bool:
    touched_markers = changed_files & MARKER_FILES
    if manual_mode:
        return bool(touched_markers)

    if touched_markers:
        return True

    marker_paths = sorted(MARKER_FILES)
    if base_ref:
        diff = run_git(
            "diff",
            "--unified=0",
            f"{base_ref}...{head_ref}",
            "--",
            *marker_paths,
        )
    else:
        diff = run_git("diff", "--unified=0", "HEAD", "--", *marker_paths)

    for line in diff.splitlines():
        if not line.startswith(("+", "-")):
            continue
        if line.startswith(("+++", "---")):
            continue
        if MARKER_PREFIX in line:
            return True
    return False


def parse_markdown_table(lines: list[str]) -> tuple[list[str], list[list[str]]]:
    table_lines = [line for line in lines if line.strip().startswith("|")]
    if len(table_lines) < 2:
        raise CheckWarning(
            "module diagram coverage matrix table is missing or malformed"
        )

    header = [
        cell.strip() for cell in table_lines[0].strip().strip("|").split("|")
    ]
    rows: list[list[str]] = []
    for raw in table_lines[2:]:
        cells = [cell.strip() for cell in raw.strip().strip("|").split("|")]
        if len(cells) != len(header):
            continue
        rows.append(cells)
    return header, rows


def validate_matrix_decisions(matrix_path: Path) -> list[str]:
    if not matrix_path.is_file():
        return [f"missing matrix file: {matrix_path}"]

    text = matrix_path.read_text(encoding="utf-8")
    header, rows = parse_markdown_table(text.splitlines())

    try:
        blast_idx = header.index("Blast Radius")
        decision_idx = header.index("Diagram Needed")
    except ValueError:
        return [
            "matrix header missing required column(s): 'Blast Radius' and 'Diagram Needed'"
        ]

    issues: list[str] = []
    allowed = {"yes", "no"}
    for row in rows:
        module = row[0]
        blast = row[blast_idx].strip().lower()
        decision = row[decision_idx].strip().lower()

        if blast == "high" and decision not in allowed:
            issues.append(
                f"high blast-radius module missing explicit diagram decision yes/no: {module}"
            )

    return issues


def evaluate_freshness(
    changed_files: set[str],
    base_ref: str | None,
    head_ref: str,
    manual_mode: bool,
    matrix_path: Path,
) -> tuple[list[str], list[str]]:
    runtime_source_changes = sorted(changed_files & RUNTIME_SOURCE_SET)
    warnings: list[str] = []

    if runtime_source_changes:
        try:
            has_marker_update = marker_update_detected(
                changed_files,
                base_ref,
                head_ref,
                manual_mode,
            )
        except RuntimeError:
            has_marker_update = False
            warnings.append(
                "unable to inspect marker diff; treat as stale until marker update is confirmed"
            )

        if not has_marker_update:
            joined = ", ".join(runtime_source_changes)
            warnings.append(
                "runtime diagram source docs changed without review marker update: "
                f"{joined}. Update 'Diagram Review Marker:' in diagram governance or "
                "module coverage matrix."
            )

    warnings.extend(validate_matrix_decisions(matrix_path))
    return runtime_source_changes, warnings


def resolve_regenerate_commands(explicit_commands: list[str]) -> list[str]:
    commands = [cmd.strip() for cmd in explicit_commands if cmd.strip()]
    env_value = os.environ.get(REGENERATE_CMD_ENV, "").strip()
    if env_value:
        commands.append(env_value)
    return commands


def run_regeneration(
    commands: list[str], trigger_paths: list[str]
) -> list[str]:
    if not commands:
        return [
            "auto-regenerate requested but no command configured. Set --regenerate-cmd "
            f"or {REGENERATE_CMD_ENV}."
        ]

    if trigger_paths:
        print(
            "INFO: runtime source changes detected: " + ", ".join(trigger_paths)
        )

    errors: list[str] = []
    for command in commands:
        print(f"INFO: running diagram regeneration command: {command}")
        result = subprocess.run(
            command,
            shell=True,
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

        if result.stdout.strip():
            print(result.stdout.rstrip())
        if result.stderr.strip():
            print(result.stderr.rstrip(), file=sys.stderr)

        if result.returncode != 0:
            errors.append(
                f"regeneration command failed (exit {result.returncode}): {command}"
            )

    return errors


def snapshot_runtime_mtimes() -> dict[str, int | None]:
    snapshot: dict[str, int | None] = {}
    for rel_path in RUNTIME_SOURCE_SET:
        path = ROOT / rel_path
        if path.is_file():
            snapshot[rel_path] = path.stat().st_mtime_ns
        else:
            snapshot[rel_path] = None
    return snapshot


def detect_runtime_source_mtime_changes(
    previous: dict[str, int | None]
) -> tuple[list[str], dict[str, int | None]]:
    changed: list[str] = []
    current = snapshot_runtime_mtimes()
    for rel_path in sorted(RUNTIME_SOURCE_SET):
        old = previous.get(rel_path)
        new = current.get(rel_path)
        if old != new:
            changed.append(rel_path)
    return changed, current


def maybe_raise(strict: bool, messages: list[str]) -> None:
    if not messages:
        return

    text = "\n".join(messages)
    if strict:
        raise CheckWarning(text)

    print("WARNING: diagram freshness check found issues:")
    print(text)


def run_watch_mode(commands: list[str], interval_seconds: float) -> int:
    if not commands:
        print(
            "ERROR: watch mode requires regeneration command(s). "
            f"Use --regenerate-cmd or set {REGENERATE_CMD_ENV}."
        )
        return 2

    print("INFO: watching runtime source set for changes...")
    print("INFO: press Ctrl+C to stop")

    previous = snapshot_runtime_mtimes()
    try:
        while True:
            time.sleep(interval_seconds)
            changed, current = detect_runtime_source_mtime_changes(previous)
            previous = current
            if not changed:
                continue

            regeneration_errors = run_regeneration(commands, changed)
            if regeneration_errors:
                print("WARNING: regeneration encountered issues:")
                for issue in regeneration_errors:
                    print(f"- {issue}")
    except KeyboardInterrupt:
        print("\nINFO: stopped watch mode")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Warn when runtime diagram source docs change without review-marker updates."
    )
    parser.add_argument(
        "--base-ref", help="Optional git base ref for diff range"
    )
    parser.add_argument(
        "--head-ref",
        default="HEAD",
        help="Optional git head ref for diff range (default: HEAD)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Exit non-zero on warnings",
    )
    parser.add_argument(
        "--changed-file",
        action="append",
        default=[],
        help="Testing override: treat path as changed without reading git diff",
    )
    parser.add_argument(
        "--matrix-path",
        default=DEFAULT_MATRIX,
        help="Path to module coverage matrix (default: docs/architecture/module-diagram-coverage-matrix.md)",
    )
    parser.add_argument(
        "--auto-regenerate",
        action="store_true",
        help="When runtime source docs changed, run regeneration command(s) before final check output.",
    )
    parser.add_argument(
        "--regenerate-cmd",
        action="append",
        default=[],
        help=(
            "Diagram regeneration shell command. Can be passed multiple times. "
            f"You can also set {REGENERATE_CMD_ENV}."
        ),
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Watch runtime source files and run regeneration command(s) on every file change.",
    )
    parser.add_argument(
        "--watch-interval",
        type=float,
        default=1.0,
        help="Watch polling interval in seconds (default: 1.0)",
    )
    args = parser.parse_args()

    regen_commands = resolve_regenerate_commands(args.regenerate_cmd)

    if args.watch:
        return run_watch_mode(regen_commands, args.watch_interval)

    manual_mode = bool(args.changed_file)

    try:
        changed_files = get_changed_files(
            args.base_ref, args.head_ref, args.changed_file
        )
    except RuntimeError as exc:
        if args.strict:
            print(str(exc), file=sys.stderr)
            return 1
        print(f"WARNING: {exc}")
        print(
            "WARNING: unable to read git diff; skipping source-change freshness check"
        )
        changed_files = set()

    matrix_path = ROOT / args.matrix_path
    runtime_source_changes, warnings = evaluate_freshness(
        changed_files,
        args.base_ref,
        args.head_ref,
        manual_mode,
        matrix_path,
    )

    if args.auto_regenerate and runtime_source_changes:
        regeneration_errors = run_regeneration(
            regen_commands, runtime_source_changes
        )
        if regeneration_errors:
            warnings.extend(regeneration_errors)
        elif not manual_mode:
            # Recompute after regeneration so marker updates are recognized.
            try:
                changed_files = get_changed_files(
                    args.base_ref, args.head_ref, args.changed_file
                )
            except RuntimeError as exc:
                warnings.append(
                    f"unable to refresh git diff after regeneration: {exc}"
                )
            else:
                runtime_source_changes, warnings = evaluate_freshness(
                    changed_files,
                    args.base_ref,
                    args.head_ref,
                    manual_mode,
                    matrix_path,
                )

    try:
        maybe_raise(args.strict, warnings)
    except CheckWarning as exc:
        print(f"ERROR: {exc}")
        return 1

    if warnings:
        return 0

    if runtime_source_changes:
        print(
            "Diagram freshness check passed: runtime source changes were accompanied by a review marker update."
        )
    else:
        print(
            "Diagram freshness check passed: no runtime source drift detected and matrix decisions are valid."
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
