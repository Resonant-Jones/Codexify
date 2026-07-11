"""Tests for static Guardian Evidence Reducer input-bundle authoring aids."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from guardian.evidence_packets.reducer_contracts import ALLOWED_REDUCER_INPUT_CLASSES

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "docs/architecture/templates/guardian-evidence-reducer-input-bundle-template.v1.json"
FIXTURE = ROOT / "docs/architecture/fixtures/guardian-evidence-reducer-input-bundle.local-tooling.v1.json"
REQUIRED_FIELDS = {
    "schema_version", "bundle_id", "review_depth", "inputs",
    "operator_context", "provenance", "limits",
}
ALLOWED_REVIEW_DEPTHS = {"light", "medium", "high", "xhigh"}
REQUIRED_INPUT_FIELDS = {
    "input_id", "input_class", "source_ref", "evidence_posture", "notes",
}


def _load(path: Path) -> dict[str, object]:
    assert path.exists()
    value = json.loads(path.read_text())
    assert isinstance(value, dict)
    return value


def test_template_has_contract_shape_and_static_limits() -> None:
    template = _load(TEMPLATE)
    assert template["schema_version"] == "guardian_evidence_reducer_input_bundle.v1"
    assert set(template) == REQUIRED_FIELDS
    assert template["provenance"]["template"] is True
    assert template["review_depth"] in ALLOWED_REVIEW_DEPTHS
    example = template["inputs"][0]
    assert REQUIRED_INPUT_FIELDS <= set(example)
    assert ALLOWED_REVIEW_DEPTHS == {"light", "medium", "high", "xhigh"}
    assert ALLOWED_REDUCER_INPUT_CLASSES == {
        "static_docs", "static_fixtures", "validation_result", "command_run_snapshot",
        "command_run_event_snapshot", "receipt_metadata", "proof_index",
        "test_result_summary", "operator_supplied_context",
    }
    limits = " ".join(template["limits"]).lower()
    for phrase in (
        "not evidence", "not packet generation", "not evidence ingestion",
        "does not authorize file reads",
    ):
        assert phrase in limits


def test_fixture_has_contract_shape_inputs_and_static_limits() -> None:
    fixture = _load(FIXTURE)
    assert fixture["schema_version"] == "guardian_evidence_reducer_input_bundle.v1"
    assert set(fixture) == REQUIRED_FIELDS
    assert fixture["provenance"]["static_fixture"] is True
    assert fixture["review_depth"] in ALLOWED_REVIEW_DEPTHS
    assert len(fixture["inputs"]) >= 3
    classes = {item["input_class"] for item in fixture["inputs"]}
    assert {"static_docs", "static_fixtures", "test_result_summary"} <= classes
    for item in fixture["inputs"]:
        assert REQUIRED_INPUT_FIELDS <= set(item)
        assert item["input_class"] in ALLOWED_REDUCER_INPUT_CLASSES
        assert not item["source_ref"].startswith("/")
    limits = " ".join(fixture["limits"]).lower()
    for phrase in (
        "does not authorize file reads", "does not authorize evidence ingestion",
        "does not authorize packet generation", "does not authorize runtime reducer behavior",
        "does not authorize command bus calls", "does not authorize codex runner calls",
        "does not authorize pi loop invocation", "does not authorize source mutation",
        "does not authorize provider execution", "does not authorize execution ledger writes",
        "does not authorize workorder mutation", "does not authorize ui support",
        "does not authorize ci gating",
    ):
        assert phrase in limits


def test_existing_validation_and_dry_run_surfaces_remain_unchanged() -> None:
    for target in ("guardian-evidence-packets-validate", "guardian-evidence-reducer-dry-run"):
        proc = subprocess.run(
            ["make", target], cwd=ROOT, capture_output=True, text=True, check=False,
        )
        assert proc.returncode == 0, proc.stderr
    proc = subprocess.run(
        ["python3", "scripts/guardian/validate_evidence_packets.py", "--json"],
        cwd=ROOT, capture_output=True, text=True, check=False,
    )
    assert proc.returncode == 0, proc.stderr
    data = json.loads(proc.stdout)
    assert data["matched_count"] == 3
    assert all(
        "guardian-evidence-reducer-input-bundle" not in item["validated_packet_ref"]
        for item in data["packet_results"]
    )


def test_docs_link_static_bundle_surfaces() -> None:
    runtime_contract = (ROOT / "docs/architecture/guardian-evidence-packet-runtime-reducer-design-contract.md").read_text()
    reducer_contract = (ROOT / "docs/architecture/guardian-evidence-packet-reducer-contract.md").read_text()
    readme = (ROOT / "docs/architecture/README.md").read_text()
    current = (ROOT / "docs/architecture/00-current-state.md").read_text()
    for text in (runtime_contract, readme):
        assert "guardian-evidence-reducer-input-bundle-template.v1.json" in text
        assert "guardian-evidence-reducer-input-bundle.local-tooling.v1.json" in text
    assert "static ReducerInputBundle template and fixture" in reducer_contract
    assert "static Guardian Evidence Reducer input bundle template" in current
