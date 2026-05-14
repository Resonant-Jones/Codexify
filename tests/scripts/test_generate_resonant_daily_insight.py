from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = (
    ROOT / "scripts" / "content" / "generate_resonant_daily_insight.py"
)


def run_cli(
    *args: str, cwd: Path = ROOT
) -> subprocess.CompletedProcess[str]:
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
        key, _, value = line.partition(": ")
        metadata[key] = json.loads(value)
    body = "\n".join(lines[closing + 2 :])
    return metadata, body


# ---------------------------------------------------------------------------
# helper to create source fixtures
# ---------------------------------------------------------------------------


def make_source(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_successful_generation_from_one_source(tmp_path: Path) -> None:
    source = make_source(
        tmp_path / "src" / "note1.md",
        "# Exploring Resonant Fields\n\nA quiet investigation into "
        "how fields self-organize when constraints are removed.\n\n"
        "## Observations\n\n- Pattern A emerged\n- Pattern B followed",
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

    metadata, body = parse_generated_page(
        output_path.read_text(encoding="utf-8")
    )
    assert metadata["date"] == "2026-05-13"
    assert "note1.md" in metadata["source_paths"]
    assert "generated_at" in metadata
    assert metadata["generated_at"].endswith("Z")

    # Default title behavior
    assert metadata["title"] == "Daily Insight — 2026-05-13"

    # Generated body must contain expected sections
    assert "## Signal" in body
    assert "Exploring Resonant Fields" in body
    assert "## Source Excerpts" in body
    assert "## Reflection" in body
    assert "generated from local source material" in body

    summary = parse_output(result.stdout)
    assert summary["ok"] is True
    assert summary["written"] is True
    assert summary["source_count"] == 1


def test_successful_generation_from_multiple_sources(
    tmp_path: Path,
) -> None:
    source1 = make_source(
        tmp_path / "a" / "field-notes.md",
        "# Field Dynamics\n\nThe lattice showed unexpected coherence "
        "at t+4.\n",
    )
    source2 = make_source(
        tmp_path / "b" / "resonance-log.md",
        "# Resonance Log\n\nPhase alignment held through cycle 7.\n\n"
        "## Details\n\n- amplitude stable\n- frequency matched prediction",
    )
    output_dir = tmp_path / "gen"

    result = run_cli(
        "--date",
        "2026-05-14",
        "--source",
        str(source1),
        "--source",
        str(source2),
        "--output-dir",
        str(output_dir),
        "--force",
    )

    assert result.returncode == 0, result.stderr
    output_path = output_dir / "2026-05-14.md"
    assert output_path.is_file()

    metadata, body = parse_generated_page(
        output_path.read_text(encoding="utf-8")
    )
    assert metadata["date"] == "2026-05-14"
    assert "field-notes.md" in metadata["source_paths"]
    assert "resonance-log.md" in metadata["source_paths"]

    # Signal from both sources
    assert "## Signal" in body
    assert "Field Dynamics" in body
    assert "Resonance Log" in body

    # Two source excerpt sections
    assert "### Source 1:" in body
    assert "### Source 2:" in body

    summary = parse_output(result.stdout)
    assert summary["source_count"] == 2


def test_missing_source_failure(tmp_path: Path) -> None:
    source = tmp_path / "no-such-file.md"
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
    source = make_source(tmp_path / "empty.md", "")
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
    source = make_source(tmp_path / "notes.txt", "# Looks like Markdown but "
        "the extension is wrong\n")
    result = run_cli(
        "--date",
        "2026-05-13",
        "--source",
        str(source),
        "--output-dir",
        str(tmp_path / "generated"),
    )

    assert result.returncode == 1
    assert (
        "each source must be a Markdown file" in result.stderr
    )
    assert result.stdout == ""


def test_existing_output_without_force_fails(tmp_path: Path) -> None:
    source = make_source(
        tmp_path / "src.md", "# Test\n\nBody\n"
    )
    output_dir = tmp_path / "generated"
    output_dir.mkdir(parents=True)
    target = output_dir / "2026-05-13.md"
    target.write_text("stale content", encoding="utf-8")

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
    assert target.read_text(encoding="utf-8") == "stale content"


def test_force_overwrite_replaces_existing_output(
    tmp_path: Path,
) -> None:
    source = make_source(
        tmp_path / "src.md",
        "# Fresh\n\nNew material.\n",
    )
    output_dir = tmp_path / "generated"
    output_dir.mkdir(parents=True)
    target = output_dir / "2026-05-13.md"
    target.write_text("stale content", encoding="utf-8")

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
    assert target.read_text(encoding="utf-8") != "stale content"

    metadata, body = parse_generated_page(
        target.read_text(encoding="utf-8")
    )
    assert metadata["date"] == "2026-05-13"
    assert "src.md" in metadata["source_paths"]
    assert "Signal" in body


def test_dry_run_does_not_write_files(tmp_path: Path) -> None:
    source = make_source(
        tmp_path / "src.md",
        "# Dry Run Insight\n\nTest body.\n",
    )
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
    assert "2026-05-13.md" in summary["target_path"]


def test_default_title_behavior(tmp_path: Path) -> None:
    source = make_source(
        tmp_path / "src.md", "# Content\n\nText.\n"
    )
    output_dir = tmp_path / "gen"

    result = run_cli(
        "--date",
        "2026-05-14",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--force",
    )

    assert result.returncode == 0, result.stderr
    output_path = output_dir / "2026-05-14.md"
    metadata, _ = parse_generated_page(
        output_path.read_text(encoding="utf-8")
    )
    assert metadata["title"] == "Daily Insight — 2026-05-14"


def test_custom_title_behavior(tmp_path: Path) -> None:
    source = make_source(
        tmp_path / "src.md", "# Content\n\nText.\n"
    )
    output_dir = tmp_path / "gen"

    result = run_cli(
        "--date",
        "2026-05-14",
        "--source",
        str(source),
        "--output-dir",
        str(output_dir),
        "--title",
        "Resonant Fields: A Study",
        "--force",
    )

    assert result.returncode == 0, result.stderr
    output_path = output_dir / "2026-05-14.md"
    metadata, _ = parse_generated_page(
        output_path.read_text(encoding="utf-8")
    )
    assert metadata["title"] == "Resonant Fields: A Study"


def test_generated_metadata_includes_date_and_source_paths(
    tmp_path: Path,
) -> None:
    source1 = make_source(tmp_path / "a.md", "# A\n\nBody A.\n")
    source2 = make_source(tmp_path / "b.md", "# B\n\nBody B.\n")
    output_dir = tmp_path / "gen"

    result = run_cli(
        "--date",
        "2026-05-15",
        "--source",
        str(source1),
        "--source",
        str(source2),
        "--output-dir",
        str(output_dir),
        "--force",
    )

    assert result.returncode == 0, result.stderr
    summary = parse_output(result.stdout)
    assert summary["date"] == "2026-05-15"
    assert len(summary["source_paths"]) == 2


def test_generated_output_no_unsupported_claims(
    tmp_path: Path,
) -> None:
    """Verify the generated page does not invent product status, release
    promises, customer statements, or metrics."""
    source = make_source(
        tmp_path / "src.md",
        "# Observation\n\nThe resonance pattern was notable today.\n",
    )
    output_dir = tmp_path / "gen"

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
    output_path = output_dir / "2026-05-13.md"
    body = output_path.read_text(encoding="utf-8")

    # Banned claim patterns — the generated output must not contain these
    banned = [
        "released",
        "launched",
        "% of",
        "customers",
        "users",
        "revenue",
        "market share",
        "partnership",
        "acquisition",
        "funding",
        "milestone reached",
        "production ready",
        "GA",
        "general availability",
        "SLA",
    ]

    body_lower = body.lower()
    for phrase in banned:
        assert phrase not in body_lower, (
            f"generated output contains unsupported claim phrase: {phrase!r}"
        )

    # Must contain the explicit artifact notice
    assert "generated from local source material" in body
    assert (
        "scripts/content/generate_resonant_daily_insight.py"
        in body
    )


@pytest.mark.parametrize(
    "bad_date",
    ["2026-13-01", "20260513", "2026-05-13T10:00:00Z", "not-a-date"],
)
def test_invalid_date_fails(tmp_path: Path, bad_date: str) -> None:
    source = make_source(tmp_path / "src.md", "# Title\n\nBody\n")
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
