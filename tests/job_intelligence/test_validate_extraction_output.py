from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.job_intelligence.validate_extraction_output import (
    main,
    validate_extraction_output,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip"
)
EXTRACTION_PATH = FIXTURE_DIR / "expected-extraction.json"
SOURCE_TEXT_PATH = FIXTURE_DIR / "source-interaction.txt"


def _load_real_extraction() -> dict[str, Any]:
    return json.loads(EXTRACTION_PATH.read_text(encoding="utf-8"))


def _write_extraction(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "extraction-output.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_real_extraction_passes_validation() -> None:
    assert validate_extraction_output(EXTRACTION_PATH) == []


def test_real_extraction_passes_with_source_text() -> None:
    assert (
        validate_extraction_output(
            EXTRACTION_PATH, source_text_path=SOURCE_TEXT_PATH
        )
        == []
    )


def test_real_extraction_passes_with_fixture_dir() -> None:
    assert (
        validate_extraction_output(EXTRACTION_PATH, fixture_dir=FIXTURE_DIR)
        == []
    )


def test_missing_required_fields_fail(tmp_path: Path) -> None:
    extraction = _load_real_extraction()
    extraction.pop("fixture_id")
    path = _write_extraction(tmp_path, extraction)

    errors = validate_extraction_output(path)

    assert any("missing required top-level keys" in error for error in errors)
    assert any("fixture_id" in error for error in errors)


def test_subjective_labels_fail(tmp_path: Path) -> None:
    extraction = _load_real_extraction()
    extraction["review_recommendations"].append(
        "Do not preserve this as a difficult customer label."
    )
    path = _write_extraction(tmp_path, extraction)

    errors = validate_extraction_output(path)

    assert any(
        "subjective durable customer label" in error for error in errors
    )


def test_pricing_commitments_fail(tmp_path: Path) -> None:
    extraction = _load_real_extraction()
    extraction["review_recommendations"].append(
        "Final price is approved for the visit."
    )
    path = _write_extraction(tmp_path, extraction)

    errors = validate_extraction_output(path)

    assert any("pricing commitment phrase" in error for error in errors)


def test_dispatch_or_scheduling_commitments_fail(tmp_path: Path) -> None:
    extraction = _load_real_extraction()
    extraction["review_recommendations"].append(
        "Appointment confirmed for tomorrow afternoon."
    )
    path = _write_extraction(tmp_path, extraction)

    errors = validate_extraction_output(path)

    assert any(
        "scheduling or dispatch commitment phrase" in error for error in errors
    )


def test_sensitive_trait_inference_phrases_fail(tmp_path: Path) -> None:
    extraction = _load_real_extraction()
    extraction["review_recommendations"].append(
        "Do not infer a mental illness from this source interaction."
    )
    path = _write_extraction(tmp_path, extraction)

    errors = validate_extraction_output(path)

    assert any("sensitive-trait inference phrase" in error for error in errors)


def test_main_returns_zero_for_real_extraction() -> None:
    result = main([str(EXTRACTION_PATH)])
    assert result == 0
