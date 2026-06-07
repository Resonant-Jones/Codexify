#!/usr/bin/env python
"""Render a standalone local Codexify voiceover file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from guardian.tts.config import get_local_tts_config  # noqa: E402
from guardian.tts.renderer import render_voiceover  # noqa: E402


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Render local voiceover audio through Codexify's TTS adapter."
    )
    parser.add_argument("--input", required=True, help="Text file to render.")
    parser.add_argument("--output", required=True, help="Output audio path.")
    parser.add_argument("--voice", default=None, help="Voice id or preset.")
    parser.add_argument("--backend", default=None, help="TTS backend id.")
    parser.add_argument(
        "--format",
        choices=("wav", "mp3"),
        default=None,
        help="Output format. Defaults to the output path suffix or wav.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the render plan without generating audio.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    input_path = Path(args.input).expanduser()
    output_path = Path(args.output).expanduser()
    if not input_path.exists():
        print(f"input_not_found:{input_path}", file=sys.stderr)
        return 2

    fmt = args.format or output_path.suffix.lstrip(".").lower() or "wav"
    cfg = get_local_tts_config()
    result = render_voiceover(
        text=input_path.read_text(encoding="utf-8"),
        output_path=output_path,
        backend_id=args.backend,
        output_format=fmt,
        voice_id=args.voice,
        dry_run=args.dry_run,
        config=cfg,
    )
    print(json.dumps(result.to_dict(), indent=2))
    if args.dry_run:
        return 0
    return 0 if result.render_succeeded else 1


if __name__ == "__main__":
    raise SystemExit(main())
