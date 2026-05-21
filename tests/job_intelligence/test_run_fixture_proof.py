from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.job_intelligence.run_fixture_proof import (
    main,
    run_fixture_proof,
    validate_proof_report,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = (
    REPO_ROOT
    / "docs/specs/job-intelligence-layer/fixtures/plumbing-three-handle-drip"
)


def _copy_fixture(tmp_path: Path, name: str = "fixture-copy") -> Path:
    destination = tmp_path / name
    shutil.copytree(FIXTURE_DIR, destination)
    return destination


def test_run_fixture_proof_returns_passing_report() -> None:
    report = run_fixture_proof(FIXTURE_DIR)

    assert report["status"] == "passed"
    assert validate_proof_report(report) == []


def test_proof_report_contains_required_top_level_keys() -> None:
    report = run_fixture_proof(FIXTURE_DIR)

    assert {
        "proof_id",
        "fixture_path",
        "status",
        "checks",
        "artifacts",
        "non_goals_confirmed",
        "metadata",
    }.issubset(report)


def test_non_goals_confirmed_are_false_and_metadata_is_synthetic() -> None:
    report = run_fixture_proof(FIXTURE_DIR)

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


def test_main_writes_output_file(tmp_path: Path) -> None:
    output_path = tmp_path / "job-intelligence-proof.json"

    result = main([str(FIXTURE_DIR), "--output", str(output_path)])

    assert result == 0
    assert output_path.exists()
    report = json.loads(output_path.read_text(encoding="utf-8"))
    assert report["status"] == "passed"
    assert validate_proof_report(report) == []


def test_broken_fixture_relation_fails_closed(tmp_path: Path) -> None:
    fixture_dir = _copy_fixture(tmp_path)
    review_packet_path = fixture_dir / "expected-review-packet.json"
    review_packet = json.loads(review_packet_path.read_text(encoding="utf-8"))
    review_packet["job_profile_id"] = "mismatched_job_profile_id"
    review_packet_path.write_text(
        json.dumps(review_packet, indent=2) + "\n", encoding="utf-8"
    )

    report = run_fixture_proof(fixture_dir)

    assert report["status"] == "failed"
    assert validate_proof_report(report) == []
    assert any(
        check["name"] == "job_profile_id_matches_review_packet"
        and check["status"] == "failed"
        for check in report["checks"]
    )
