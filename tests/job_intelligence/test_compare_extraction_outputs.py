from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.job_intelligence.compare_extraction_outputs import (
    compare_extraction_outputs,
    main,
    validate_comparison_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip"
)
EXPECTED_PATH = FIXTURE_DIR / "expected-extraction.json"
MANUAL_PATH = FIXTURE_DIR / "manual-extraction-output-v0.json"
SOURCE_TEXT_PATH = FIXTURE_DIR / "source-interaction.txt"


def _load_manual_extraction() -> dict[str, Any]:
    return json.loads(MANUAL_PATH.read_text(encoding="utf-8"))


def _write_json(tmp_path: Path, payload: dict[str, Any]) -> Path:
    path = tmp_path / "manual-extraction-output.json"
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path


def test_real_manual_comparison_returns_passing_report() -> None:
    report = compare_extraction_outputs(EXPECTED_PATH, MANUAL_PATH)

    assert report["status"] == "passed"
    assert validate_comparison_report(report) == []


def test_report_contains_required_top_level_keys() -> None:
    report = compare_extraction_outputs(EXPECTED_PATH, MANUAL_PATH)

    assert {
        "comparison_id",
        "status",
        "expected_path",
        "actual_path",
        "source_text_path",
        "fixture_dir",
        "checks",
        "field_presence",
        "stable_field_matches",
        "differences",
        "non_goals_confirmed",
        "metadata",
    }.issubset(report)


def test_stable_field_matches_are_true_for_real_sample() -> None:
    report = compare_extraction_outputs(EXPECTED_PATH, MANUAL_PATH)

    assert report["stable_field_matches"] == {
        "source_interaction_id": True,
        "interaction_type": True,
        "service_vertical": True,
    }


def test_non_goals_confirmed_are_false_and_metadata_is_synthetic() -> None:
    report = compare_extraction_outputs(EXPECTED_PATH, MANUAL_PATH)

    assert report["non_goals_confirmed"] == {
        "model_called": False,
        "network_used": False,
        "runtime_used": False,
        "prompt_executed": False,
        "semantic_scoring_used": False,
        "persistence_used": False,
        "transcription_used": False,
        "pricing_automated": False,
        "dispatch_automated": False,
    }
    assert report["metadata"]["synthetic_only"] is True


def test_main_returns_zero_for_real_comparison() -> None:
    result = main([str(EXPECTED_PATH), str(MANUAL_PATH)])

    assert result == 0


def test_main_writes_output_json_file(tmp_path: Path) -> None:
    output_path = tmp_path / "job-intelligence-extraction-comparison.json"

    result = main(
        [
            str(EXPECTED_PATH),
            str(MANUAL_PATH),
            "--source-text",
            str(SOURCE_TEXT_PATH),
            "--fixture-dir",
            str(FIXTURE_DIR),
            "--output",
            str(output_path),
        ]
    )

    assert result == 0
    assert output_path.exists()
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert validate_comparison_report(report) == []


def test_stable_field_mismatch_fails(tmp_path: Path) -> None:
    manual = _load_manual_extraction()
    manual["source_interaction_id"] = "mismatched_interaction_id"
    actual_path = _write_json(tmp_path, manual)

    report = compare_extraction_outputs(EXPECTED_PATH, actual_path)

    assert report["status"] == "failed"
    assert report["stable_field_matches"]["source_interaction_id"] is False
    assert any("source_interaction_id" in item for item in report["differences"])
    assert validate_comparison_report(report) == []


def test_missing_non_empty_manual_field_fails(tmp_path: Path) -> None:
    manual = _load_manual_extraction()
    manual["policy_questions"] = []
    actual_path = _write_json(tmp_path, manual)

    report = compare_extraction_outputs(EXPECTED_PATH, actual_path)

    assert report["status"] == "failed"
    assert any("policy_questions" in item for item in report["differences"])
    assert validate_comparison_report(report) == []
