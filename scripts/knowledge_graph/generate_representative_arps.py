#!/usr/bin/env python3
"""Generate only the fixed DLG Phase 3B representative calibration scenarios.

This calibration-fixture generator accepts no arbitrary natural-language query,
performs no LLM call, performs no semantic search, and performs no runtime
retrieval.  It deterministically reconstructs four reviewed Agent Reading
Packet fixtures from the pinned Phase 3A graph and generated findings.  A
future general resolver and any runtime retrieval integration are separate
work.

Usage:
  python3 scripts/knowledge_graph/generate_representative_arps.py validate
  python3 scripts/knowledge_graph/generate_representative_arps.py generate \
    --created-at <RFC3339 timestamp>
  python3 scripts/knowledge_graph/generate_representative_arps.py check-generated \
    --created-at <RFC3339 timestamp>
"""

from __future__ import annotations

import argparse
import copy
import json
import os
import sys
import tempfile
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Mapping, Sequence

import jsonschema


SCRIPT_ID = "scripts/knowledge_graph/generate_representative_arps.py"
SCHEMA_VERSION = "1.0.0"
EXPECTED_REPOSITORY_REVISION = "1c51187427d843af88bc7fbd2dc7cea58c892fd3"
EXPECTED_GRAPH_REVISION = (
    "5fd8431fa3bac6cc9b2939bcdf24784562738404137bedb4b315c77706f30db3"
)
EXPECTED_RELATION_COUNTS = {
    "depends_on": 2,
    "evidence_for": 4,
    "governed_by": 2,
}

GRAPH_RELATIVE_PATH = Path("docs/knowledge-graph/generated/document-graph.json")
STALE_RELATIVE_PATH = Path("docs/knowledge-graph/generated/stale-documents.json")
SUPERSESSION_RELATIVE_PATH = Path(
    "docs/knowledge-graph/generated/supersession-map.json"
)
CONFLICT_RELATIVE_PATH = Path(
    "docs/knowledge-graph/generated/authority-conflicts.json"
)
SCHEMA_RELATIVE_PATH = Path(
    "schemas/knowledge/agent-reading-packet.schema.json"
)
OUTPUT_RELATIVE_DIR = Path(
    "docs/knowledge-graph/generated/agent-reading-packets"
)

CURRENT_STATE = "codexify:doc:architecture:current-state"
ADR_056 = "codexify:doc:adr:056-document-lifecycle-graph-control-plane"
ADR_057 = (
    "codexify:doc:adr:057-product-architecture-ontology-dlg-integration"
)
ADR_INDEX = "codexify:doc:architecture:adr-index"
DLG_CONTRACT = "codexify:doc:architecture:document-lifecycle-graph-contract"
KB_ENTRYPOINT = "codexify:doc:architecture:kb-entrypoint"
PRODUCT_LANES = "codexify:doc:architecture:product-lanes-and-boundaries"
AXIS_README = "codexify:doc:axis-node:readme"
PUBLICATION_PROOF = (
    "codexify:doc:proof:2026-08-07-dlg-pao-canonical-history-publication"
)

EXPECTED_DOCUMENT_IDS = frozenset(
    {
        ADR_056,
        ADR_057,
        ADR_INDEX,
        CURRENT_STATE,
        DLG_CONTRACT,
        KB_ENTRYPOINT,
        PRODUCT_LANES,
        AXIS_README,
        PUBLICATION_PROOF,
    }
)

OUTPUT_FILENAMES = (
    "representative-release-support.json",
    "representative-dlg-pao-architecture.json",
    "representative-dlg-pao-publication-history.json",
    "representative-dlg-runtime-retrieval-proof-gap.json",
)

NOTICE = (
    "Representative DLG Phase 3B calibration fixture; generated and "
    "reconstructable from the pinned Phase 3A graph. It is not a runtime "
    "retrieval receipt, not execution authorization, not architecture "
    "approval, and not proof beyond the selected sources' evidence boundaries."
)


def _path(*steps: tuple[str, str, str]) -> tuple[tuple[str, str, str], ...]:
    return steps


# Fixed, human-reviewed Phase 3B calibration fixtures.  These are not a full
# future resolver policy and are deliberately not configurable by question.
SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "filename": "representative-release-support.json",
        "packet_id": "codexify:arp:representative-release-support",
        "question_or_intent": (
            "What is currently supported in the Codexify release, and what "
            "remains explicitly unsupported or deferred?"
        ),
        "authority_profile": "release_and_support",
        "reading_budget": {
            "maximum_sources": 3,
            "maximum_hops": 0,
            "maximum_total_chunks": 12,
            "maximum_sections_per_source": 4,
        },
        "roots": (CURRENT_STATE,),
        "selected_order": (CURRENT_STATE,),
        "selections": {
            CURRENT_STATE: {
                "authority_scope": "present release promise",
                "selection_reason": (
                    "Required scoped release/support root. It states the current "
                    "release promise and explicit deferrals; it is neither "
                    "universal architecture authority nor live-runtime proof."
                ),
                "required_sections": (
                    "Current supported reality",
                    "Not yet true / do not assume",
                    "Active blockers",
                    "Release definition right now",
                ),
                "graph_path": _path(),
            }
        },
        "exclusion_reasons": {
            ADR_056: (
                "Accepted DLG architecture decision outside the bounded current "
                "release/support answer; its must_not_prove boundary excludes "
                "runtime behavior and release support."
            ),
            ADR_057: (
                "Accepted PAO architecture decision outside the bounded current "
                "release/support answer; it does not establish current support "
                "posture or release qualification."
            ),
            ADR_INDEX: (
                "Structural ADR discovery and routing only; it cannot establish "
                "release support independently of current-state authority."
            ),
            DLG_CONTRACT: (
                "Normative DLG contract not required for this scoped release "
                "question and explicitly not runtime, resolver, or release proof."
            ),
            KB_ENTRYPOINT: (
                "Structural architecture routing surface, not release-support "
                "authority or live-runtime proof."
            ),
            PRODUCT_LANES: (
                "Normative Product Architecture Ontology contract; its vocabulary "
                "does not prove current support, runtime participation, or release."
            ),
            AXIS_README: (
                "Structural Axis orientation surface, not release readiness or a "
                "parallel repository truth store."
            ),
            PUBLICATION_PROOF: (
                "Historical publication and validation evidence, not current "
                "release/support authority or current-head runtime proof."
            ),
        },
        "proof_gaps": (),
    },
    {
        "filename": "representative-dlg-pao-architecture.json",
        "packet_id": "codexify:arp:representative-dlg-pao-architecture",
        "question_or_intent": (
            "Which accepted documents govern the Document Lifecycle Graph and "
            "its Product Architecture Ontology extension, and what dependency "
            "chain connects them?"
        ),
        "authority_profile": "architecture_decision",
        "reading_budget": {
            "maximum_sources": 4,
            "maximum_hops": 2,
            "maximum_total_chunks": 28,
            "maximum_sections_per_source": 6,
        },
        "roots": (PRODUCT_LANES,),
        "selected_order": (ADR_056, ADR_057, DLG_CONTRACT, PRODUCT_LANES),
        "selections": {
            ADR_056: {
                "authority_scope": "Document Lifecycle Graph architecture and governance",
                "selection_reason": (
                    "Applicable accepted foundation ADR reached through the "
                    "reviewed Product Lanes -> ADR-057 -> ADR-056 dependency "
                    "chain; it governs DLG architecture but does not prove runtime "
                    "implementation."
                ),
                "required_sections": (
                    "Decision",
                    "Authority and truth boundary",
                    "Rollout posture",
                    "Non-goals",
                ),
                "graph_path": _path(
                    (PRODUCT_LANES, "governed_by", ADR_057),
                    (ADR_057, "depends_on", ADR_056),
                ),
            },
            ADR_057: {
                "authority_scope": "Product Architecture Ontology integration with the DLG",
                "selection_reason": (
                    "Applicable accepted PAO-extension ADR reached through the "
                    "reviewed Product Lanes governed_by edge; it follows ADR-056 "
                    "within the accepted dependency chain and grants no runtime proof."
                ),
                "required_sections": (
                    "Decision",
                    "Governing ADRs and alignment",
                    "Explicitly deferred work",
                    "Non-goals",
                ),
                "graph_path": _path(
                    (PRODUCT_LANES, "governed_by", ADR_057),
                ),
            },
            DLG_CONTRACT: {
                "authority_scope": "DLG relationship and graph invariants",
                "selection_reason": (
                    "Normative DLG contract reached through the reviewed Product "
                    "Lanes depends_on edge; it supplies graph doctrine below the "
                    "applicable accepted ADR tier and is not implementation proof."
                ),
                "required_sections": (
                    "Canonical token domains and orthogonal axes",
                    "Graph invariants",
                    "Staged corpus migration",
                ),
                "graph_path": _path(
                    (PRODUCT_LANES, "depends_on", DLG_CONTRACT),
                ),
            },
            PRODUCT_LANES: {
                "authority_scope": "product-architecture dependency and projection doctrine",
                "selection_reason": (
                    "Required normative root for the PAO extension and its reviewed "
                    "governance/dependency edges; it defines doctrine, not current "
                    "assertion context or runtime behavior."
                ),
                "required_sections": (
                    "Relationship to the DLG",
                    "Product Architecture relationship vocabulary",
                    "Allowed dependency directions",
                    "Non-goals",
                ),
                "graph_path": _path(),
            },
        },
        "exclusion_reasons": {
            ADR_INDEX: (
                "Structural ADR routing does not outrank or add decision authority "
                "to the selected accepted ADRs and normative contracts."
            ),
            CURRENT_STATE: (
                "Scoped release authority is not universal architecture-decision "
                "authority for this bounded DLG/PAO governance question."
            ),
            KB_ENTRYPOINT: (
                "Structural architecture orientation does not outrank the selected "
                "accepted ADRs and normative contracts."
            ),
            AXIS_README: (
                "Structural Axis orientation is outside the bounded DLG/PAO "
                "decision chain and grants no architecture approval."
            ),
            PUBLICATION_PROOF: (
                "Historical publication evidence is unnecessary for the bounded "
                "current architecture-decision question and remains evidence-only."
            ),
        },
        "proof_gaps": (),
    },
    {
        "filename": "representative-dlg-pao-publication-history.json",
        "packet_id": "codexify:arp:representative-dlg-pao-publication-history",
        "question_or_intent": (
            "What evidence records the canonical publication history of the DLG "
            "and PAO architecture artifacts?"
        ),
        "authority_profile": "historical_and_provenance",
        "reading_budget": {
            "maximum_sources": 5,
            "maximum_hops": 1,
            "maximum_total_chunks": 30,
            "maximum_sections_per_source": 6,
        },
        "roots": (PUBLICATION_PROOF,),
        "selected_order": (
            PUBLICATION_PROOF,
            ADR_056,
            ADR_057,
            DLG_CONTRACT,
            PRODUCT_LANES,
        ),
        "selections": {
            PUBLICATION_PROOF: {
                "authority_scope": (
                    "canonical Git ancestry of the recorded DLG and pre-acceptance PAO milestones"
                ),
                "selection_reason": (
                    "Required historical/provenance root. It records bounded "
                    "publication, ancestry, and validation evidence at its stated "
                    "revisions while remaining evidence-only."
                ),
                "required_sections": (
                    "Pre-reconciliation state",
                    "Reconciliation",
                    "Post-rebase milestone SHAs",
                    "Publication status",
                ),
                "graph_path": _path(),
            },
            ADR_056: {
                "authority_scope": "Document Lifecycle Graph architecture and governance",
                "selection_reason": (
                    "Current accepted DLG interpretation target of the proof's "
                    "direct reviewed evidence_for edge; the evidence edge does not "
                    "transfer architecture authority to the proof."
                ),
                "required_sections": ("Decision", "Authority and truth boundary"),
                "graph_path": _path(
                    (PUBLICATION_PROOF, "evidence_for", ADR_056),
                ),
            },
            ADR_057: {
                "authority_scope": "Product Architecture Ontology integration with the DLG",
                "selection_reason": (
                    "Current accepted PAO interpretation target of a direct "
                    "reviewed evidence_for edge; the proof is explicitly "
                    "pre-acceptance and does not independently prove later ADR-057 acceptance."
                ),
                "required_sections": ("Decision", "Governing ADRs and alignment"),
                "graph_path": _path(
                    (PUBLICATION_PROOF, "evidence_for", ADR_057),
                ),
            },
            DLG_CONTRACT: {
                "authority_scope": "Agent Reading Packet and staged migration doctrine",
                "selection_reason": (
                    "Current normative DLG interpretation target reached by the "
                    "proof's direct reviewed evidence_for edge; publication evidence "
                    "does not prove every substantive contract claim."
                ),
                "required_sections": ("Graph invariants", "Staged corpus migration"),
                "graph_path": _path(
                    (PUBLICATION_PROOF, "evidence_for", DLG_CONTRACT),
                ),
            },
            PRODUCT_LANES: {
                "authority_scope": "Product Architecture Ontology vocabulary",
                "selection_reason": (
                    "Current normative PAO interpretation target reached by the "
                    "proof's direct reviewed evidence_for edge; the historical proof "
                    "does not upgrade into current relationship or runtime authority."
                ),
                "required_sections": (
                    "Relationship to the DLG",
                    "Product Architecture Assertions",
                ),
                "graph_path": _path(
                    (PUBLICATION_PROOF, "evidence_for", PRODUCT_LANES),
                ),
            },
        },
        "exclusion_reasons": {
            ADR_INDEX: (
                "Structural ADR routing is unnecessary because the bounded proof "
                "has direct reviewed evidence_for paths to all interpretation targets."
            ),
            CURRENT_STATE: (
                "Current release/support authority is outside this dated publication-"
                "history question and is not required for provenance resolution."
            ),
            KB_ENTRYPOINT: (
                "Structural architecture routing is unnecessary for the bounded "
                "direct historical evidence traversal."
            ),
            AXIS_README: (
                "Structural Axis orientation is unrelated to the recorded DLG/PAO "
                "publication-history evidence chain."
            ),
        },
        "proof_gaps": (),
    },
    {
        "filename": "representative-dlg-runtime-retrieval-proof-gap.json",
        "packet_id": "codexify:arp:representative-dlg-runtime-retrieval-proof-gap",
        "question_or_intent": (
            "Is DLG runtime retrieval integration implemented and proven by the "
            "current calibration corpus?"
        ),
        "authority_profile": "implementation_behavior",
        "reading_budget": {
            "maximum_sources": 3,
            "maximum_hops": 0,
            "maximum_total_chunks": 16,
            "maximum_sections_per_source": 5,
        },
        "roots": (CURRENT_STATE, DLG_CONTRACT),
        "selected_order": (CURRENT_STATE, DLG_CONTRACT),
        "selections": {
            CURRENT_STATE: {
                "authority_scope": "present release promise",
                "selection_reason": (
                    "Required current-state root for the release boundary: DLG "
                    "automatic retrieval is not assumed or release-supported here. "
                    "This source is not code-path or live-runtime proof."
                ),
                "required_sections": (
                    "Current supported reality",
                    "Not yet true / do not assume",
                    "Release definition right now",
                ),
                "graph_path": _path(),
            },
            DLG_CONTRACT: {
                "authority_scope": "Agent Reading Packet and staged migration doctrine",
                "selection_reason": (
                    "Required accepted architecture root for the implemented-versus-"
                    "unimplemented and staged-retrieval boundary; a normative "
                    "contract is not implementation evidence."
                ),
                "required_sections": ("Graph invariants", "Staged corpus migration"),
                "graph_path": _path(),
            },
        },
        "exclusion_reasons": {
            ADR_056: (
                "Accepted DLG architecture-decision authority, not proven code-path "
                "or live-runtime evidence for retrieval implementation."
            ),
            ADR_057: (
                "Accepted PAO architecture-decision authority, not implementation "
                "evidence for DLG runtime retrieval."
            ),
            ADR_INDEX: (
                "Structural ADR routing cannot prove implementation or live behavior."
            ),
            KB_ENTRYPOINT: (
                "Structural architecture routing cannot establish DLG runtime "
                "retrieval implementation."
            ),
            PRODUCT_LANES: (
                "PAO architecture doctrine explicitly does not prove runtime DLG "
                "retrieval, current relationships, or integration."
            ),
            AXIS_README: (
                "Structural Axis orientation does not implement or prove automatic "
                "retrieval or a runtime harness."
            ),
            PUBLICATION_PROOF: (
                "Historical publication and validation evidence explicitly does not "
                "prove DLG runtime retrieval implementation or live behavior."
            ),
        },
        "proof_gaps": (
            {
                "authority_scope": "DLG runtime retrieval implementation behavior",
                "required_evidence_class": "proven-code-path",
                "reason": (
                    "No current code-path evidence represented in the nine-node "
                    "calibration graph proves DLG runtime retrieval integration."
                ),
            },
            {
                "authority_scope": "DLG runtime retrieval live behavior",
                "required_evidence_class": "proven-live-runtime",
                "reason": (
                    "No live-runtime evidence represented in the nine-node "
                    "calibration graph proves DLG retrieval integration is operating "
                    "in a supported runtime path."
                ),
            },
        ),
    },
)


class CalibrationError(RuntimeError):
    """Raised when the pinned calibration prerequisites or fixtures drift."""


@dataclass(frozen=True)
class Corpus:
    repository_root: Path
    graph: dict[str, Any]
    schema: dict[str, Any]
    nodes_by_id: Mapping[str, dict[str, Any]]
    accepted_edges: frozenset[tuple[str, str, str]]
    resolved_pointers: tuple[dict[str, Any], ...]
    supersession_chains: tuple[dict[str, Any], ...]
    conflicts: tuple[dict[str, Any], ...]
    stale_warnings: tuple[dict[str, Any], ...]
    unavailable_sources: tuple[dict[str, Any], ...]


def _fail(message: str) -> None:
    raise CalibrationError(message)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_bytes()
        text = raw.decode("utf-8")
        value = json.loads(text)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        _fail(f"cannot read required UTF-8 JSON {path}: {exc}")
    if not isinstance(value, dict):
        _fail(f"required JSON root must be an object: {path}")
    return value


def _validate_created_at(value: str) -> None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        _fail(f"created-at must be RFC3339: {exc}")
    if parsed.tzinfo is None:
        _fail("created-at must include an explicit UTC offset")


def _accepted_edges(graph: dict[str, Any]) -> frozenset[tuple[str, str, str]]:
    edges: set[tuple[str, str, str]] = set()
    for node in graph["nodes"]:
        for relation in node.get("relations", []):
            if (
                relation.get("canonicality") == "canonical"
                and relation.get("review_status") == "accepted"
            ):
                edges.add(
                    (
                        node["document_id"],
                        relation["relation_type"],
                        relation["target_document_id"],
                    )
                )
    return frozenset(edges)


def load_corpus(repository_root: Path | str) -> Corpus:
    """Load and verify only the pinned Phase 3A inputs used by these fixtures."""
    root = Path(repository_root).resolve()
    graph = _read_json_object(root / GRAPH_RELATIVE_PATH)
    stale_report = _read_json_object(root / STALE_RELATIVE_PATH)
    supersession_report = _read_json_object(root / SUPERSESSION_RELATIVE_PATH)
    conflict_report = _read_json_object(root / CONFLICT_RELATIVE_PATH)
    schema = _read_json_object(root / SCHEMA_RELATIVE_PATH)

    try:
        jsonschema.Draft202012Validator.check_schema(schema)
    except jsonschema.SchemaError as exc:
        _fail(f"ARP schema is not valid Draft 2020-12: {exc}")

    if graph.get("record_type") != "document_graph":
        _fail("document graph record_type changed; next-proof-needed")
    if graph.get("repository_revision") != EXPECTED_REPOSITORY_REVISION:
        _fail("document graph repository revision changed; next-proof-needed")
    if graph.get("graph_revision") != EXPECTED_GRAPH_REVISION:
        _fail("document graph revision changed; next-proof-needed")
    nodes = graph.get("nodes")
    if not isinstance(nodes, list) or len(nodes) != 9:
        _fail("calibration graph must contain exactly nine nodes; next-proof-needed")
    nodes_by_id = {
        node.get("document_id"): node for node in nodes if isinstance(node, dict)
    }
    if frozenset(nodes_by_id) != EXPECTED_DOCUMENT_IDS or len(nodes_by_id) != 9:
        _fail("calibration graph document identities changed; next-proof-needed")

    relations = [
        relation
        for node in nodes
        for relation in node.get("relations", [])
        if isinstance(relation, dict)
    ]
    counts = Counter(relation.get("relation_type") for relation in relations)
    if len(relations) != 8 or dict(sorted(counts.items())) != EXPECTED_RELATION_COUNTS:
        _fail("calibration graph relation corpus changed; next-proof-needed")
    if any(
        relation.get("canonicality") != "canonical"
        or relation.get("review_status") != "accepted"
        for relation in relations
    ):
        _fail("calibration graph contains a noncanonical or unaccepted edge")

    for name, report in (
        ("stale", stale_report),
        ("supersession", supersession_report),
        ("authority-conflict", conflict_report),
    ):
        if report.get("repository_revision") != EXPECTED_REPOSITORY_REVISION:
            _fail(f"{name} report repository revision changed; next-proof-needed")
        if report.get("graph_revision") != EXPECTED_GRAPH_REVISION:
            _fail(f"{name} report graph revision changed; next-proof-needed")

    stale_documents = stale_report.get("stale_documents")
    supersession_set = supersession_report.get("supersession_set")
    conflicts = conflict_report.get("conflicts")
    if not isinstance(stale_documents, list):
        _fail("stale report shape changed; next-proof-needed")
    if not isinstance(supersession_set, list):
        _fail("supersession report shape changed; next-proof-needed")
    if not isinstance(conflicts, list):
        _fail("authority-conflict report shape changed; next-proof-needed")
    if stale_documents:
        _fail("Phase 3A now reports stale documents; next-proof-needed")
    if supersession_set:
        _fail("Phase 3A now reports supersessions; next-proof-needed")
    if conflicts:
        _fail("Phase 3A now reports authority conflicts; next-proof-needed")

    pointer_edges = [
        edge for edge in _accepted_edges(graph) if edge[1] == "pointer_to"
    ]
    if pointer_edges:
        _fail("Phase 3A now reports compatibility pointers; next-proof-needed")

    return Corpus(
        repository_root=root,
        graph=graph,
        schema=schema,
        nodes_by_id=nodes_by_id,
        accepted_edges=_accepted_edges(graph),
        resolved_pointers=tuple(),
        supersession_chains=tuple(copy.deepcopy(supersession_set)),
        conflicts=tuple(copy.deepcopy(conflicts)),
        stale_warnings=tuple(copy.deepcopy(stale_documents)),
        unavailable_sources=tuple(),
    )


def _graph_path(value: Sequence[tuple[str, str, str]]) -> list[dict[str, str]]:
    return [
        {
            "from_document_id": source,
            "relation_type": relation_type,
            "to_document_id": target,
        }
        for source, relation_type, target in value
    ]


def _selected_source(
    corpus: Corpus,
    document_id: str,
    selection: Mapping[str, Any],
) -> dict[str, Any]:
    node = corpus.nodes_by_id[document_id]
    value: dict[str, Any] = {
        "document_id": document_id,
        "path": node["path"],
        "selection_reason": selection["selection_reason"],
        "authority_scope": selection["authority_scope"],
        "authority_class": node["authority_class"],
        "freshness_state": node["freshness"]["state"],
        "evidence_class": node["evidence_class"],
        "retrieval_priority": node["retrieval_policy"]["priority"],
        "graph_path": _graph_path(selection["graph_path"]),
    }
    required_sections = selection.get("required_sections", ())
    if required_sections:
        value["required_sections"] = list(required_sections)
    return value


def build_packets(corpus: Corpus, created_at: str) -> dict[str, dict[str, Any]]:
    """Construct the four fixed representative packets entirely in memory."""
    _validate_created_at(created_at)
    packets: dict[str, dict[str, Any]] = {}
    ordered_node_ids = sorted(corpus.nodes_by_id)
    for scenario in SCENARIOS:
        selected_ids = scenario["selected_order"]
        selected_set = set(selected_ids)
        exclusion_reasons = scenario["exclusion_reasons"]
        expected_excluded = EXPECTED_DOCUMENT_IDS - selected_set
        if set(exclusion_reasons) != expected_excluded:
            _fail(f"scenario exclusion specification drifted: {scenario['packet_id']}")
        packet = {
            "schema_version": SCHEMA_VERSION,
            "packet_id": scenario["packet_id"],
            "created_at": created_at,
            "repository_revision": corpus.graph["repository_revision"],
            "graph_revision": corpus.graph["graph_revision"],
            "question_or_intent": scenario["question_or_intent"],
            "authority_profile": scenario["authority_profile"],
            "reading_budget": copy.deepcopy(scenario["reading_budget"]),
            "selected_sources": [
                _selected_source(
                    corpus,
                    document_id,
                    scenario["selections"][document_id],
                )
                for document_id in selected_ids
            ],
            "resolved_pointers": [copy.deepcopy(item) for item in corpus.resolved_pointers],
            "supersession_chains": [
                copy.deepcopy(item) for item in corpus.supersession_chains
            ],
            "excluded_sources": [
                {
                    "document_id": document_id,
                    "exclusion_reason": exclusion_reasons[document_id],
                }
                for document_id in ordered_node_ids
                if document_id not in selected_set
            ],
            "conflicts": [copy.deepcopy(item) for item in corpus.conflicts],
            "stale_warnings": [
                copy.deepcopy(item) for item in corpus.stale_warnings
            ],
            "proof_gaps": [copy.deepcopy(item) for item in scenario["proof_gaps"]],
            "unavailable_sources": [
                copy.deepcopy(item) for item in corpus.unavailable_sources
            ],
            "human_decisions_required": [],
            "illustrative": True,
            "notice": NOTICE,
        }
        packets[scenario["filename"]] = packet
    validate_packets(corpus, packets)
    return packets


def _scenario_by_filename() -> dict[str, dict[str, Any]]:
    return {scenario["filename"]: scenario for scenario in SCENARIOS}


def _validate_notice(packet: Mapping[str, Any]) -> None:
    notice = str(packet.get("notice", "")).lower()
    required = (
        "representative dlg phase 3b calibration fixture",
        "generated and reconstructable",
        "not a runtime retrieval receipt",
        "not execution authorization",
        "not architecture approval",
        "not proof beyond",
    )
    if not all(fragment in notice for fragment in required):
        _fail(f"packet notice is missing required boundary language: {packet.get('packet_id')}")


def _validate_path(
    corpus: Corpus,
    scenario: Mapping[str, Any],
    source: Mapping[str, Any],
) -> None:
    document_id = source["document_id"]
    path = source["graph_path"]
    roots = set(scenario["roots"])
    maximum_hops = scenario["reading_budget"]["maximum_hops"]
    if document_id in roots:
        if path:
            _fail(f"root source has a non-empty graph path: {document_id}")
        return
    if not path:
        _fail(f"non-root source has an empty graph path: {document_id}")
    if len(path) > maximum_hops:
        _fail(f"source graph path exceeds hop budget: {document_id}")
    if path[0]["from_document_id"] not in roots:
        _fail(f"source graph path does not begin at a declared root: {document_id}")
    if path[-1]["to_document_id"] != document_id:
        _fail(f"source graph path does not end at selected source: {document_id}")
    for index, step in enumerate(path):
        edge = (
            step["from_document_id"],
            step["relation_type"],
            step["to_document_id"],
        )
        if edge not in corpus.accepted_edges:
            _fail(f"source graph path invents or reverses an edge: {edge}")
        if index and path[index - 1]["to_document_id"] != step["from_document_id"]:
            _fail(f"source graph path is discontinuous: {document_id}")


def validate_packet(
    corpus: Corpus,
    scenario: Mapping[str, Any],
    packet: dict[str, Any],
) -> None:
    """Validate schema and semantic calibration rules for one packet."""
    validator = jsonschema.Draft202012Validator(
        corpus.schema,
        format_checker=jsonschema.FormatChecker(),
    )
    errors = sorted(
        validator.iter_errors(packet),
        key=lambda error: (list(error.absolute_path), error.message),
    )
    if errors:
        detail = "; ".join(error.message for error in errors)
        _fail(f"ARP schema validation failed for {scenario['packet_id']}: {detail}")

    fixed_fields = (
        "packet_id",
        "question_or_intent",
        "authority_profile",
        "reading_budget",
    )
    for field in fixed_fields:
        if packet.get(field) != scenario[field]:
            _fail(f"fixed scenario field drifted: {scenario['packet_id']} {field}")
    if packet.get("schema_version") != SCHEMA_VERSION:
        _fail(f"schema version drifted: {scenario['packet_id']}")
    if packet.get("repository_revision") != EXPECTED_REPOSITORY_REVISION:
        _fail(f"repository revision binding drifted: {scenario['packet_id']}")
    if packet.get("graph_revision") != EXPECTED_GRAPH_REVISION:
        _fail(f"graph revision binding drifted: {scenario['packet_id']}")
    if packet.get("illustrative") is not True:
        _fail(f"packet must remain illustrative: {scenario['packet_id']}")
    if "architecture_context" in packet:
        _fail(f"architecture_context is prohibited for Phase 3B: {scenario['packet_id']}")
    _validate_notice(packet)

    selected = packet["selected_sources"]
    excluded = packet["excluded_sources"]
    selected_ids = [source["document_id"] for source in selected]
    excluded_ids = [source["document_id"] for source in excluded]
    if selected_ids != list(scenario["selected_order"]):
        _fail(f"selected source order drifted: {scenario['packet_id']}")
    if len(selected_ids) != len(set(selected_ids)):
        _fail(f"duplicate selected source: {scenario['packet_id']}")
    if len(excluded_ids) != len(set(excluded_ids)):
        _fail(f"duplicate excluded source: {scenario['packet_id']}")
    if set(selected_ids) & set(excluded_ids):
        _fail(f"source selected and excluded: {scenario['packet_id']}")
    if set(selected_ids) | set(excluded_ids) != EXPECTED_DOCUMENT_IDS:
        _fail(f"packet does not account for all nine nodes: {scenario['packet_id']}")
    if len(selected) > packet["reading_budget"]["maximum_sources"]:
        _fail(f"selected source budget exceeded: {scenario['packet_id']}")

    expected_exclusions = scenario["exclusion_reasons"]
    for exclusion in excluded:
        if exclusion["exclusion_reason"] != expected_exclusions[exclusion["document_id"]]:
            _fail(f"exclusion reason drifted: {exclusion['document_id']}")

    roots = set(scenario["roots"])
    if not roots <= set(selected_ids):
        _fail(f"declared root is not selected: {scenario['packet_id']}")
    for source in selected:
        document_id = source["document_id"]
        node = corpus.nodes_by_id[document_id]
        selection = scenario["selections"][document_id]
        exact_metadata = {
            "path": node["path"],
            "authority_class": node["authority_class"],
            "freshness_state": node["freshness"]["state"],
            "evidence_class": node["evidence_class"],
            "retrieval_priority": node["retrieval_policy"]["priority"],
        }
        for field, expected in exact_metadata.items():
            if source.get(field) != expected:
                _fail(f"selected metadata drifted: {document_id} {field}")
        if source.get("authority_scope") != selection["authority_scope"]:
            _fail(f"selected authority scope drifted: {document_id}")
        if source["authority_scope"] not in node["authority_scopes"]:
            _fail(f"selected authority scope is not canonical: {document_id}")
        if source.get("selection_reason") != selection["selection_reason"]:
            _fail(f"selection reason drifted: {document_id}")
        required_sections = source.get("required_sections", [])
        canonical_sections = node["retrieval_policy"].get("section_hints", [])
        if not set(required_sections) <= set(canonical_sections):
            _fail(f"selected section hint is not canonical: {document_id}")
        if len(required_sections) > packet["reading_budget"]["maximum_sections_per_source"]:
            _fail(f"selected section budget exceeded: {document_id}")
        if node["lifecycle_state"] in {"retired", "tombstoned"}:
            _fail(f"retired/tombstoned source selected: {document_id}")
        if node["disposition"] in {"superseded", "quarantined"}:
            _fail(f"superseded/quarantined source selected: {document_id}")
        _validate_path(corpus, scenario, source)

    stale_selected = {
        source["document_id"]
        for source in selected
        if source["freshness_state"] == "stale"
    }
    warning_ids = {warning["document_id"] for warning in packet["stale_warnings"]}
    if stale_selected != warning_ids:
        _fail(f"stale-warning coverage drifted: {scenario['packet_id']}")
    if packet["resolved_pointers"] != list(corpus.resolved_pointers):
        _fail(f"pointer findings drifted: {scenario['packet_id']}")
    if packet["supersession_chains"] != list(corpus.supersession_chains):
        _fail(f"supersession findings drifted: {scenario['packet_id']}")
    if packet["conflicts"] != list(corpus.conflicts):
        _fail(f"conflict findings drifted: {scenario['packet_id']}")
    if packet["stale_warnings"] != list(corpus.stale_warnings):
        _fail(f"stale findings drifted: {scenario['packet_id']}")
    if packet["unavailable_sources"] != list(corpus.unavailable_sources):
        _fail(f"unavailable-source findings drifted: {scenario['packet_id']}")
    if packet["proof_gaps"] != list(scenario["proof_gaps"]):
        _fail(f"proof gaps drifted: {scenario['packet_id']}")
    if packet["human_decisions_required"] != []:
        _fail(f"unexpected human decision: {scenario['packet_id']}")


def validate_packets(
    corpus: Corpus,
    packets: Mapping[str, dict[str, Any]],
) -> None:
    """Validate exact four-file identity plus every packet semantic rule."""
    if len(SCENARIOS) != 4 or len(OUTPUT_FILENAMES) != 4:
        _fail("Phase 3B must expose exactly four fixed scenarios")
    if tuple(scenario["filename"] for scenario in SCENARIOS) != OUTPUT_FILENAMES:
        _fail("scenario/output filename registry drifted")
    if set(packets) != set(OUTPUT_FILENAMES) or len(packets) != 4:
        _fail("exactly four representative packet payloads are required")
    packet_ids = [packet["packet_id"] for packet in packets.values()]
    if len(packet_ids) != len(set(packet_ids)):
        _fail("representative packet IDs must be unique")
    scenarios = _scenario_by_filename()
    for filename in OUTPUT_FILENAMES:
        validate_packet(corpus, scenarios[filename], packets[filename])


def _pretty_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2).encode("utf-8")
        + b"\n"
    )


def atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    """Write deterministic UTF-8 JSON through same-directory atomic replacement."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_pretty_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_path, path)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise


def _assert_output_scope(output_dir: Path, *, allow_missing: bool) -> None:
    if not output_dir.exists():
        if allow_missing:
            return
        _fail(f"representative packet output directory is missing: {output_dir}")
    if not output_dir.is_dir():
        _fail(f"representative packet output path is not a directory: {output_dir}")
    entries = sorted(path.name for path in output_dir.iterdir())
    if set(entries) - set(OUTPUT_FILENAMES):
        _fail(f"unknown representative packet output exists: {entries}")


def write_packets(
    output_dir: Path | str,
    packets: Mapping[str, dict[str, Any]],
) -> None:
    """Atomically write exactly the four fixed representative packets."""
    target = Path(output_dir)
    _assert_output_scope(target, allow_missing=True)
    for filename in OUTPUT_FILENAMES:
        atomic_write_json(target / filename, packets[filename])


def load_persisted_packets(output_dir: Path | str) -> dict[str, dict[str, Any]]:
    target = Path(output_dir)
    _assert_output_scope(target, allow_missing=False)
    entries = sorted(path.name for path in target.iterdir() if path.is_file())
    if entries != sorted(OUTPUT_FILENAMES):
        _fail("persisted representative output must contain exactly four JSON files")
    return {
        filename: _read_json_object(target / filename)
        for filename in OUTPUT_FILENAMES
    }


def _summary(packets: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    return {
        "tool": SCRIPT_ID,
        "result": "pass",
        "packets_valid": f"{len(packets)}/4",
        "corpus_accounting_valid": f"{len(packets)}/4",
        "packet_ids": [packets[name]["packet_id"] for name in OUTPUT_FILENAMES],
        "total_selected_source_occurrences": sum(
            len(packet["selected_sources"]) for packet in packets.values()
        ),
        "total_proof_gaps": sum(len(packet["proof_gaps"]) for packet in packets.values()),
        "total_stale_warnings": sum(
            len(packet["stale_warnings"]) for packet in packets.values()
        ),
        "total_conflicts": sum(len(packet["conflicts"]) for packet in packets.values()),
        "architecture_context_count": sum(
            "architecture_context" in packet for packet in packets.values()
        ),
        "arbitrary_query_support": "none",
        "graph_revision": EXPECTED_GRAPH_REVISION,
        "repository_revision": EXPECTED_REPOSITORY_REVISION,
    }


def generate(
    repository_root: Path | str,
    created_at: str,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    corpus = load_corpus(repository_root)
    packets = build_packets(corpus, created_at)
    target = (
        Path(output_dir)
        if output_dir is not None
        else corpus.repository_root / OUTPUT_RELATIVE_DIR
    )
    write_packets(target, packets)
    return packets


def validate(
    repository_root: Path | str,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    corpus = load_corpus(repository_root)
    target = (
        Path(output_dir)
        if output_dir is not None
        else corpus.repository_root / OUTPUT_RELATIVE_DIR
    )
    packets = load_persisted_packets(target)
    validate_packets(corpus, packets)
    return packets


def check_generated(
    repository_root: Path | str,
    created_at: str,
    *,
    output_dir: Path | str | None = None,
) -> dict[str, dict[str, Any]]:
    """Regenerate into a temporary directory and byte-compare all four files."""
    corpus = load_corpus(repository_root)
    target = (
        Path(output_dir)
        if output_dir is not None
        else corpus.repository_root / OUTPUT_RELATIVE_DIR
    )
    persisted = load_persisted_packets(target)
    validate_packets(corpus, persisted)
    regenerated = build_packets(corpus, created_at)
    drifted: list[str] = []
    with tempfile.TemporaryDirectory(prefix="codexify-dlg-phase3b-repro-") as name:
        temporary_dir = Path(name)
        write_packets(temporary_dir, regenerated)
        for filename in OUTPUT_FILENAMES:
            if (temporary_dir / filename).read_bytes() != (target / filename).read_bytes():
                drifted.append(filename)
    if drifted:
        _fail("generated packet drift: " + ", ".join(drifted))
    return persisted


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Generate and validate four fixed representative DLG Phase 3B "
            "calibration packets."
        )
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    for command in ("validate", "generate", "check-generated"):
        subparser = subparsers.add_parser(command)
        subparser.add_argument(
            "--repository-root",
            default=str(Path(__file__).resolve().parents[2]),
            help="Repository root containing the pinned Phase 3A inputs.",
        )
        if command != "validate":
            subparser.add_argument("--created-at", required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "generate":
            packets = generate(args.repository_root, args.created_at)
        elif args.command == "check-generated":
            packets = check_generated(args.repository_root, args.created_at)
        else:
            packets = validate(args.repository_root)
    except CalibrationError as exc:
        print(f"DLG Phase 3B next-proof-needed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(_summary(packets), ensure_ascii=False, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
