#!/usr/bin/env python3
"""Generate a deterministic Resonant Constructs daily insight Markdown artifact.

This script is repo-local.  It reads only local Markdown source files,
extracts a concise signal from headings and first non-empty paragraphs,
and produces a dated insight page.  No LLM, network API, or external
publishing step is involved.
"""

from __future__ import annotations

import argparse
import datetime
import re
import sys
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_MARKDOWN_EXTENSIONS = frozenset(
    {".md", ".markdown", ".mdown", ".mkd", ".mkdn"}
)


def _is_markdown(path: Path) -> bool:
    """Return *True* if *path* has a recognised Markdown extension."""
    return path.suffix.lower() in _MARKDOWN_EXTENSIONS


# ---------------------------------------------------------------------------
# signal extraction
# ---------------------------------------------------------------------------

_HEADING_RE = re.compile(r"^#{1,6}\s+(.+)", re.MULTILINE)
_PARA_RE = re.compile(
    r"^(?!\s*#{1,6}\s)(?!\s*>)(?!\s*[-*+]\s)(?!\s*\d+\.\s)[^\s].*$",
    re.MULTILINE,
)


def _extract_headings(text: str, max_items: int = 3) -> list[str]:
    """Return the first *max_items* heading bodies from *text*."""
    headings: list[str] = []
    for match in _HEADING_RE.finditer(text):
        body = match.group(1).strip()
        if body and body not in headings:
            headings.append(body)
        if len(headings) >= max_items:
            break
    return headings


def _extract_first_paragraph(text: str, max_sentences: int = 2) -> str | None:
    """Return the first substantial non-heading paragraph from *text*.

    The result is clipped to roughly *max_sentences* sentence boundaries.
    """
    for match in _PARA_RE.finditer(text):
        raw = match.group(0).strip()
        if len(raw) < 10:  # skip very short lines (e.g. standalone punctuation)
            continue
        # clip after max_sentences sentence-ending punctuation marks
        sentence_endings = re.finditer(r"[.!?](?:\s|$)", raw)
        count = 0
        last_pos = 0
        for se in sentence_endings:
            count += 1
            last_pos = se.end()
            if count >= max_sentences:
                return raw[:last_pos].rstrip()
        return raw
    return None


def _build_signal(text: str) -> str:
    """Build a concise signal line from source *text*."""
    headings = _extract_headings(text)
    if headings:
        heading_signal = " / ".join(headings)
        paragraph = _extract_first_paragraph(text)
        if paragraph:
            return f"{heading_signal} — {paragraph}"
        return heading_signal

    paragraph = _extract_first_paragraph(text, max_sentences=3)
    if paragraph:
        return paragraph

    return "(no extractable signal)"


# ---------------------------------------------------------------------------
# reflection template
# ---------------------------------------------------------------------------

_REFLECTION_TEMPLATE = (
    "This is a local, deterministic daily insight generated from "
    "Resonant Constructs source material.  It is not an external "
    "announcement or release statement.  The reflection captures "
    "one practitioner’s reading of the source material on the "
    "generation date; revisit the referenced source documents for "
    "the full context and author’s voice."
)


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------


def _format_timestamp(dt: datetime.datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")  # UTC


def _build_source_excerpt(path: Path) -> str:
    """Return an excerpted version of a source file."""
    text = path.read_text(encoding="utf-8")
    headings = _extract_headings(text, max_items=99)
    if not headings:
        return text.strip()

    lines: list[str] = []
    for heading in headings:
        lines.append(f"### {heading}")
    lines.append("")  # blank separator
    lines.append(f"*Excerpted from `{path}` — see source for full content.*")
    return "\n".join(lines)


def generate_daily_insight(
    *,
    date_str: str,
    source_paths: Sequence[Path],
    output_dir: Path,
    title: str | None,
    dry_run: bool,
    force: bool,
) -> str:
    """Generate a Resonant Constructs daily insight.

    Returns the path of the generated (or would-be generated) file.
    Raises *ValueError* for invalid inputs, *FileNotFoundError* for
    missing sources.
    """
    # -- validate date -------------------------------------------------------
    try:
        date_obj = datetime.date.fromisoformat(date_str)
    except (ValueError, TypeError) as exc:
        raise ValueError(f"invalid date {date_str!r}: {exc}") from exc

    # -- validate sources ----------------------------------------------------
    if not source_paths:
        raise ValueError("at least one --source is required")

    for src in source_paths:
        if not src.is_file():
            raise FileNotFoundError(f"source file not found: {src}")
        if not _is_markdown(src):
            raise ValueError(
                f"source is not a Markdown file: {src} (suffix={src.suffix})"
            )
        text = src.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"source file is empty: {src}")

    # -- compute output path -------------------------------------------------
    output_path = output_dir / f"{date_str}.md"

    # -- handle existing file ------------------------------------------------
    if output_path.exists() and not force:
        raise FileExistsError(
            f"output file already exists: {output_path} (pass --force to overwrite)"
        )

    # -- build metadata ------------------------------------------------------
    generated_at = datetime.datetime.now(datetime.timezone.utc)
    final_title = title or f"Daily Insight — {date_str}"

    # -- build signal section ------------------------------------------------
    signal_parts: list[str] = []
    for src in source_paths:
        text = src.read_text(encoding="utf-8")
        signal_text = _build_signal(text)
        signal_parts.append(f"- **{src.name}:** {signal_text}")

    # -- build excerpt section ------------------------------------------------
    excerpt_parts: list[str] = []
    for src in source_paths:
        excerpt_parts.append(_build_source_excerpt(src))
        excerpt_parts.append("")

    # -- build source listing ------------------------------------------------
    source_lines = [f"- `{src}`" for src in source_paths]

    # -- assemble output -----------------------------------------------------
    output_lines = [
        f"# {final_title}",
        "",
        f"**Date:** {date_str}",
        f"**Generated:** {_format_timestamp(generated_at)}",
        "",
        "**Source files:**",
        *source_lines,
        "",
        "> This artifact is generated from local source material only.  It is not an external announcement.",
        "",
        "---",
        "",
        "## Signal",
        "",
        *signal_parts,
        "",
        "---",
        "",
        "## Source Excerpts",
        "",
        *excerpt_parts,
        "---",
        "",
        "## Reflection",
        "",
        _REFLECTION_TEMPLATE,
        "",
    ]
    content = "\n".join(output_lines)

    # -- dry run -------------------------------------------------------------
    if dry_run:
        return str(output_path)

    # -- write ---------------------------------------------------------------
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path.write_text(content, encoding="utf-8")

    print(f"Wrote: {output_path}")
    return str(output_path)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a deterministic Resonant Constructs daily insight artifact."
    )
    parser.add_argument(
        "--date",
        required=True,
        help="Date for the insight (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--source",
        action="append",
        dest="sources",
        required=True,
        type=Path,
        help="Path to a local Markdown source file (repeatable)",
    )
    parser.add_argument(
        "--output-dir",
        default=str(
            REPO_ROOT
            / "docs"
            / "ResonantConstructs"
            / "daily-insights"
            / "generated"
        ),
        help="Output directory for generated artifact",
    )
    parser.add_argument(
        "--title",
        default=None,
        help="Custom title (default: 'Daily Insight — YYYY-MM-DD')",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print target path and source summary without writing",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing output file if present",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        output_path = generate_daily_insight(
            date_str=args.date,
            source_paths=args.sources,
            output_dir=Path(args.output_dir),
            title=args.title,
            dry_run=args.dry_run,
            force=args.force,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except FileExistsError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    if args.dry_run:
        print(f"[DRY RUN] Would write to: {output_path}")
        print(f"[DRY RUN] Sources:")
        for src in args.sources:
            print(f"  - {src}")
        source_count = len(args.sources)
        print(f"[DRY RUN] Total sources: {source_count}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
