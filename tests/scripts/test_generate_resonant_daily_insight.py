"""Tests for the Resonant Constructs daily insight generator."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    REPO_ROOT / "scripts" / "content" / "generate_resonant_daily_insight.py"
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

_FORBIDDEN_RELEASE_PATTERNS = [
    "release-ready",
    "public launch",
    "GA date",
    "production ready",
    "enterprise-grade",
    "announcing",
    "now available",
    "we guarantee",
    "zero downtime",
    "100% coverage",
    "flawless",
    "industry-leading",
    "best in class",
    "SLA",
]


def _make_source_file(tmp_path: Path, name: str, content: str) -> Path:
    path = tmp_path / name
    path.write_text(content, encoding="utf-8")
    return path


def _make_markdown_file(tmp_path: Path, name: str, content: str) -> Path:
    if not name.endswith(".md"):
        name = f"{name}.md"
    return _make_source_file(tmp_path, name, content)


def _run_cli(
    date: str,
    sources: list[Path],
    output_dir: Path,
    *,
    title: str | None = None,
    dry_run: bool = False,
    force: bool = False,
) -> subprocess.CompletedProcess[str]:
    cmd = [
        sys.executable,
        str(SCRIPT),
        "--date",
        date,
        "--output-dir",
        str(output_dir),
    ]
    for src in sources:
        cmd.extend(["--source", str(src)])
    if title:
        cmd.extend(["--title", title])
    if dry_run:
        cmd.append("--dry-run")
    if force:
        cmd.append("--force")

    return subprocess.run(
        cmd,
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )


def _read_insight(path: Path) -> str:
    return path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# successful generation
# ---------------------------------------------------------------------------

ONE_SOURCE_MD = """# Understanding Deterministic Generation

Deterministic generation ensures that the same inputs always produce the
same outputs. This is a foundational property for content pipelines that
must operate without external dependencies.

## Key Properties

- Idempotent across runs
- Reproducible by any team member
- Auditable output history
"""


def test_generates_from_one_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(tmp_path, "deterministic.md", ONE_SOURCE_MD)

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode == 0, result.stderr

    insight_path = output_dir / "2026-05-13.md"
    assert insight_path.exists()

    content = _read_insight(insight_path)
    assert "Daily Insight — 2026-05-13" in content
    assert "**Date:** 2026-05-13" in content
    assert "**Generated:**" in content
    assert f"`{src}`" in content
    assert "## Signal" in content
    assert "Understanding Deterministic Generation" in content
    assert "## Source Excerpts" in content
    assert "## Reflection" in content


def test_generates_from_multiple_sources(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src1 = _make_markdown_file(
        tmp_path,
        "a.md",
        "# First Document\n\nThe first document describes foundational concepts.\n",
    )
    src2 = _make_markdown_file(
        tmp_path,
        "b.md",
        "# Second Document\n\nThe second document builds on the first.\n",
    )

    result = _run_cli("2026-05-13", [src1, src2], output_dir)
    assert result.returncode == 0, result.stderr

    insight_path = output_dir / "2026-05-13.md"
    content = _read_insight(insight_path)

    assert "First Document" in content
    assert "Second Document" in content
    assert f"`{src1}`" in content
    assert f"`{src2}`" in content


# ---------------------------------------------------------------------------
# error: missing / empty / non-Markdown
# ---------------------------------------------------------------------------


def test_fails_on_missing_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    missing = tmp_path / "nope.md"

    result = _run_cli("2026-05-13", [missing], output_dir)
    assert result.returncode != 0
    assert "not found" in result.stderr.lower()


def test_fails_on_empty_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_source_file(tmp_path, "empty.md", "")

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode != 0
    assert "empty" in result.stderr.lower()


def test_fails_on_non_markdown_source(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_source_file(tmp_path, "notes.txt", "Some text content\n")

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode != 0
    assert "not a markdown file" in result.stderr.lower()


# ---------------------------------------------------------------------------
# existing output behaviour
# ---------------------------------------------------------------------------


def test_fails_existing_output_without_force(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    existing = output_dir / "2026-05-13.md"
    existing.write_text("preexisting content\n", encoding="utf-8")

    src = _make_markdown_file(tmp_path, "x.md", "# Title\n\nBody.\n")

    result = _run_cli("2026-05-13", [src], output_dir, force=False)
    assert result.returncode != 0
    assert "already exists" in result.stderr.lower()


def test_overwrites_with_force(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    output_dir.mkdir(parents=True)
    existing = output_dir / "2026-05-13.md"
    existing.write_text("preexisting content\n", encoding="utf-8")

    src = _make_markdown_file(
        tmp_path, "y.md", "# Fresh Content\n\nFresh body.\n"
    )

    result = _run_cli("2026-05-13", [src], output_dir, force=True)
    assert result.returncode == 0, result.stderr

    content = _read_insight(existing)
    assert "preexisting" not in content
    assert "Fresh Content" in content


# ---------------------------------------------------------------------------
# dry run
# ---------------------------------------------------------------------------


def test_dry_run_does_not_write(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(
        tmp_path, "z.md", "# Dry Run Test\n\nDoes not write.\n"
    )

    result = _run_cli("2026-05-13", [src], output_dir, dry_run=True)
    assert result.returncode == 0, result.stderr

    insight_path = output_dir / "2026-05-13.md"
    assert not insight_path.exists()

    stdout = result.stdout
    assert "[DRY RUN]" in stdout
    assert "2026-05-13.md" in stdout


# ---------------------------------------------------------------------------
# title behaviour
# ---------------------------------------------------------------------------


def test_default_title(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(tmp_path, "title_a.md", "# Test\n\nBody.\n")

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode == 0

    content = _read_insight(output_dir / "2026-05-13.md")
    assert "# Daily Insight — 2026-05-13" in content


def test_custom_title(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(tmp_path, "title_b.md", "# Test\n\nBody.\n")

    result = _run_cli(
        "2026-05-13", [src], output_dir, title="My Custom Insight"
    )
    assert result.returncode == 0

    content = _read_insight(output_dir / "2026-05-13.md")
    assert "# My Custom Insight" in content
    assert "Daily Insight — 2026-05-13" not in content


# ---------------------------------------------------------------------------
# metadata
# ---------------------------------------------------------------------------


def test_metadata_includes_date_and_sources(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(
        tmp_path, "meta.md", "# Meta\n\nTesting metadata.\n"
    )

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode == 0

    content = _read_insight(output_dir / "2026-05-13.md")
    assert "**Date:** 2026-05-13" in content
    assert "**Generated:**" in content
    assert f"`{src}`" in content
    assert "local source material" in content


# ---------------------------------------------------------------------------
# no unsupported claims
# ---------------------------------------------------------------------------


def test_no_unsupported_product_release_claims(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(
        tmp_path,
        "clean.md",
        "# A Neutral Document\n\nThis document discusses architecture patterns without making product announcements.\n\n## Details\n\nThe team is exploring several approaches to content generation.\n",
    )

    result = _run_cli("2026-05-13", [src], output_dir)
    assert result.returncode == 0

    content = _read_insight(output_dir / "2026-05-13.md").lower()
    for pattern in _FORBIDDEN_RELEASE_PATTERNS:
        assert (
            pattern.lower() not in content
        ), f"found forbidden pattern: {pattern}"


# ---------------------------------------------------------------------------
# CLI argument validation
# ---------------------------------------------------------------------------


def test_fails_without_sources(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--date",
            "2026-05-13",
            "--output-dir",
            str(output_dir),
        ],
        cwd=str(REPO_ROOT),
        text=True,
        capture_output=True,
    )
    assert result.returncode != 0


def test_fails_with_invalid_date(tmp_path: Path) -> None:
    output_dir = tmp_path / "out"
    src = _make_markdown_file(tmp_path, "d.md", "# Doc\n\nBody.\n")

    result = _run_cli("not-a-date", [src], output_dir)
    assert result.returncode != 0
    assert "invalid date" in result.stderr.lower()
