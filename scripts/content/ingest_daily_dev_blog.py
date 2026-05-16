#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUTPUT_DIR = Path("docs/Website/dev-blog/generated")
MARKDOWN_SUFFIXES = {".md", ".markdown"}


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


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Ingest a repo-local daily dev blog Markdown source into the "
            "Codexify website content tree."
        )
    )
    parser.add_argument("--date", required=True, help="Target date YYYY-MM-DD")
    parser.add_argument(
        "--source",
        required=True,
        help="Path to the Markdown source file",
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Output directory for generated website pages",
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


def validate_date(date_text: str) -> str:
    try:
        parsed = datetime.strptime(date_text, "%Y-%m-%d").date()
    except ValueError as exc:
        raise ValueError(
            f"invalid --date value {date_text!r}; expected YYYY-MM-DD"
        ) from exc
    return parsed.isoformat()


def is_markdown_source(path: Path) -> bool:
    return path.suffix.lower() in MARKDOWN_SUFFIXES


def read_source_text(source_path: Path) -> str:
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


def extract_title(source_text: str, fallback_title: str) -> str:
    lines = source_text.splitlines()
    index = 0

    if lines and lines[0].strip() == "---":
        index = 1
        while index < len(lines):
            if lines[index].strip() == "---":
                index += 1
                break
            index += 1

    for line in lines[index:]:
        stripped = line.lstrip()
        if stripped.startswith("# "):
            return stripped[2:].strip() or fallback_title

    return fallback_title


def yaml_scalar(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def build_generated_page(
    *,
    title: str,
    date_text: str,
    source_path_text: str,
    generated_at: str,
    source_text: str,
) -> str:
    frontmatter = [
        "---",
        f"title: {yaml_scalar(title)}",
        f"date: {yaml_scalar(date_text)}",
        f"source_path: {yaml_scalar(source_path_text)}",
        f"generated_at: {yaml_scalar(generated_at)}",
        "---",
        "",
        source_text,
    ]
    return "\n".join(frontmatter)


def build_summary(
    *,
    date_text: str,
    source_path_text: str,
    target_path: Path,
    title: str,
    generated_at: str,
    body_chars: int,
    dry_run: bool,
) -> dict[str, object]:
    return {
        "ok": True,
        "dry_run": dry_run,
        "date": date_text,
        "source_path": source_path_text,
        "target_path": display_path(target_path),
        "title": title,
        "generated_at": generated_at,
        "body_chars": body_chars,
    }


def run(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        date_text = validate_date(args.date)
    except ValueError as exc:
        print(f"ingest-daily-dev-blog error: {exc}", file=sys.stderr)
        return 1

    source_input = args.source
    source_path = resolve_repo_path(source_input)
    if not is_markdown_source(source_path):
        print(
            "ingest-daily-dev-blog error: source must be a Markdown file "
            "(.md or .markdown)",
            file=sys.stderr,
        )
        return 1

    try:
        source_text = read_source_text(source_path)
    except (FileNotFoundError, ValueError) as exc:
        print(f"ingest-daily-dev-blog error: {exc}", file=sys.stderr)
        return 1

    output_dir_input = Path(args.output_dir).expanduser()
    output_dir = (
        output_dir_input
        if output_dir_input.is_absolute()
        else (REPO_ROOT / output_dir_input)
    ).resolve()
    target_path = output_dir / f"{date_text}.md"

    if target_path.exists() and not args.force:
        print(
            "ingest-daily-dev-blog error: output already exists; pass "
            "--force to overwrite",
            file=sys.stderr,
        )
        return 1

    title = extract_title(
        source_text, fallback_title=f"Daily Dev Blog - {date_text}"
    )
    generated_at = (
        datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace(
            "+00:00", "Z"
        )
    )
    generated_page = build_generated_page(
        title=title,
        date_text=date_text,
        source_path_text=source_input,
        generated_at=generated_at,
        source_text=source_text,
    )
    summary = build_summary(
        date_text=date_text,
        source_path_text=source_input,
        target_path=target_path,
        title=title,
        generated_at=generated_at,
        body_chars=len(source_text),
        dry_run=args.dry_run,
    )

    if args.dry_run:
        print(json.dumps(summary, indent=2, sort_keys=True))
        return 0

    output_dir.mkdir(parents=True, exist_ok=True)
    target_path.write_text(generated_page, encoding="utf-8")
    summary["written"] = True
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
