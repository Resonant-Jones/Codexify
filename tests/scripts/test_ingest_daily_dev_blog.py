from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "content" / "ingest_daily_dev_blog.py"


def run_cli(*args: str, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), *args],
        cwd=cwd,
        text=True,
        capture_output=True,
        check=False,
    )


def parse_output(text: str) -> dict[str, object]:
    return json.loads(text.strip())


def parse_generated_page(text: str) -> tuple[dict[str, str], str]:
    lines = text.splitlines()
    assert lines[0] == "---"
    closing = lines.index("---", 1)
    metadata: dict[str, str] = {}
    for line in lines[1:closing]:
        key, value = line.split(": ", 1)
        metadata[key] = json.loads(value)
    body = "\n".join(lines[closing + 2 :])
    return metadata, body


def test_successful_ingestion(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text(
        "# Daily Dev Blog\n\nThis is the author's voice.\n\n- point one",
        encoding="utf-8",
    )
    output_dir = tmp_path / "generated"

    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--force",
    )

    assert result.returncode == 0, result.stderr
    assert result.stderr == ""

    output_path = output_dir / "2026-05-13.md"
    assert output_path.is_file()

    metadata, body = parse_generated_page(output_path.read_text(encoding="utf-8"))
    assert metadata["date"] == "2026-05-13"
    assert metadata["source_path"] == str(source)
    assert metadata["title"] == "Daily Dev Blog"
    assert "generated_at" in metadata
    assert metadata["generated_at"].endswith("Z")
    assert body == source.read_text(encoding="utf-8")

    summary = parse_output(result.stdout)
    assert summary["ok"] is True
    assert summary["written"] is True
    assert summary["target_path"] == str(output_path)


def test_missing_source_failure(tmp_path: Path) -> None:
    source = tmp_path / "missing.md"
    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(tmp_path / "generated"),
    )

    assert result.returncode == 1
    assert "source file not found" in result.stderr
    assert result.stdout == ""


def test_empty_source_failure(tmp_path: Path) -> None:
    source = tmp_path / "empty.md"
    source.write_text("", encoding="utf-8")
    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(tmp_path / "generated"),
    )

    assert result.returncode == 1
    assert "source file is empty" in result.stderr
    assert result.stdout == ""


def test_non_markdown_source_failure(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("# Not Markdown enough\n", encoding="utf-8")
    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(tmp_path / "generated"),
    )

    assert result.returncode == 1
    assert "source must be a Markdown file" in result.stderr
    assert result.stdout == ""


def test_existing_output_without_force_fails(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Title\n\nBody", encoding="utf-8")
    output_dir = tmp_path / "generated"
    output_dir.mkdir(parents=True)
    target = output_dir / "2026-05-13.md"
    target.write_text("old content", encoding="utf-8")

    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
    )

    assert result.returncode == 1
    assert "output already exists" in result.stderr
    assert target.read_text(encoding="utf-8") == "old content"


def test_force_overwrite_replaces_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# New Title\n\nFresh body", encoding="utf-8")
    output_dir = tmp_path / "generated"
    output_dir.mkdir(parents=True)
    target = output_dir / "2026-05-13.md"
    target.write_text("old content", encoding="utf-8")

    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--force",
    )

    assert result.returncode == 0, result.stderr
    assert target.read_text(encoding="utf-8") != "old content"

    metadata, body = parse_generated_page(target.read_text(encoding="utf-8"))
    assert metadata["date"] == "2026-05-13"
    assert metadata["source_path"] == str(source)
    assert body == source.read_text(encoding="utf-8")


def test_dry_run_does_not_write_files(tmp_path: Path) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Dry Run\n\nBody", encoding="utf-8")
    output_dir = tmp_path / "generated"

    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--dry-run",
    )

    assert result.returncode == 0, result.stderr
    assert not (output_dir / "2026-05-13.md").exists()
    assert not output_dir.exists()

    summary = parse_output(result.stdout)
    assert summary["dry_run"] is True
    assert summary["target_path"] == str(output_dir / "2026-05-13.md")


@pytest.mark.parametrize(
    "bad_date",
    ["2026-13-01", "20260513", "2026-05-13T10:00:00Z"],
)
def test_invalid_date_fails(tmp_path: Path, bad_date: str) -> None:
    source = tmp_path / "source.md"
    source.write_text("# Title\n\nBody", encoding="utf-8")
    result = run_cli(
        "--date",
        bad_date,
        "--source",
        str(source),
        "--output-dir",
        str(tmp_path / "generated"),
    )

    assert result.returncode == 1
    assert "invalid --date value" in result.stderr
