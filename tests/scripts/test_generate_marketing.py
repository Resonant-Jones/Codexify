from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.marketing.pipeline import (
    CANDIDATE_MARKETABLE_CLAIM,
    CANDIDATE_METADATA_REFERENCE,
    CANDIDATE_RISK_OR_BLOCKER,
    STATUS_LIVE_PROVEN,
    STATUS_VERIFIED,
    Claim,
    collect_source_documents,
    enforce_banned_phrasing,
    enforce_no_evidence_no_claim,
    extract_claim_candidates,
    generate_marketing_artifacts,
    merge_claims_by_precedence,
)

FIXTURE_ROOT = Path("tests/fixtures/marketing/source")
SUITABILITY_FIXTURE_ROOT = Path("tests/fixtures/marketing/suitability/source")
GOLDEN_ROOT = Path("tests/fixtures/marketing/golden/CAMPAIGN_TEST")

FORBIDDEN_PUBLIC_PHRASES = [
    "not release-ready",
    "release-ready for this path: no",
    "failed before",
    "migrator failed",
    "task.failed",
    "blocked",
    "missing revision",
    "restore the missing",
    "re-run",
    "not yet runtime-owned",
    "worker runtime artifact",
]


def test_truth_extraction_and_precedence() -> None:
    documents = collect_source_documents(FIXTURE_ROOT)
    candidates = extract_claim_candidates(documents)
    merged = merge_claims_by_precedence(candidates)

    plain_claim = next(
        item
        for item in merged
        if item.claim
        == "Codexify tracks claim evidence through campaign receipts."
    )
    assert plain_claim.evidence_paths == ["docs/Campaign/CAMPAIGN_SAMPLE.md"]

    live_claim = next(
        item for item in merged if "Supported path proof" in item.claim
    )
    assert live_claim.status == STATUS_LIVE_PROVEN

    verified_claim = next(
        item for item in merged if "Verified regression coverage" in item.claim
    )
    assert verified_claim.status == STATUS_VERIFIED


def test_evidence_and_banned_phrase_gates() -> None:
    with pytest.raises(ValueError, match="no evidence"):
        enforce_no_evidence_no_claim(
            [
                Claim(
                    claim="No evidence claim",
                    proof_tier="implemented",
                    evidence_paths=[],
                    status="implemented",
                    channel="core",
                    approval_state="draft",
                )
            ],
            FIXTURE_ROOT,
        )

    with pytest.raises(ValueError, match="Banned phrase"):
        enforce_banned_phrasing(
            "This is guaranteed to be public launch ready.",
            ["guaranteed", "public launch ready"],
        )


def test_claim_suitability_classification() -> None:
    documents = collect_source_documents(SUITABILITY_FIXTURE_ROOT)
    candidates = extract_claim_candidates(documents)
    merged = merge_claims_by_precedence(candidates)

    by_claim = {item.claim: item for item in merged}
    assert (
        by_claim[
            "Codexify includes a deterministic draft marketing pipeline with evidence-ledger outputs."
        ].candidate_class
        == CANDIDATE_MARKETABLE_CLAIM
    )
    assert (
        by_claim[
            "Release-ready for this path: no; not release-ready until runtime proof passes."
        ].candidate_class
        == CANDIDATE_RISK_OR_BLOCKER
    )
    assert (
        by_claim[
            "The migrator failed before compose startup in the latest run."
        ].candidate_class
        == CANDIDATE_RISK_OR_BLOCKER
    )
    assert (
        by_claim[
            "Re-run the live Compose proof after the blocked dependency install path is restored."
        ].candidate_class
        == CANDIDATE_RISK_OR_BLOCKER
    )
    assert (
        by_claim[
            "Proof artifact: docs/proofs/2026-05-12-compose-proof.md"
        ].candidate_class
        == CANDIDATE_METADATA_REFERENCE
    )


def test_non_marketable_claims_route_to_review_notes(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(SUITABILITY_FIXTURE_ROOT, source_root)

    generate_marketing_artifacts(
        source_root=source_root,
        campaign_id="CAMPAIGN_CLAIM_HYGIENE",
        audience="local-first-builders",
        channels=["website", "social", "community"],
        mode="draft",
        output_root=output_root,
        generated_at="2026-05-12T00:00:00Z",
    )

    campaign_dir = output_root / "CAMPAIGN_CLAIM_HYGIENE"
    public_files = [
        "channel-website.md",
        "channel-social.md",
        "channel-community.md",
        "ad-copy.md",
    ]
    for name in public_files:
        content = (campaign_dir / name).read_text(encoding="utf-8").lower()
        for phrase in FORBIDDEN_PUBLIC_PHRASES:
            assert phrase not in content
    website = (campaign_dir / "channel-website.md").read_text(encoding="utf-8")
    assert (
        "Codexify includes a deterministic draft marketing pipeline with evidence-ledger outputs."
        in website
    )

    review_notes = (
        (campaign_dir / "review-notes.md").read_text(encoding="utf-8").lower()
    )
    assert "release-ready for this path: no" in review_notes
    assert "migrator failed" in review_notes
    assert "re-run the live compose proof" in review_notes
    assert (
        "proof artifact: docs/proofs/2026-05-12-compose-proof.md"
        in review_notes
    )

    evidence = json.loads((campaign_dir / "evidence-ledger.json").read_text())
    assert evidence["approval_state"] == "draft"
    assert evidence["mode"] == "draft"
    assert evidence["claim_summary"]["marketable_claim"] >= 1
    assert evidence["claim_summary"]["risk_or_blocker"] >= 1
    assert evidence["claim_summary"]["metadata_reference"] >= 1
    assert evidence["risk_flags"]
    assert "unsupported_readiness_risk" in evidence["risk_flags"]
    assert "failed_proof_risk" in evidence["risk_flags"]
    assert "blocked_run_risk" in evidence["risk_flags"]
    for claim in evidence["claims"]:
        assert claim["approval_state"] == "draft"


def test_golden_generation_is_deterministic(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(FIXTURE_ROOT, source_root)

    generate_marketing_artifacts(
        source_root=source_root,
        campaign_id="CAMPAIGN_TEST",
        audience="local-first-builders",
        channels=["website", "social", "community"],
        mode="draft",
        output_root=output_root,
        generated_at="2026-05-11T00:00:00Z",
    )

    generate_marketing_artifacts(
        source_root=source_root,
        campaign_id="CAMPAIGN_TEST",
        audience="local-first-builders",
        channels=["website", "social", "community"],
        mode="draft",
        output_root=output_root,
        generated_at="2026-05-11T00:00:00Z",
    )

    produced_dir = output_root / "CAMPAIGN_TEST"
    assert produced_dir.exists()

    golden_files = sorted(
        path for path in GOLDEN_ROOT.glob("*") if path.is_file()
    )
    for golden_file in golden_files:
        produced_file = produced_dir / golden_file.name
        assert produced_file.exists(), f"Missing {produced_file}"
        assert produced_file.read_text(
            encoding="utf-8"
        ) == golden_file.read_text(encoding="utf-8")


def test_cli_generates_expected_artifacts(tmp_path: Path) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(FIXTURE_ROOT, source_root)

    result = subprocess.run(
        [
            sys.executable,
            "scripts/marketing/generate_marketing.py",
            "--campaign-id",
            "CAMPAIGN_E2E",
            "--audience",
            "local-first-builders",
            "--channels",
            "website,social,community",
            "--mode",
            "draft",
            "--source-root",
            str(source_root),
            "--output-root",
            str(output_root),
            "--generated-at",
            "2026-05-11T00:00:00Z",
        ],
        cwd=Path(__file__).resolve().parents[2],
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["ok"] is True

    campaign_dir = output_root / "CAMPAIGN_E2E"
    expected_names = {
        "evidence-ledger.json",
        "core-brief.md",
        "channel-website.md",
        "channel-social.md",
        "channel-community.md",
        "ad-copy.md",
        "infographic-spec.md",
        "review-notes.md",
        "run-metadata.json",
    }
    assert expected_names.issubset(
        {path.name for path in campaign_dir.glob("*")}
    )

    evidence = json.loads((campaign_dir / "evidence-ledger.json").read_text())
    assert evidence["approval_state"] == "draft"
    assert evidence["mode"] == "draft"
    assert evidence["claims"]
    assert evidence["marketable_claims"]
    for claim in evidence["claims"]:
        assert claim["approval_state"] == "draft"
        assert claim["status"] in {"implemented", "verified", "live-proven"}
        assert claim["proof_tier"] in {"implemented", "verified", "live-proven"}
        assert claim["evidence_paths"]
        assert claim["candidate_class"]

    history = (
        source_root
        / "docs"
        / "Marketing"
        / "generated"
        / "history"
        / "run-history.jsonl"
    )
    assert history.exists()
    assert history.read_text(encoding="utf-8").strip()
