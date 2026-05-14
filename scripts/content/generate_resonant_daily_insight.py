#!/usr/bin/env python3
"""Generate a deterministic Resonant Constructs Daily Insight artifact from
one or more local Markdown source files.

This script is repo-local and does not call an LLM, web service, network API,
or external publisher.  Every insight is a derived artifact from source
material already present in the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path("docs/ResonantConstructs/daily-insights/generated")
MARKDOWN_SUFFIXES = {".md", ".markdown"}

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def resolve_repo_path(raw_path: str) -> Path:
    path = Path(raw_path).expanduser()
    if path.is_absolute():
        return path.resolve()
    return (REPO_ROOT / path).resolve()


def display_path(path: Path) -> str:
    resolved = path.resolve()
    try:
        return resolved.relative_to(REPO_ROOT).as_posix()
    except ValueError:
        return str(resolved)


def is_markdown_source(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def validate_date(date_text: str) -> str:
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"invalid --date value {date_text!r}; expected YYYY-MM-DD"
        ) from exc
    return parsed.isoformat()


# ---------------------------------------------------------------------------
# source reading & validation
# ---------------------------------------------------------------------------


def read_source_text(source_path: Path) -> str:
    """Read a Markdown source file and return its text.

    Raises FileNotFoundError or ValueError if the source is missing or empty.
    """
    try:
        text = source_path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise FileNotFoundError(
            f"source file not found: {source_path}"
        ) from exc
    except UnicodeDecodeError as exc:
        raise ValueError(
            f"source file is not valid UTF-8 Markdown: {source_path}"
        ) from exc

    if not text.strip():
        raise ValueError(f"source file is empty: {source_path}")

    return text


# ---------------------------------------------------------------------------
# signal extraction (deterministic, no LLM)
# ---------------------------------------------------------------------------


def _first_heading_and_paragraph(lines: list[str]) -> str:
    """Return the first level-1 heading as title and first non-empty,
    non-heading line after it as the signal sentence.

    Returns empty string if nothing useful is found.
    """
    found_heading: str | None = None
    found_paragraph: str | None = None
    past_frontmatter = False

    idx = 0
    if lines and lines[0].strip() == "---":
        idx = 1
        while idx < len(lines):
            if lines[idx].strip() == "---":
                idx += 1
                break
            idx += 1
    past_frontmatter = True

    for line in lines[idx:]:
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("# ") and found_heading is None:
            found_heading = stripped[2:].strip()
            continue
        if stripped.startswith("#"):
            continue  # skip sub-headings
        if found_heading is not None and found_paragraph is None:
            found_paragraph = stripped
            break

    parts: list[str] = []
    if found_heading:
        parts.append(found_heading)
    if found_paragraph:
        parts.append(found_paragraph)
    return " — ".join(parts)


def extract_signal(source_text: str) -> str:
    """Derive a concise signal string from the source Markdown text.

    Strategy (deterministic, no rewriting):
    1. Take the first level-1 heading + first non-empty paragraph.
    2. If no heading/paragraph is found, fall back to the first 140 chars
       of cleaned source text.
    """
    lines = source_text.splitlines()
    heading_signal = _first_heading_and_paragraph(lines)
    if heading_signal:
        return heading_signal

    # Last resort: first 140 chars of non-blank text
    combined = source_text.strip()
    if not combined:
        return "(no signal — source empty)"
    return combined[:140].strip()


# ---------------------------------------------------------------------------
# excerpt extraction
# ---------------------------------------------------------------------------


def extract_excerpt(source_text: str, max_chars: int = 2000) -> str:
    """Return the full source text, trimmed to a safe excerpt length if
    needed.  The original author voice is preserved without rewriting."""
    stripped = source_text.strip()
    if len(stripped) <= max_chars:
        return stripped
    return stripped[:max_chars] + "\n\n[... excerpt truncated ...]"


# ---------------------------------------------------------------------------
# page assembly
# ---------------------------------------------------------------------------


def yaml_scalar(value: str) -> str:
    """JSON-encode a string for safe use as a YAML value."""
    return json.dumps(value, ensure_ascii=False)


def build_insight_page(
    *,
    title: str,
    date_text: str,
    source_paths: list[str],
    generated_at: str,
    signal: str,
    source_excerpts: list[str],
) -> str:
    """Assemble the complete Daily Insight Markdown artifact."""

    source_paths_joined = ", ".join(source_paths)

    frontmatter = [
        "---",
        f"title: {yaml_scalar(title)}",
        f"date: {yaml_scalar(date_text)}",
        f"source_paths: {yaml_scalar(source_paths_joined)}",
        f"generated_at: {yaml_scalar(generated_at)}",
        "---",
        "",
        f"# {title}",
        "",
        f"**Date**: {date_text}",
        "",
        "---",
        "",
        "## Signal",
        "",
        signal,
        "",
        "---",
        "",
        "## Source Excerpts",
        "",
    ]

    for idx, (path, excerpt) in enumerate(
        zip(source_paths, source_excerpts), start=1
    ):
        frontmatter.append(f"### Source {idx}: {path}")
        frontmatter.append("")
        frontmatter.append(excerpt)
        frontmatter.append("")

    frontmatter.extend(
        [
            "---",
            "",
            "## Reflection",
            "",
            "This daily insight was generated from local source material",
            "within the Codexify repository.  The signal above is a",
            "deterministic extraction from the source headings and opening",
            "paragraphs and should not be read as a new claim, product",
            "announcement, or external statement.",
            "",
            "The reflection space is intentionally conservative.  It",
            "captures the immediate thematic alignment of the day's source",
            "material without extrapolating beyond what the sources",
            "themselves contain.",
            "",
            "---",
            "",
            "*Generated by `scripts/content/generate_resonant_daily_insight.py`*",
            f"*from {len(source_paths)} source file(s) on {generated_at}*",
        ]
    )

    return "\n".join(frontmatter)


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------


def build_summary(
    *,
    date_text: str,
    source_paths: list[str],
    target_path: Path,
    title: str,
    generated_at: str,
    signal_length: int,
    total_excerpt_chars: int,
    dry_run: bool,
    source_count: int,
) -> dict[str, object]:
    return {
        "ok": True,
        "dry_run": dry_run,
        "date": date_text,
        "source_paths": source_paths,
        "source_count": source_count,
        "target_path": display_path(target_path),
        "title": title,
        "generated_at": generated_at,
        "signal_length": signal_length,
        "total_excerpt_chars": total_excerpt_chars,
    }


# ---------------------------------------------------------------------------
# argument parsing
# ---------------------------------------------------------------------------


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a deterministic Resonant Constructs Daily Insight "
            "Markdown artifact from local source files."
        )
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Target date YYYY-MM-DD",
    )
    parser.add_argument(
        "--source",
        required=True,
        action="append",
        help="Path to a Markdown source file (repeatable)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for generated insight pages",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Optional custom title (default: Daily Insight — YYYY-MM-DD)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate inputs and print the target path without writing files",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite the output file if it already exists",
    )
    return parser.parse_args(argv)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    # --date validation
    try:
        date_text = validate_date(args.date)
    except ValueError as exc:
        print(f"generate-resonant-daily-insight error: {exc}", file=sys.stderr)
        return 1

    # --source validation (repeatable)
    sources_input: list[str] = args.source
    source_paths: list[Path] = []
    source_texts: list[str] = []

    for source_raw in sources_input:
        source_path = resolve_repo_path(source_raw)

        if not is_markdown_source(source_path):
            print(
                "generate-resonant-daily-insight error: each source must be "
                "a Markdown file (.md or .markdown); found "
                f"{source_raw}",
                file=sys.stderr,
            )
            return 1

        try:
            text = read_source_text(source_path)
        except (FileNotFoundError, ValueError) as exc:
            print(
                f"generate-resonant-daily-insight error: {exc}",
                file=sys.stderr,
            )
            return 1

        source_paths.append(source_path)
        source_texts.append(text)

    # --output-dir & target path
    output_dir_input = Path(args.output_dir).expanduser()
    output_dir = (
        output_dir_input
        if output_dir_input.is_absolute()
        else (REPO_ROOT / output_dir_input)
    ).resolve()
    target_path = output_dir / f"{date_text}.md"

    if target_path.exists() and not args.force:
        print(
            "generate-resonant-daily-insight error: output already exists; "
            "pass --force to overwrite",
            file=sys.stderr,
        )
        return 1

    # --title
    title = args.title or f"Daily Insight — {date_text}"

    # derived content
    generated_at = (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )

    # signal: combine signals from all sources
    signals: list[str] = []
    for text in source_texts:
        sig = extract_signal(text)
        if sig:
            signals.append(sig)
    combined_signal = "\n\n".join(signals) if signals else "(no signal)"

    # excerpts
    excerpts: list[str] = [extract_excerpt(t) for t in source_texts]

    # summary (for --dry-run and success output)
    source_path_strs = [
        display_path(p) for p in source_paths
    ]
    summary = build_summary(
        date_text=date_text,
        source_paths=source_path_strs,
        target_path=target_path,
        title=title,
        generated_at=generated_at,
        signal_length=len(combined_signal),
        total_excerpt_chars=sum(len(e) for e in excerpts),
        dry_run=args.dry_run,
        source_count=len(source_paths),
    )

    if args.dry_run:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    # generate & write
    page = build_insight_page(
        title=title,
        date_text=date_text,
        source_paths=source_path_strs,
        generated_at=generated_at,
        signal=combined_signal,
        source_excerpts=excerpts,
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(page, encoding="utf-8")
    summary["written"] = True
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
