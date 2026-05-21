from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.job_intelligence.validate_fixture import main, validate_fixture

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip"
)


def _copy_fixture(tmp_path: Path, name: str = "fixture-copy") -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURE_DIR, destination)
    return destination


def test_real_fixture_passes_validation() -> None:
    assert validate_fixture(FIXTURE_DIR) == []


def test_missing_required_files_fail(tmp_path: Path) -> None:
    fixture_dir = tmp_path / "missing-files-fixture"
    fixture_dir.mkdir()
    (fixture_dir / "README.md").write_text("# Incomplete fixture\n", encoding="utf-8")

    errors = validate_fixture(fixture_dir)

    assert errors
    assert any("source-interaction.txt" in error for error in errors)
    assert any("expected-extraction.json" in error for error in errors)


def test_prohibited_subjective_labels_fail(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(tmp_path)
    review_packet_path = fixture_dir / "expected-review-packet.json"
    review_packet = json.loads(review_packet_path.read_text(encoding="utf-8"))
    review_packet["field_review_notes"].append(
        {
            "field_path": "review.notes",
            "note": "This looks like a difficult customer situation.",
        }
    )
    review_packet_path.write_text(
        json.dumps(review_packet, indent=2) + "\n", encoding="utf-8"
    )

    errors = validate_fixture(fixture_dir)

    assert any("prohibited subjective label" in error for error in errors)


def test_contact_like_source_data_fails(tmp_path: Path) -> None:
    samples = [
        "Customer: Please call me at 123-456-7890.\n",
        "Customer: Email me at example@example.com.\n",
        "Customer: The property is at 123 Maple Street.\n",
    ]

    for index, sample in enumerate(samples):
        fixture_dir = _copy_fixture(tmp_path, f"fixture-copy-{index}")
        (fixture_dir / "source-interaction.txt").write_text(
            sample, encoding="utf-8"
        )

        errors = validate_fixture(fixture_dir)

        assert any(
            "source-interaction.txt appears to contain" in error
            for error in errors
        )


def test_main_returns_zero_for_real_fixture() -> None:
    result = main([str(FIXTURE_DIR)])
    assert result == 0
