from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.marketing.pipeline import (
    ALLOWED_PRESENTATION_ROLES,
    CANDIDATE_MARKETABLE_CLAIM,
    CANDIDATE_METADATA_REFERENCE,
    CANDIDATE_RISK_OR_BLOCKER,
    EVIDENCE_LEDGER_SCHEMA_VERSION,
    PRESENTATION_INTERNAL_ANCHOR,
    PRESENTATION_METADATA_REFERENCE,
    PRESENTATION_PUBLIC_COPY_SEED,
    PRESENTATION_RISK_NOTE,
    PRESENTATION_SUPPORTING_EVIDENCE,
    STATUS_LIVE_PROVEN,
    STATUS_VERIFIED,
    Claim,
    assign_presentation_roles,
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

PUBLIC_ARTIFACT_NAMES = [
    "core-brief.md",
    "channel-website.md",
    "channel-social.md",
    "channel-community.md",
    "ad-copy.md",
    "infographic-spec.md",
]

DRAFT_SAFE_PUBLIC_PLACEHOLDER = (
    "No copy-ready public claims were available for this campaign. "
    "Review evidence ledger before publication."
)

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
    "task-2026",
    "docs/architecture/",
    "guardian/queue/",
    "codexify:queue:",
    "adr-020",
    "1dae1662d",
    "depends on",
    "per adr",
]

FORBIDDEN_PUBLIC_PATTERNS = [
    re.compile(r"\b[0-9a-f]{8,}\b", re.IGNORECASE),
]


def _public_artifact_texts(campaign_dir: Path) -> dict[str, str]:
    return {
        name: (campaign_dir / name).read_text(encoding="utf-8")
        for name in PUBLIC_ARTIFACT_NAMES
    }


def _assert_public_artifacts_clean(
    campaign_dir: Path,
    forbidden_claim_texts: list[str],
    require_placeholder: bool = False,
) -> None:
    artifacts = _public_artifact_texts(campaign_dir)
    combined = "\n".join(artifacts.values())
    for phrase in FORBIDDEN_PUBLIC_PHRASES:
        assert phrase not in combined.lower()
    for pattern in FORBIDDEN_PUBLIC_PATTERNS:
        assert not pattern.search(combined)
    for text in forbidden_claim_texts:
        assert text not in combined
    if require_placeholder:
        assert DRAFT_SAFE_PUBLIC_PLACEHOLDER in combined


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


def test_presentation_roles_classify_copy_readiness() -> None:
    documents = collect_source_documents(SUITABILITY_FIXTURE_ROOT)
    candidates = extract_claim_candidates(documents)
    merged = assign_presentation_roles(merge_claims_by_precedence(candidates))

    by_claim = {item.claim: item for item in merged}
    public_claim = by_claim[
        "Generated campaign claims are tied back to implementation receipts and reviewable evidence."
    ]
    assert public_claim.presentation_role == PRESENTATION_PUBLIC_COPY_SEED
    assert public_claim.copy_ready is True

    for claim_text in [
        "Campaign audit path docs/architecture/00-current-state.md records proof 1dae1662d.",
        "TASK-2026-05-11-CODING-RESULT traces task envelope execution.",
        "codexify:queue:coding-execution backs coding work-order execution.",
    ]:
        claim = by_claim[claim_text]
        assert claim.candidate_class == CANDIDATE_MARKETABLE_CLAIM
        assert claim.presentation_role == PRESENTATION_SUPPORTING_EVIDENCE
        assert claim.copy_ready is False

    for claim_text in ["Depends on: ADR-020", "Per ADR-020 contract:"]:
        claim = by_claim[claim_text]
        assert claim.presentation_role == PRESENTATION_INTERNAL_ANCHOR
        assert claim.copy_ready is False

    risk_claim = by_claim[
        "Release-ready for this path: no; not release-ready until runtime proof passes."
    ]
    assert risk_claim.presentation_role == PRESENTATION_RISK_NOTE
    assert risk_claim.copy_ready is False

    metadata_claim = by_claim[
        "Proof artifact: docs/proofs/2026-05-12-compose-proof.md"
    ]
    assert metadata_claim.presentation_role == PRESENTATION_METADATA_REFERENCE
    assert metadata_claim.copy_ready is False


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
        "infographic-spec.md",
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
    assert evidence["schema_version"] == EVIDENCE_LEDGER_SCHEMA_VERSION
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
        assert claim["candidate_class"]
        assert claim["channel_eligible"] in {True, False}
        assert claim["presentation_role"] in ALLOWED_PRESENTATION_ROLES
        assert claim["copy_ready"] in {True, False}
        assert isinstance(claim["copy_ready"], bool)
        assert isinstance(claim["risk_flags"], list)
        if claim["copy_ready"]:
            assert claim["candidate_class"] == CANDIDATE_MARKETABLE_CLAIM
            assert claim["presentation_role"] == PRESENTATION_PUBLIC_COPY_SEED
            assert claim["risk_flags"] == []

    risk_claims = [
        claim
        for claim in evidence["claims"]
        if claim["candidate_class"] == CANDIDATE_RISK_OR_BLOCKER
    ]
    assert risk_claims
    for claim in risk_claims:
        assert claim["channel_eligible"] is False
        assert claim["presentation_role"] == PRESENTATION_RISK_NOTE
        assert claim["copy_ready"] is False
    assert any(claim["risk_flags"] for claim in risk_claims)

    metadata_claims = [
        claim
        for claim in evidence["claims"]
        if claim["candidate_class"] == CANDIDATE_METADATA_REFERENCE
    ]
    assert metadata_claims
    for claim in metadata_claims:
        assert claim["channel_eligible"] is False
        assert claim["presentation_role"] == PRESENTATION_METADATA_REFERENCE
        assert claim["copy_ready"] is False

    implementation_breadcrumbs = [
        claim
        for claim in evidence["claims"]
        if any(
            marker in claim["claim"].lower()
            for marker in [
                "1dae1662d",
                "task-2026",
                "docs/architecture/",
                "codexify:queue:",
                "adr-020",
            ]
        )
    ]
    assert implementation_breadcrumbs
    for claim in implementation_breadcrumbs:
        assert claim["copy_ready"] is False

    marketable_from_claims = [
        claim for claim in evidence["claims"] if claim["channel_eligible"]
    ]
    non_marketable_from_claims = [
        claim for claim in evidence["claims"] if not claim["channel_eligible"]
    ]
    assert all(
        claim["candidate_class"] is not None for claim in evidence["claims"]
    )
    assert all(
        claim["channel_eligible"] is not None for claim in evidence["claims"]
    )
    assert all(
        claim["presentation_role"] is not None for claim in evidence["claims"]
    )
    assert all(claim["copy_ready"] is not None for claim in evidence["claims"])
    assert all(claim["risk_flags"] is not None for claim in evidence["claims"])
    assert all(
        isinstance(claim["channel_eligible"], bool)
        for claim in evidence["claims"]
    )
    assert all(
        isinstance(claim["risk_flags"], list) for claim in evidence["claims"]
    )
    assert len(evidence["marketable_claims"]) == len(marketable_from_claims)
    assert len(evidence["non_marketable_claims"]) == len(
        non_marketable_from_claims
    )
    assert evidence["marketable_claims"] == marketable_from_claims
    assert evidence["non_marketable_claims"] == non_marketable_from_claims
    assert evidence["claim_summary"]["marketable_claim"] >= len(
        evidence["marketable_claims"]
    )
    assert len(evidence["non_marketable_claims"]) == len(
        [claim for claim in evidence["claims"] if not claim["channel_eligible"]]
    )


def test_zero_copy_ready_claims_render_draft_safe_placeholders(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(SUITABILITY_FIXTURE_ROOT, source_root)

    campaign_file = source_root / "docs" / "Campaign" / "CAMPAIGN_SAMPLE.md"
    campaign_file.write_text(
        "\n".join(
            [
                "# Campaign Suitability Sample",
                "",
                "- Campaign audit path docs/architecture/00-current-state.md records proof 1dae1662d.",
                "- TASK-2026-05-11-CODING-RESULT traces task envelope execution.",
                "- codexify:queue:coding-execution backs coding work-order execution.",
                "- Depends on: ADR-020",
                "- Per ADR-020 contract:",
                "- Release-ready for this path: no; not release-ready until runtime proof passes.",
                "- The migrator failed before compose startup in the latest run.",
                "- Re-run the live Compose proof after the blocked dependency install path is restored.",
                "- Proof artifact: docs/proofs/2026-05-12-compose-proof.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_state = (
        source_root / "docs" / "architecture" / "00-current-state.md"
    )
    if current_state.exists():
        current_state.unlink()
    dev_log = source_root / "docs" / "DEV_LOG" / "Dev-Log-Sample.md"
    if dev_log.exists():
        dev_log.unlink()

    generate_marketing_artifacts(
        source_root=source_root,
        campaign_id="CAMPAIGN_PLACEHOLDER",
        audience="local-first-builders",
        channels=["website", "social", "community"],
        mode="draft",
        output_root=output_root,
        generated_at="2026-05-12T00:00:00Z",
    )

    campaign_dir = output_root / "CAMPAIGN_PLACEHOLDER"
    evidence = json.loads((campaign_dir / "evidence-ledger.json").read_text())
    assert all(claim["copy_ready"] is False for claim in evidence["claims"])
    assert any(
        claim["channel_eligible"] is True for claim in evidence["claims"]
    )
    forbidden_claim_texts = [
        claim["claim"]
        for claim in evidence["claims"]
        if claim["copy_ready"] is False
    ]
    _assert_public_artifacts_clean(
        campaign_dir,
        forbidden_claim_texts=forbidden_claim_texts,
        require_placeholder=True,
    )


def test_zero_copy_ready_claims_render_draft_safe_placeholders(
    tmp_path: Path,
) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(SUITABILITY_FIXTURE_ROOT, source_root)

    campaign_file = source_root / "docs" / "Campaign" / "CAMPAIGN_SAMPLE.md"
    campaign_file.write_text(
        "\n".join(
            [
                "# Campaign Suitability Sample",
                "",
                "- Campaign audit path docs/architecture/00-current-state.md records proof 1dae1662d.",
                "- TASK-2026-05-11-CODING-RESULT traces task envelope execution.",
                "- codexify:queue:coding-execution backs coding work-order execution.",
                "- Depends on: ADR-020",
                "- Per ADR-020 contract:",
                "- Release-ready for this path: no; not release-ready until runtime proof passes.",
                "- The migrator failed before compose startup in the latest run.",
                "- Re-run the live Compose proof after the blocked dependency install path is restored.",
                "- Proof artifact: docs/proofs/2026-05-12-compose-proof.md",
                "",
            ]
        ),
        encoding="utf-8",
    )
    current_state = (
        source_root / "docs" / "architecture" / "00-current-state.md"
    )
    if current_state.exists():
        current_state.unlink()
    dev_log = source_root / "docs" / "DEV_LOG" / "Dev-Log-Sample.md"
    if dev_log.exists():
        dev_log.unlink()

    generate_marketing_artifacts(
        source_root=source_root,
        campaign_id="CAMPAIGN_PLACEHOLDER",
        audience="local-first-builders",
        channels=["website", "social", "community"],
        mode="draft",
        output_root=output_root,
        generated_at="2026-05-12T00:00:00Z",
    )

    campaign_dir = output_root / "CAMPAIGN_PLACEHOLDER"
    evidence = json.loads((campaign_dir / "evidence-ledger.json").read_text())
    assert all(claim["copy_ready"] is False for claim in evidence["claims"])
    assert any(
        claim["channel_eligible"] is True for claim in evidence["claims"]
    )
    forbidden_claim_texts = [
        claim["claim"]
        for claim in evidence["claims"]
        if claim["copy_ready"] is False
    ]
    _assert_public_artifacts_clean(
        campaign_dir,
        forbidden_claim_texts=forbidden_claim_texts,
        require_placeholder=True,
    )


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
    assert evidence["schema_version"] == EVIDENCE_LEDGER_SCHEMA_VERSION
    assert evidence["approval_state"] == "draft"
    assert evidence["mode"] == "draft"
    assert evidence["claims"]
    assert evidence["marketable_claims"]
    for claim in evidence["claims"]:
        assert claim["approval_state"] == "draft"
        assert claim["status"] in {"implemented", "verified", "live-proven"}
        assert claim["proof_tier"] in {"implemented", "verified", "live-proven"}
        assert claim["presentation_role"] in ALLOWED_PRESENTATION_ROLES
        assert isinstance(claim["copy_ready"], bool)
        assert claim["evidence_paths"]
        assert claim["candidate_class"]
        assert claim["channel_eligible"] in {True, False}
        assert isinstance(claim["risk_flags"], list)
    assert all(
        claim["candidate_class"] is not None for claim in evidence["claims"]
    )
    assert all(
        claim["channel_eligible"] is not None for claim in evidence["claims"]
    )
    assert all(claim["risk_flags"] is not None for claim in evidence["claims"])
    assert all(
        isinstance(claim["channel_eligible"], bool)
        for claim in evidence["claims"]
    )
    assert all(
        isinstance(claim["risk_flags"], list) for claim in evidence["claims"]
    )
    assert evidence["marketable_claims"] == [
        claim
        for claim in evidence["claims"]
        if claim["channel_eligible"] is True
    ]
    assert evidence["non_marketable_claims"] == [
        claim
        for claim in evidence["claims"]
        if claim["channel_eligible"] is False
    ]

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
