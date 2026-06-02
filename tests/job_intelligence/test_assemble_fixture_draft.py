from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.job_intelligence.assemble_fixture_draft import (
    assemble_job_profile_draft,
    assemble_review_packet,
    main,
    run_assembly,
)
from scripts.job_intelligence.validate_fixture import load_json

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip"
)


def _copy_fixture(tmp_path: Path, name: str = "fixture-copy") -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURE_DIR, destination)
    return destination


def test_run_assembly_returns_passing_report() -> None:
    report = run_assembly(FIXTURE_DIR)

    assert report["status"] == "passed"


def test_generated_artifacts_match_expected_fixture_outputs() -> None:
    extraction = load_json(FIXTURE_DIR / "expected-extraction.json")
    expected_draft = load_json(FIXTURE_DIR / "expected-job-profile-draft.json")
    expected_review_packet = load_json(
        FIXTURE_DIR / "expected-review-packet.json"
    )

    draft = assemble_job_profile_draft(extraction, expected_draft)
    review_packet = assemble_review_packet(
        extraction, draft, expected_review_packet
    )

    assert draft == expected_draft
    assert review_packet == expected_review_packet


def test_assembly_report_contains_required_top_level_keys() -> None:
    report = run_assembly(FIXTURE_DIR)

    assert {
        "assembly_id",
        "fixture_path",
        "status",
        "checks",
        "generated_artifacts",
        "comparison",
        "non_goals_confirmed",
        "metadata",
    }.issubset(report)


def test_non_goals_confirmed_are_false_and_metadata_is_synthetic() -> None:
    report = run_assembly(FIXTURE_DIR)

    assert report["non_goals_confirmed"] == {
        "model_called": False,
        "network_used": False,
        "runtime_used": False,
        "persistence_used": False,
        "transcription_used": False,
        "pricing_automated": False,
        "dispatch_automated": False,
    }
    assert report["metadata"]["synthetic_only"] is True


def test_main_returns_zero_for_real_fixture() -> None:
    result = main([str(FIXTURE_DIR)])
    assert result == 0


def test_main_writes_generated_artifacts_and_report(tmp_path: Path) -> None:
    output_dir = tmp_path / "job-intelligence-assembly"

    result = main([str(FIXTURE_DIR), "--output-dir", str(output_dir)])

    assert result == 0
    assert (output_dir / "generated-job-profile-draft.json").exists()
    assert (output_dir / "generated-review-packet.json").exists()
    assert (output_dir / "assembly-report.json").exists()

    report = json.loads(
        (output_dir / "assembly-report.json").read_text(encoding="utf-8")
    )
    assert report["status"] == "passed"


def test_broken_expected_review_packet_comparison_fails_closed(
    tmp_path: Path,
) -> None:
    fixture_dir = _copy_fixture(tmp_path)
    review_packet_path = fixture_dir / "expected-review-packet.json"
    review_packet = json.loads(review_packet_path.read_text(encoding="utf-8"))
    review_packet["job_profile_id"] = "mismatched_job_profile_id"
    review_packet_path.write_text(
        json.dumps(review_packet, indent=2) + "\n", encoding="utf-8"
    )

    report = run_assembly(fixture_dir)

    assert report["status"] == "failed"
    assert report["comparison"]["review_packet_matches_expected"] is False
    assert any(
        check["name"] == "review_packet_matches_expected"
        and check["status"] == "failed"
        for check in report["checks"]
    )
