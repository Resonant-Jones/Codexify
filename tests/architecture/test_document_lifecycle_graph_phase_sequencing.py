"""Regression tests for DLG classification and connection phase sequencing.

These tests exercise the Draft 2020-12 document-node schema only. They do not
implement or claim cross-record semantic validation, a canonical node corpus,
or runtime behavior.
"""

import copy
import json
from pathlib import Path

import jsonschema
import pytest


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "schemas/knowledge/document-lifecycle-graph.schema.json"
EXAMPLE_PATH = (
    REPO_ROOT
    / "docs/knowledge-graph/examples/document-lifecycle-graph.example.json"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def schema() -> dict:
    return load_json(SCHEMA_PATH)


@pytest.fixture(scope="module")
def validator(schema: dict) -> jsonschema.Draft202012Validator:
    return jsonschema.Draft202012Validator(schema)


def minimal_document_node() -> dict:
    """Return one deterministic schema-complete architecture-contract node."""
    return {
        "schema_version": "1.0.0",
        "record_type": "document_node",
        "document_id": "codexify:doc:architecture:phase-sequencing-fixture",
        "path": "docs/architecture/phase-sequencing-fixture.md",
        "title": "DLG Phase Sequencing Fixture",
        "kind": "architecture_contract",
        "summary": "Deterministic fixture for the DLG classification boundary.",
        "aliases": [],
        "authority_class": "normative_contract",
        "authority_scopes": ["DLG phase sequencing"],
        "lifecycle_state": "active",
        "freshness": {
            "state": "current",
            "verified_at": "2026-08-08T00:00:00Z",
            "verified_commit": "0" * 40,
            "triggers": ["fixture inputs change"],
        },
        "disposition": "accepted",
        "evidence_class": "proven-test",
        "owners": ["Codexify architecture maintainers"],
        "source_anchors": [
            {
                "path": "schemas/knowledge/document-lifecycle-graph.schema.json",
                "anchor_type": "schema",
                "invalidates_freshness": True,
            }
        ],
        "read_when": ["validating DLG phase sequencing"],
        "must_not_prove": ["cross-record relation completeness", "runtime behavior"],
        "retrieval_policy": {
            "default_policy": "include",
            "applicable_intents": ["architecture_decision"],
            "excluded_intents": [],
            "priority": "primary",
        },
        "temporal": {
            "created_at": "2026-08-08T00:00:00Z",
            "effective_from": "2026-08-08T00:00:00Z",
        },
        "content_hash": "0" * 64,
        "relations": [],
        "governing_adr_posture": "accepted",
    }


def reviewed_relation(relation_type: str, target_document_id: str) -> dict:
    return {
        "relation_type": relation_type,
        "target_document_id": target_document_id,
        "authority_scope": "DLG phase sequencing",
        "canonicality": "canonical",
        "review_status": "accepted",
        "rationale": "Deterministic reviewed relation for schema regression coverage.",
    }


def compatibility_pointer(pointer_relations: list[dict]) -> dict:
    node = minimal_document_node()
    node.update(
        {
            "document_id": "codexify:doc:architecture:phase-sequencing-pointer",
            "path": "docs/architecture/phase-sequencing-pointer.md",
            "title": "DLG Phase Sequencing Pointer Fixture",
            "kind": "compatibility_pointer",
            "authority_class": "pointer",
            "governing_adr_posture": "not_applicable",
            "relations": pointer_relations,
        }
    )
    return node


def proof_node() -> dict:
    node = minimal_document_node()
    node.update(
        {
            "document_id": "codexify:doc:proof:phase-sequencing-fixture",
            "path": "docs/architecture/proofs/phase-sequencing-fixture.md",
            "title": "DLG Phase Sequencing Proof Fixture",
            "kind": "proof",
            "authority_class": "evidence_only",
            "lifecycle_state": "frozen",
            "governing_adr_posture": "not_applicable",
        }
    )
    return node


def test_phase_1_accepted_architecture_contract_without_relations_validates(validator):
    validator.validate(minimal_document_node())


def test_accepted_architecture_contract_still_requires_accepted_adr_posture(validator):
    node = minimal_document_node()
    node["governing_adr_posture"] = "not_applicable"

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(node)


def test_phase_2_accepted_governed_by_relation_validates(validator):
    node = minimal_document_node()
    node["relations"] = [
        reviewed_relation(
            "governed_by",
            "codexify:doc:adr:056-document-lifecycle-graph",
        )
    ]

    validator.validate(node)


@pytest.mark.parametrize(
    ("pointer_count", "should_validate"),
    [(0, False), (1, True), (2, False)],
)
def test_compatibility_pointer_still_requires_exactly_one_pointer_relation(
    validator,
    pointer_count,
    should_validate,
):
    pointer_relation = reviewed_relation(
        "pointer_to",
        "codexify:doc:architecture:phase-sequencing-target",
    )
    node = compatibility_pointer(
        [copy.deepcopy(pointer_relation) for _ in range(pointer_count)]
    )

    if should_validate:
        validator.validate(node)
    else:
        with pytest.raises(jsonschema.ValidationError):
            validator.validate(node)


@pytest.mark.parametrize(
    ("field", "invalid_value"),
    [("authority_class", "supplementary"), ("lifecycle_state", "active")],
)
def test_proof_node_special_constraints_remain_enforced(
    validator,
    field,
    invalid_value,
):
    node = proof_node()
    node[field] = invalid_value

    with pytest.raises(jsonschema.ValidationError):
        validator.validate(node)


def test_existing_canonical_dlg_example_still_validates(validator):
    validator.validate(load_json(EXAMPLE_PATH))


def test_schema_is_valid_draft_2020_12(schema):
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"
    jsonschema.Draft202012Validator.check_schema(schema)
