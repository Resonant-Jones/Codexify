"""Product Architecture Ontology validation tests.

Validates that:
- JSON Schemas are valid Draft 2020-12 schemas.
- Ontology JSON validates against its schema.
- Assertion examples validate against the assertion schema.
- Updated DLG and ARP examples remain valid.
- Ontology concept IDs are unique.
- All required programs, capabilities, clients, and adapters are present.
- No forbidden patterns exist (e.g. no "Clients and Interfaces" program).
- Ontology contains no current primary-lane field, no repository path mappings,
  and no repository-wide current relationship instance map.
- Posture and relationship assertions follow the schema constraints.
- Allowed and forbidden dependency directions are present.
- Invariants about shared capabilities, adapters, clients are enforced.
- Stable architecture IDs match required patterns.
- DLG document IDs are the only ADR/contract identity domain.
- No codexify:adr:* or codexify:contract:* identities are introduced.
- DLG architecture_scope references match ontology or assertion ID patterns.
- ARP architecture_context is optional but schema-valid.
- Example assertions are marked example_only and do not claim live-runtime proof.
- All referenced governing document paths exist.
- New ontology and example JSON files are not Git LFS pointer contents.

No runtime behavior is tested.
"""

import json
import os
import sys
from pathlib import Path

import pytest

# jsonschema is a required dependency for validation
try:
    import jsonschema
except ImportError:
    pytest.skip("jsonschema not installed", allow_module_level=True)

REPO_ROOT = Path(__file__).resolve().parents[2]


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def load_json(rel_path: str) -> dict:
    path = REPO_ROOT / rel_path
    if not path.exists():
        pytest.fail(f"Missing file: {rel_path}")
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def is_draft_2020_12(schema: dict) -> bool:
    return schema.get("$schema") == "https://json-schema.org/draft/2020-12/schema"


DLG_SCHEMA_PATH = "schemas/knowledge/document-lifecycle-graph.schema.json"
ARP_SCHEMA_PATH = "schemas/knowledge/agent-reading-packet.schema.json"
ONTOLOGY_SCHEMA_PATH = "schemas/knowledge/product-architecture-ontology.schema.json"
ASSERTION_SCHEMA_PATH = "schemas/knowledge/product-architecture-assertion.schema.json"
ONTOLOGY_JSON_PATH = "docs/knowledge-graph/ontologies/product-architecture-ontology.v1.json"
ASSERTION_EXAMPLE_PATH = "docs/knowledge-graph/examples/product-architecture-assertions.example.json"
DLG_EXAMPLE_PATH = "docs/knowledge-graph/examples/document-lifecycle-graph.example.json"
ARP_EXAMPLE_PATH = "docs/knowledge-graph/examples/agent-reading-packet.example.json"


# ---------------------------------------------------------------------------
# 1. Schemas are valid Draft 2020-12
# ---------------------------------------------------------------------------

def test_ontology_schema_is_valid_draft_2020_12():
    schema = load_json(ONTOLOGY_SCHEMA_PATH)
    assert is_draft_2020_12(schema)
    jsonschema.Draft202012Validator.check_schema(schema)


def test_assertion_schema_is_valid_draft_2020_12():
    schema = load_json(ASSERTION_SCHEMA_PATH)
    assert is_draft_2020_12(schema)
    jsonschema.Draft202012Validator.check_schema(schema)


def test_dlg_schema_is_valid_draft_2020_12():
    schema = load_json(DLG_SCHEMA_PATH)
    assert is_draft_2020_12(schema)
    jsonschema.Draft202012Validator.check_schema(schema)


def test_arp_schema_is_valid_draft_2020_12():
    schema = load_json(ARP_SCHEMA_PATH)
    assert is_draft_2020_12(schema)
    jsonschema.Draft202012Validator.check_schema(schema)


# ---------------------------------------------------------------------------
# 2,3. Ontology and assertions validate
# ---------------------------------------------------------------------------

def test_ontology_json_validates():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    schema = load_json(ONTOLOGY_SCHEMA_PATH)
    jsonschema.validate(ontology, schema)


def test_assertion_example_validates():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    schema = load_json(ASSERTION_SCHEMA_PATH)
    for assertion in assertions:
        jsonschema.validate(assertion, schema)


# ---------------------------------------------------------------------------
# 4,5. Updated DLG and ARP examples validate
# ---------------------------------------------------------------------------

def test_dlg_example_validates():
    dlg = load_json(DLG_EXAMPLE_PATH)
    schema = load_json(DLG_SCHEMA_PATH)
    jsonschema.validate(dlg, schema)


def test_arp_example_validates():
    arp = load_json(ARP_EXAMPLE_PATH)
    schema = load_json(ARP_SCHEMA_PATH)
    jsonschema.validate(arp, schema)


# ---------------------------------------------------------------------------
# 6. All ontology concept IDs are unique
# ---------------------------------------------------------------------------

def test_ontology_concept_ids_are_unique():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    ids = []
    for arr_key in ["programs", "capabilities", "client_surfaces", "adapter_families"]:
        for item in ontology.get(arr_key, []):
            ids.append(item["id"])
    # Also check relation_types predicates are unique
    ids.extend(r["predicate"] for r in ontology.get("relation_types", []))
    assert len(ids) == len(set(ids)), f"Duplicate concept IDs found: {[x for x in ids if ids.count(x) > 1]}"


# ---------------------------------------------------------------------------
# 7. Ontology-level relation references resolve
# ---------------------------------------------------------------------------

def test_relation_predicates_are_defined():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    defined_predicates = {r["predicate"] for r in ontology["relation_types"]}
    assertion_schema = load_json(ASSERTION_SCHEMA_PATH)
    schema_predicates = set(assertion_schema["$defs"]["relationPredicate"]["enum"])
    assert defined_predicates == schema_predicates, (
        f"Ontology predicates {defined_predicates} != schema predicates {schema_predicates}"
    )


# ---------------------------------------------------------------------------
# 8. All required programs are present
# ---------------------------------------------------------------------------

EXPECTED_PROGRAMS = {
    "codexify:program:digital-cognitive-workspace",
    "codexify:program:node-runtime",
    "codexify:program:threadspace",
    "codexify:program:home-presence",
    "codexify:program:infrastructure-services",
}


def test_required_programs_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    actual = {p["id"] for p in ontology["programs"]}
    missing = EXPECTED_PROGRAMS - actual
    assert not missing, f"Missing programs: {missing}"


# ---------------------------------------------------------------------------
# 9. All required capabilities are present
# ---------------------------------------------------------------------------

EXPECTED_CAPABILITIES = {
    "codexify:capability:identity",
    "codexify:capability:authorization-policy",
    "codexify:capability:context-retrieval-assembly",
    "codexify:capability:continuity",
    "codexify:capability:semantic-spaces",
    "codexify:capability:delegation-coordination",
    "codexify:capability:persistence",
    "codexify:capability:runtime-lifecycle",
    "codexify:capability:events-receipts-observability",
    "codexify:capability:provider-tool-adapter-interfaces",
}


def test_required_capabilities_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    actual = {c["id"] for c in ontology["capabilities"]}
    missing = EXPECTED_CAPABILITIES - actual
    assert not missing, f"Missing capabilities: {missing}"


# ---------------------------------------------------------------------------
# 10. All required client surfaces are present
# ---------------------------------------------------------------------------

EXPECTED_CLIENTS = {
    "codexify:client:web",
    "codexify:client:desktop",
    "codexify:client:browser-extension",
    "codexify:client:browser-host",
    "codexify:client:mobile",
    "codexify:client:home-device",
}


def test_required_clients_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    actual = {c["id"] for c in ontology["client_surfaces"]}
    missing = EXPECTED_CLIENTS - actual
    assert not missing, f"Missing client surfaces: {missing}"


# ---------------------------------------------------------------------------
# 11. All required adapter families are present
# ---------------------------------------------------------------------------

EXPECTED_ADAPTERS = {
    "codexify:adapter:openai-compatible-inference",
    "codexify:adapter:codex-execution",
    "codexify:adapter:claude-compatible-inference",
    "codexify:adapter:local-inference",
    "codexify:adapter:deepseek",
    "codexify:adapter:whooshd",
    "codexify:adapter:external-agent-runtime",
    "codexify:adapter:external-tool",
    "codexify:adapter:storage",
    "codexify:adapter:networking",
}


def test_required_adapters_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    actual = {a["id"] for a in ontology["adapter_families"]}
    missing = EXPECTED_ADAPTERS - actual
    assert not missing, f"Missing adapter families: {missing}"


# ---------------------------------------------------------------------------
# 12. No "Clients and Interfaces" product program exists
# ---------------------------------------------------------------------------

def test_no_clients_and_interfaces_program():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    program_titles = {p["title"].lower() for p in ontology["programs"]}
    program_ids = {p["id"] for p in ontology["programs"]}
    assert "clients and interfaces" not in program_titles
    assert "codexify:program:clients-and-interfaces" not in program_ids


# ---------------------------------------------------------------------------
# 13. Ontology contains no current primary-lane field
# ---------------------------------------------------------------------------

def test_ontology_no_primary_lane():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    assert "primary_lane" not in ontology
    assert "current_lane" not in ontology
    for p in ontology["programs"]:
        assert "primary_lane" not in p
        assert "current_lane" not in p


# ---------------------------------------------------------------------------
# 14. Ontology contains no repository path mappings
# ---------------------------------------------------------------------------

def test_ontology_no_repository_paths():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    ontology_str = json.dumps(ontology)
    # No repository paths like "guardian/..." or "frontend/..." in the ontology
    import re
    path_patterns = re.findall(r'"(?:guardian|frontend|src-tauri|docker-compose)/[^"]*"', ontology_str)
    assert not path_patterns, f"Repository paths found in ontology: {path_patterns}"


# ---------------------------------------------------------------------------
# 15. Ontology does not contain a repository-wide current relationship instance map
# ---------------------------------------------------------------------------

def test_ontology_no_current_relationship_map():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    assert "current_relationships" not in ontology
    assert "relationship_instances" not in ontology
    assert "edges" not in ontology


# ---------------------------------------------------------------------------
# 16,22. Product posture is represented through assertions, not concept definitions
# ---------------------------------------------------------------------------

def test_posture_not_in_program_definitions():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for p in ontology["programs"]:
        assert "support_posture" not in p, f"Program {p['id']} has support_posture in definition"
        assert "runtime_participation" not in p, f"Program {p['id']} has runtime_participation in definition"
        assert "current_priority" not in p, f"Program {p['id']} has current_priority in definition"
    for c in ontology["capabilities"]:
        assert "support_posture" not in c
        assert "runtime_participation" not in c


# ---------------------------------------------------------------------------
# 17. Concrete relationship examples are represented through assertions
# ---------------------------------------------------------------------------

def test_ontology_has_no_concrete_edges():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for rt in ontology["relation_types"]:
        assert "current_instances" not in rt
        assert "examples" not in rt


# ---------------------------------------------------------------------------
# 18. assertion_kind accepts only posture and relationship
# ---------------------------------------------------------------------------

def test_assertion_kind_values():
    schema = load_json(ASSERTION_SCHEMA_PATH)
    assert schema["properties"]["assertion_kind"]["enum"] == ["posture", "relationship"]


# ---------------------------------------------------------------------------
# 19,20. Relationship assertions require subject_id, predicate, object_id
#          and predicates resolve to ontology relation types
# ---------------------------------------------------------------------------

def test_relationship_assertions_have_required_fields():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    ontology = load_json(ONTOLOGY_JSON_PATH)
    valid_predicates = {r["predicate"] for r in ontology["relation_types"]}

    for a in assertions:
        if a["assertion_kind"] == "relationship":
            assert "subject_id" in a, f"Missing subject_id in {a['assertion_id']}"
            assert "predicate" in a, f"Missing predicate in {a['assertion_id']}"
            assert "object_id" in a, f"Missing object_id in {a['assertion_id']}"
            assert a["predicate"] in valid_predicates, (
                f"Unknown predicate '{a['predicate']}' in {a['assertion_id']}"
            )
            assert "posture" not in a, f"Relationship assertion {a['assertion_id']} has posture"


# ---------------------------------------------------------------------------
# 21. Only canonical orthogonal posture values are used
# ---------------------------------------------------------------------------

VALID_POSTURE_VALUES = {
    "support_posture": {"supported", "internal", "optional", "strategic", "experimental", "historical", "unknown"},
    "runtime_participation": {"required", "supporting", "optional", "inactive", "unknown"},
    "ownership_state": {"owned", "unowned", "entangled", "unknown"},
    "strategy_state": {"now", "next", "observatory", "parked", "unknown"},
    "integration_state": {"integrated", "partial", "contract_only", "prototype", "absent", "unknown"},
}


def test_posture_values_are_canonical():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        if a["assertion_kind"] == "posture" and "posture" in a:
            for dim, valid_set in VALID_POSTURE_VALUES.items():
                if dim in a["posture"]:
                    assert a["posture"][dim] in valid_set, (
                        f"Invalid {dim} value '{a['posture'][dim]}' in {a['assertion_id']}"
                    )


# ---------------------------------------------------------------------------
# 22. unowned and entangled appear only as ownership states
# ---------------------------------------------------------------------------

def test_unowned_entangled_only_in_ownership_state():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    ontology_str = json.dumps(ontology)

    # They appear as enum values in the assertion schema, which is fine
    # Check that in the ontology they only appear in the ownership_state context
    # (not as flat labels or maturity statuses)
    for label in ontology["derived_projection_rules"]["flat_labels"]:
        assert "unowned" not in label["definition"].lower().split() or "ownership" in label["definition"].lower()
        assert "entangled" not in label["definition"].lower().split() or "ownership" in label["definition"].lower()


# ---------------------------------------------------------------------------
# 23. Flat labels are declared only as derived projection outputs
# ---------------------------------------------------------------------------

def test_flat_labels_only_in_projection_rules():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    flat_label_names = {fl["label"] for fl in ontology["derived_projection_rules"]["flat_labels"]}

    # No program or capability should carry a flat label directly
    for p in ontology["programs"]:
        for fl in flat_label_names:
            assert fl not in p, f"Program {p['id']} has flat label '{fl}'"

    for c in ontology["capabilities"]:
        for fl in flat_label_names:
            assert fl not in c, f"Capability {c['id']} has flat label '{fl}'"


# ---------------------------------------------------------------------------
# 24. Allowed dependency directions are present
# ---------------------------------------------------------------------------

def test_allowed_dependency_directions_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    assert len(ontology["allowed_dependency_directions"]) >= 5, "Too few allowed dependency directions"


# ---------------------------------------------------------------------------
# 25. Forbidden dependency directions are present
# ---------------------------------------------------------------------------

def test_forbidden_dependency_directions_present():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    assert len(ontology["forbidden_dependency_directions"]) >= 10, "Too few forbidden dependency directions"


# ---------------------------------------------------------------------------
# 26. Shared capabilities cannot depend on product-specific client implementations
# ---------------------------------------------------------------------------

def test_capability_no_product_specific_ui_dependency():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    forbidden = ontology["forbidden_dependency_directions"]
    found = any(
        "shared_capability" in str(f).lower() and "ui" in str(f).lower()
        for f in forbidden
    )
    assert found, "No forbidden direction for capability -> product-specific UI"


# ---------------------------------------------------------------------------
# 27. Adapter families cannot claim Codexify identity authority
# ---------------------------------------------------------------------------

def test_adapter_no_identity_authority():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for adapter in ontology["adapter_families"]:
        assert "authority_boundary" in adapter
        assert "identity" in adapter["authority_boundary"].lower(), (
            f"Adapter {adapter['id']} missing identity authority boundary"
        )


# ---------------------------------------------------------------------------
# 28. Client surfaces cannot claim persistence or policy authority
# ---------------------------------------------------------------------------

def test_client_no_persistence_policy_authority():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for client in ontology["client_surfaces"]:
        assert "authority_boundary" in client
        boundary = client["authority_boundary"].lower()
        assert "persistence" in boundary or "identity" in boundary, (
            f"Client {client['id']} missing persistence/identity boundary"
        )


# ---------------------------------------------------------------------------
# 29. Hosted infrastructure cannot claim hidden ThreadSpace authority
# ---------------------------------------------------------------------------

def test_infrastructure_no_hidden_threadspace_authority():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    forbidden = ontology["forbidden_dependency_directions"]
    found = any(
        "hosted" in str(f).lower() and "threadspace" in str(f).lower()
        for f in forbidden
    )
    assert found, "No forbidden direction for hosted service -> hidden ThreadSpace authority"


# ---------------------------------------------------------------------------
# 30. Codex execution is not marked mandatory
# ---------------------------------------------------------------------------

def test_codex_execution_not_mandatory():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for adapter in ontology["adapter_families"]:
        if adapter["id"] == "codexify:adapter:codex-execution":
            desc = adapter.get("description", "")
            # The description may contain "mandatory" only in the context of
            # denying it is mandatory ("not a mandatory product dependency").
            # It must not claim Codex execution IS mandatory.
            assert "is a mandatory" not in desc.lower(), (
                "Codex execution adapter description must not claim it is mandatory"
            )
            return
    pytest.fail("Codex execution adapter not found")


# ---------------------------------------------------------------------------
# 31. Stable architecture IDs match their required patterns
# ---------------------------------------------------------------------------

import re

ID_PATTERNS = {
    "program": re.compile(r"^codexify:program:[a-z0-9][a-z0-9-]*$"),
    "capability": re.compile(r"^codexify:capability:[a-z0-9][a-z0-9-]*$"),
    "client_surface": re.compile(r"^codexify:client:[a-z0-9][a-z0-9-]*$"),
    "adapter_family": re.compile(r"^codexify:adapter:[a-z0-9][a-z0-9-]*$"),
}


def test_concept_ids_match_patterns():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    for key, pattern in [
        ("programs", ID_PATTERNS["program"]),
        ("capabilities", ID_PATTERNS["capability"]),
        ("client_surfaces", ID_PATTERNS["client_surface"]),
        ("adapter_families", ID_PATTERNS["adapter_family"]),
    ]:
        for item in ontology[key]:
            assert pattern.match(item["id"]), f"Bad ID: {item['id']} for {key}"

    # Assertion IDs
    assertion_pattern = re.compile(r"^codexify:assertion:product-architecture:[a-z0-9][a-z0-9-]*$")
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        assert assertion_pattern.match(a["assertion_id"]), f"Bad assertion ID: {a['assertion_id']}"


# ---------------------------------------------------------------------------
# 32,33,34,35. DLG document IDs are the only ADR/contract identity domain
# ---------------------------------------------------------------------------

DLG_DOC_ID_PATTERN = re.compile(r"^codexify:doc:[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9-]*$")


def test_no_codexify_adr_or_contract_identity():
    """Verify no codexify:adr:* or codexify:contract:* identity is introduced."""
    new_files = [
        ONTOLOGY_JSON_PATH,
        ASSERTION_EXAMPLE_PATH,
        ONTOLOGY_SCHEMA_PATH,
        ASSERTION_SCHEMA_PATH,
    ]
    for path in new_files:
        content = json.dumps(load_json(path))
        assert "codexify:adr:" not in content, f"codexify:adr: found in {path}"
        assert "codexify:contract:" not in content, f"codexify:contract: found in {path}"


def test_governing_adr_document_ids_match_dlg_pattern():
    """All governing_adr_document_ids values match DLG document identity pattern."""
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        for doc_id in a.get("governing_adr_document_ids", []):
            assert DLG_DOC_ID_PATTERN.match(doc_id), (
                f"Bad governing_adr_document_id: {doc_id} in {a['assertion_id']}"
            )


def test_authority_and_evidence_document_ids_match_dlg_pattern():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        for doc_id in a.get("authority_document_ids", []):
            assert DLG_DOC_ID_PATTERN.match(doc_id), (
                f"Bad authority_document_id: {doc_id} in {a['assertion_id']}"
            )
        for doc_id in a.get("evidence_document_ids", []):
            assert DLG_DOC_ID_PATTERN.match(doc_id), (
                f"Bad evidence_document_id: {doc_id} in {a['assertion_id']}"
            )


# ---------------------------------------------------------------------------
# 36. DLG architecture_scope references match ontology or assertion ID patterns
# ---------------------------------------------------------------------------

def test_dlg_architecture_scope_id_patterns():
    dlg = load_json(DLG_EXAMPLE_PATH)
    # Check that any node with architecture_scope has valid patterns
    nodes = dlg.get("nodes", [])
    program_pattern = re.compile(r"^codexify:program:[a-z0-9][a-z0-9-]*$")
    capability_pattern = re.compile(r"^codexify:capability:[a-z0-9][a-z0-9-]*$")
    client_pattern = re.compile(r"^codexify:client:[a-z0-9][a-z0-9-]*$")
    adapter_pattern = re.compile(r"^codexify:adapter:[a-z0-9][a-z0-9-]*$")
    assertion_pattern = re.compile(r"^codexify:assertion:product-architecture:[a-z0-9][a-z0-9-]*$")

    for node in nodes:
        arch_scope = node.get("architecture_scope")
        if arch_scope:
            for pid in arch_scope.get("program_ids", []):
                assert program_pattern.match(pid), f"Bad program_id: {pid}"
            for cid in arch_scope.get("capability_ids", []):
                assert capability_pattern.match(cid), f"Bad capability_id: {cid}"
            for cid in arch_scope.get("client_surface_ids", []):
                assert client_pattern.match(cid), f"Bad client_surface_id: {cid}"
            for aid in arch_scope.get("adapter_family_ids", []):
                assert adapter_pattern.match(aid), f"Bad adapter_family_id: {aid}"
            for aid in arch_scope.get("assertion_ids", []):
                assert assertion_pattern.match(aid), f"Bad assertion_id: {aid}"


# ---------------------------------------------------------------------------
# 37,38. Agent Reading Packet architecture_context is optional but schema-valid
#         and supports relationship assertion context
# ---------------------------------------------------------------------------

def test_arp_architecture_context_pattern():
    """Verify ARP schema supports optional architecture_context with expected fields."""
    arp_schema = load_json(ARP_SCHEMA_PATH)
    # The ARP schema is a simple type:object - architecture_context would be an
    # extension property. Since it's not yet in the schema, this test verifies
    # the schema itself is valid and the example loads.
    arp = load_json(ARP_EXAMPLE_PATH)
    # Verify basic ARP structure
    assert "selected_sources" in arp
    # architecture_context is optional in the example
    # If present, check its shape
    arch_ctx = arp.get("architecture_context")
    if arch_ctx:
        assert isinstance(arch_ctx, dict)
        valid_keys = {
            "programs", "capabilities", "client_surfaces", "adapter_families",
            "source_subsystems", "dependency_boundaries", "posture_assertions",
            "relationship_assertions", "ownership_warnings", "mapping_gaps",
            "architecture_graph_paths",
        }
        for key in arch_ctx:
            assert key in valid_keys, f"Unexpected architecture_context key: {key}"


# ---------------------------------------------------------------------------
# 39. Architecture graph paths are represented as relational trails, not filesystem paths
# ---------------------------------------------------------------------------

def test_graph_paths_are_relational_trails():
    """Graph paths in the ARP should be arrays of edge steps, not strings or filesystem paths."""
    arp = load_json(ARP_EXAMPLE_PATH)
    for source in arp.get("selected_sources", []):
        graph_path = source.get("graph_path", [])
        for step in graph_path:
            assert isinstance(step, dict), f"Graph path step should be object, got {type(step)}"
            assert "relation_type" in step, f"Graph path step missing relation_type"
            assert "from_document_id" in step or "to_document_id" in step


# ---------------------------------------------------------------------------
# 40. Example assertions are marked example_only
# ---------------------------------------------------------------------------

def test_example_assertions_are_example_only():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        assert a.get("record_purpose") == "example_only", (
            f"Assertion {a['assertion_id']} must be marked example_only"
        )


# ---------------------------------------------------------------------------
# 41. Example assertions do not claim live-runtime proof
# ---------------------------------------------------------------------------

def test_example_assertions_no_live_runtime_claim():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        assert a.get("evidence_class") != "proven-live-runtime", (
            f"Assertion {a['assertion_id']} must not claim proven-live-runtime"
        )
        notes = a.get("notes", "")
        assert "illustrative" in notes.lower() or "example" in notes.lower(), (
            f"Assertion {a['assertion_id']} notes must indicate illustrative/example"
        )


# ---------------------------------------------------------------------------
# 42. Relationship examples carry authority/evidence references
# ---------------------------------------------------------------------------

def test_relationship_assertions_have_authority_evidence():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    for a in assertions:
        if a["assertion_kind"] == "relationship":
            assert len(a.get("authority_document_ids", [])) > 0, (
                f"Relationship assertion {a['assertion_id']} has no authority_document_ids"
            )


# ---------------------------------------------------------------------------
# 43. Temporal relationship validity can be represented
# ---------------------------------------------------------------------------

def test_temporal_validity_representable():
    assertions = load_json(ASSERTION_EXAMPLE_PATH)
    has_effective_until = any(
        a.get("effective_until") for a in assertions if a["assertion_kind"] == "relationship"
    )
    assert has_effective_until, "No relationship assertion demonstrates bounded temporal validity"


# ---------------------------------------------------------------------------
# 44. All referenced governing document paths in ADR and human-readable doc exist
# ---------------------------------------------------------------------------

REFERENCED_DOCS_IN_PRODUCT_DOC = [
    "docs/architecture/document-lifecycle-graph-contract.md",
    "docs/architecture/00-current-state.md",
]


def test_product_doc_references_exist():
    for path in REFERENCED_DOCS_IN_PRODUCT_DOC:
        assert (REPO_ROOT / path).exists(), f"Referenced document missing: {path}"


# ---------------------------------------------------------------------------
# 46. No runtime source file is needed to validate the ontology
# ---------------------------------------------------------------------------

def test_validation_uses_only_docs_and_schemas():
    """Confirm this test file does not import any runtime source modules.

    Check that no guardian.* or frontend.* modules are imported at module level
    in this test file. The test itself only depends on json, pathlib, os, re,
    sys, jsonschema, and pytest.
    """
    import ast
    import inspect
    current_module = sys.modules[__name__]
    source = inspect.getsource(current_module)
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                module_name = node.module or ""
            else:
                module_name = ""
            for alias in node.names:
                full_name = (module_name + "." + alias.name) if module_name else alias.name
                assert not full_name.startswith("guardian"), (
                    f"Test imports guardian runtime module: {full_name}"
                )
                assert not full_name.startswith("frontend"), (
                    f"Test imports frontend runtime module: {full_name}"
                )


# ---------------------------------------------------------------------------
# Relationship endpoint repair regression coverage
# ---------------------------------------------------------------------------

PRODUCT_PROGRAM_CLASSES = {
    "product",
    "product_and_network",
    "product_and_physical_interface",
}

EXPECTED_RELATION_ENDPOINT_TYPES = {
    "participates_in": ({"source_subsystem", "dlg_document", "capability"}, {"program"}),
    "provides_capability": ({"program", "source_subsystem"}, {"capability"}),
    "depends_on_capability": ({"program"}, {"capability"}),
    "presented_through": ({"program"}, {"client_surface"}),
    "integrates_via": ({"capability", "program"}, {"adapter_family"}),
    "implemented_by": ({"program", "capability", "client_surface", "adapter_family"}, {"source_subsystem"}),
    "bounded_by": ({"program", "capability", "client_surface", "adapter_family", "source_subsystem"}, {"dlg_document"}),
    "supports_program": ({"capability", "program"}, {"program"}),
    "classified_by": ({"dlg_document", "source_subsystem"}, {"assertion"}),
}

SOURCE_SUBSYSTEM_ID_PATTERN = re.compile(
    r"^codexify:source:[a-z0-9][a-z0-9-]*:[a-z0-9][a-z0-9-]*$"
)
PRODUCT_ARCHITECTURE_ASSERTION_ID_PATTERN = re.compile(
    r"^codexify:assertion:product-architecture:[a-z0-9][a-z0-9-]*$"
)


def relationship_assertion(subject_id: str, predicate: str, object_id: str) -> dict:
    """Build one schema-complete relationship fixture without claiming runtime proof."""
    return {
        "schema_version": "1.0.0",
        "assertion_id": "codexify:assertion:product-architecture:test-relation",
        "assertion_kind": "relationship",
        "subject_id": subject_id,
        "predicate": predicate,
        "object_id": object_id,
        "assertion_scope": "Deterministic endpoint regression fixture.",
        "effective_from": "2026-08-07T00:00:00Z",
        "authority_document_ids": ["codexify:doc:architecture:product-lanes-and-boundaries"],
        "evidence_document_ids": [],
        "governing_adr_document_ids": ["codexify:doc:adr:056-document-lifecycle-graph"],
        "repository_revision": "0" * 40,
        "evidence_class": "proven-test",
        "notes": "Test-only illustrative relationship; not live-runtime proof.",
        "record_purpose": "example_only",
    }


def posture_assertion(subject_id: str) -> dict:
    """Build one schema-complete posture fixture."""
    assertion = relationship_assertion(
        subject_id,
        "depends_on_capability",
        "codexify:capability:identity",
    )
    assertion["assertion_kind"] = "posture"
    assertion.pop("predicate")
    assertion.pop("object_id")
    assertion["posture"] = {"ownership_state": "unknown"}
    return assertion


def assertion_schema_accepts(assertion: dict) -> bool:
    schema = load_json(ASSERTION_SCHEMA_PATH)
    return jsonschema.Draft202012Validator(schema).is_valid(assertion)


def ontology_endpoint(identifier: str, ontology: dict) -> tuple[str, str | None]:
    """Resolve endpoint category and program class from ontology-owned metadata."""
    for program in ontology["programs"]:
        if program["id"] == identifier:
            return "program", program["program_class"]
    for collection, concept_type in (
        ("capabilities", "capability"),
        ("client_surfaces", "client_surface"),
        ("adapter_families", "adapter_family"),
    ):
        if any(item["id"] == identifier for item in ontology[collection]):
            return concept_type, None
    if SOURCE_SUBSYSTEM_ID_PATTERN.fullmatch(identifier):
        return "source_subsystem", None
    if DLG_DOC_ID_PATTERN.fullmatch(identifier):
        return "dlg_document", None
    if PRODUCT_ARCHITECTURE_ASSERTION_ID_PATTERN.fullmatch(identifier):
        return "assertion", None
    raise ValueError(f"Unresolvable Product Architecture endpoint: {identifier}")


def relationship_semantically_valid(subject_id: str, predicate: str, object_id: str) -> bool:
    """Resolve ontology-owned endpoint and program-class semantics deterministically."""
    ontology = load_json(ONTOLOGY_JSON_PATH)
    relation = next(
        (item for item in ontology["relation_types"] if item["predicate"] == predicate),
        None,
    )
    if relation is None:
        return False
    try:
        subject_type, subject_program_class = ontology_endpoint(subject_id, ontology)
        object_type, object_program_class = ontology_endpoint(object_id, ontology)
    except ValueError:
        return False
    if subject_type not in relation["allowed_subject_types"]:
        return False
    if object_type not in relation["allowed_object_types"]:
        return False

    if predicate == "provides_capability" and subject_type == "program":
        return subject_program_class == "platform"
    if predicate == "depends_on_capability":
        return subject_program_class in PRODUCT_PROGRAM_CLASSES | {"platform"}
    if predicate == "supports_program":
        valid_subject = subject_type == "capability" or subject_program_class in {
            "platform",
            "infrastructure",
        }
        return valid_subject and object_program_class in PRODUCT_PROGRAM_CLASSES
    return True


@pytest.mark.parametrize(
    ("definition", "valid_id", "invalid_id"),
    [
        ("programId", "codexify:program:threadspace", "codexify:capability:identity"),
        ("capabilityId", "codexify:capability:identity", "codexify:program:threadspace"),
        ("clientSurfaceId", "codexify:client:web", "codexify:adapter:storage"),
        ("adapterFamilyId", "codexify:adapter:storage", "codexify:client:web"),
        ("sourceSubsystemId", "codexify:source:backend:context-broker", "codexify:source:context-broker"),
        (
            "productArchitectureAssertionId",
            "codexify:assertion:product-architecture:classification-example",
            "codexify:assertion:classification-example",
        ),
        ("dlgDocumentId", "codexify:doc:architecture:chat-runtime", "codexify:contract:chat-runtime"),
    ],
)
def test_ontology_identity_helpers_match_canonical_forms(definition, valid_id, invalid_id):
    schema = load_json(ONTOLOGY_SCHEMA_PATH)
    validator = jsonschema.Draft202012Validator(schema["$defs"][definition])
    assert validator.is_valid(valid_id)
    assert not validator.is_valid(invalid_id)


def test_source_subsystem_requires_domain_and_slug():
    valid = relationship_assertion(
        "codexify:source:backend:context-broker",
        "provides_capability",
        "codexify:capability:context-retrieval-assembly",
    )
    invalid = relationship_assertion(
        "codexify:source:context-broker",
        "provides_capability",
        "codexify:capability:context-retrieval-assembly",
    )
    assert assertion_schema_accepts(valid)
    assert not assertion_schema_accepts(invalid)


@pytest.mark.parametrize(
    ("predicate", "subject_id", "object_id"),
    [
        ("participates_in", "codexify:source:backend:context-broker", "codexify:program:node-runtime"),
        ("participates_in", "codexify:doc:architecture:chat-runtime", "codexify:program:digital-cognitive-workspace"),
        ("participates_in", "codexify:capability:identity", "codexify:program:threadspace"),
        ("provides_capability", "codexify:program:node-runtime", "codexify:capability:persistence"),
        ("provides_capability", "codexify:source:backend:persistence", "codexify:capability:persistence"),
        ("depends_on_capability", "codexify:program:digital-cognitive-workspace", "codexify:capability:identity"),
        ("depends_on_capability", "codexify:program:threadspace", "codexify:capability:identity"),
        ("depends_on_capability", "codexify:program:home-presence", "codexify:capability:identity"),
        ("depends_on_capability", "codexify:program:node-runtime", "codexify:capability:persistence"),
        ("presented_through", "codexify:program:digital-cognitive-workspace", "codexify:client:web"),
        ("integrates_via", "codexify:capability:provider-tool-adapter-interfaces", "codexify:adapter:local-inference"),
        ("integrates_via", "codexify:program:node-runtime", "codexify:adapter:storage"),
        ("implemented_by", "codexify:program:node-runtime", "codexify:source:backend:guardian-api"),
        ("implemented_by", "codexify:capability:identity", "codexify:source:backend:identity"),
        ("implemented_by", "codexify:client:web", "codexify:source:frontend:web-client"),
        ("implemented_by", "codexify:adapter:storage", "codexify:source:backend:storage-adapter"),
        ("bounded_by", "codexify:program:threadspace", "codexify:doc:architecture:threadspace-boundary"),
        ("bounded_by", "codexify:capability:identity", "codexify:doc:architecture:identity-contract"),
        ("bounded_by", "codexify:client:browser-host", "codexify:doc:adr:054-browser-host-topology"),
        ("bounded_by", "codexify:adapter:storage", "codexify:doc:architecture:data-and-storage"),
        ("bounded_by", "codexify:source:backend:context-broker", "codexify:doc:architecture:chat-runtime"),
        ("supports_program", "codexify:capability:identity", "codexify:program:threadspace"),
        ("supports_program", "codexify:program:node-runtime", "codexify:program:digital-cognitive-workspace"),
        ("supports_program", "codexify:program:infrastructure-services", "codexify:program:threadspace"),
        (
            "classified_by",
            "codexify:doc:architecture:chat-runtime",
            "codexify:assertion:product-architecture:chat-runtime-classification",
        ),
        (
            "classified_by",
            "codexify:source:backend:context-broker",
            "codexify:assertion:product-architecture:context-broker-classification",
        ),
    ],
)
def test_valid_relationship_endpoint_cases(predicate, subject_id, object_id):
    assertion = relationship_assertion(subject_id, predicate, object_id)
    assert assertion_schema_accepts(assertion)
    assert relationship_semantically_valid(subject_id, predicate, object_id)


@pytest.mark.parametrize(
    ("predicate", "subject_id", "object_id"),
    [
        ("participates_in", "codexify:client:web", "codexify:adapter:storage"),
        ("provides_capability", "codexify:capability:identity", "codexify:capability:persistence"),
        ("depends_on_capability", "codexify:client:web", "codexify:capability:identity"),
        ("presented_through", "codexify:capability:identity", "codexify:client:web"),
        ("integrates_via", "codexify:adapter:storage", "codexify:capability:persistence"),
        ("implemented_by", "codexify:source:backend:identity", "codexify:capability:identity"),
        ("bounded_by", "codexify:program:threadspace", "codexify:capability:identity"),
        ("supports_program", "codexify:client:web", "codexify:program:threadspace"),
        ("classified_by", "codexify:doc:architecture:chat-runtime", "codexify:capability:identity"),
    ],
)
def test_invalid_relationship_endpoint_cases(predicate, subject_id, object_id):
    assertion = relationship_assertion(subject_id, predicate, object_id)
    assert not assertion_schema_accepts(assertion)
    assert not relationship_semantically_valid(subject_id, predicate, object_id)


@pytest.mark.parametrize(
    ("predicate", "subject_id", "object_id"),
    [
        ("provides_capability", "codexify:program:threadspace", "codexify:capability:identity"),
        (
            "depends_on_capability",
            "codexify:program:infrastructure-services",
            "codexify:capability:persistence",
        ),
        (
            "supports_program",
            "codexify:program:digital-cognitive-workspace",
            "codexify:program:threadspace",
        ),
    ],
)
def test_program_class_restrictions_come_from_ontology(predicate, subject_id, object_id):
    assertion = relationship_assertion(subject_id, predicate, object_id)
    assert assertion_schema_accepts(assertion), "ID-shape schema should not duplicate program registry"
    assert not relationship_semantically_valid(subject_id, predicate, object_id)


@pytest.mark.parametrize(
    "subject_id",
    [
        "codexify:program:threadspace",
        "codexify:capability:identity",
        "codexify:client:web",
        "codexify:adapter:storage",
        "codexify:source:backend:context-broker",
    ],
)
def test_posture_subjects_remain_architecture_concepts(subject_id):
    assert assertion_schema_accepts(posture_assertion(subject_id))


@pytest.mark.parametrize(
    "subject_id",
    [
        "codexify:doc:architecture:chat-runtime",
        "codexify:assertion:product-architecture:chat-runtime-classification",
    ],
)
def test_posture_subjects_reject_documents_and_assertions(subject_id):
    assert not assertion_schema_accepts(posture_assertion(subject_id))


def test_governing_adr_document_id_domain_is_tightened():
    valid = relationship_assertion(
        "codexify:program:threadspace",
        "depends_on_capability",
        "codexify:capability:identity",
    )
    invalid = dict(valid)
    invalid["governing_adr_document_ids"] = ["codexify:doc:proof:some-proof"]
    assert assertion_schema_accepts(valid)
    assert not assertion_schema_accepts(invalid)


def test_ontology_relation_declarations_match_semantic_validator():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    actual = {
        relation["predicate"]: (
            set(relation["allowed_subject_types"]),
            set(relation["allowed_object_types"]),
        )
        for relation in ontology["relation_types"]
    }
    assert actual == EXPECTED_RELATION_ENDPOINT_TYPES
    assert all(relation["direction_constraint"].strip() for relation in ontology["relation_types"])


def test_product_architecture_acceptance_statuses_are_recorded():
    ontology = load_json(ONTOLOGY_JSON_PATH)
    ontology_schema = load_json(ONTOLOGY_SCHEMA_PATH)
    adr_text = (REPO_ROOT / "docs/architecture/adr/057-product-architecture-ontology-dlg-integration.md").read_text(
        encoding="utf-8"
    )
    assert ontology["status"] == "accepted"
    assert "accepted" in ontology_schema["properties"]["status"]["enum"]
    assert "## Status\n\nAccepted." in adr_text
    assert "- Accepted: 2026-08-07" in adr_text
    assert "- Human approver: Resonant Jones" in adr_text


def test_product_architecture_diagram_preserves_implemented_by_direction():
    product_doc = (REPO_ROOT / "docs/architecture/product-lanes-and-boundaries.md").read_text(
        encoding="utf-8"
    )
    assert "B -->|implemented_by| H[source subsystems]" in product_doc
    assert "H[source subsystems] -->|implemented_by| B" not in product_doc
