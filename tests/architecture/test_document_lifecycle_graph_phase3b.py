"""Golden calibration coverage for representative DLG Phase 3B ARPs.

These tests exercise fixed, illustrative source-selection fixtures only.  They
do not implement an arbitrary resolver, perform retrieval, start runtime
services, populate PAO context, or widen release claims.
"""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
from datetime import datetime as real_datetime
from pathlib import Path

import jsonschema
import pytest

from scripts.knowledge_graph import generate_representative_arps as arps


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/knowledge_graph/generate_representative_arps.py"
OUTPUT_DIR = REPO_ROOT / arps.OUTPUT_RELATIVE_DIR
CREATED_AT = "2026-08-08T14:27:29-04:00"
PHASE3A_SHA = "236798baaa3dd1f355232a85fd2f72d0c3715bd1"


@pytest.fixture(scope="module")
def corpus() -> arps.Corpus:
    return arps.load_corpus(REPO_ROOT)


@pytest.fixture(scope="module")
def packets(corpus: arps.Corpus) -> dict[str, dict]:
    value = arps.load_persisted_packets(OUTPUT_DIR)
    arps.validate_packets(corpus, value)
    return value


def scenario(filename: str) -> dict:
    return next(item for item in arps.SCENARIOS if item["filename"] == filename)


def selected_ids(packet: dict) -> list[str]:
    return [source["document_id"] for source in packet["selected_sources"]]


def excluded_ids(packet: dict) -> set[str]:
    return {source["document_id"] for source in packet["excluded_sources"]}


def packet(filename: str, packets: dict[str, dict]) -> dict:
    return packets[filename]


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(REPO_ROOT), *args],
        capture_output=True,
        check=False,
        text=True,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return completed.stdout.strip()


def test_arp_schema_is_valid_draft_2020_12(corpus: arps.Corpus) -> None:
    jsonschema.Draft202012Validator.check_schema(corpus.schema)


def test_exactly_four_fixed_scenarios_and_output_paths_exist() -> None:
    assert len(arps.SCENARIOS) == 4
    assert len(arps.OUTPUT_FILENAMES) == 4
    assert tuple(item["filename"] for item in arps.SCENARIOS) == arps.OUTPUT_FILENAMES
    assert sorted(path.name for path in OUTPUT_DIR.iterdir()) == sorted(arps.OUTPUT_FILENAMES)


def test_four_packet_ids_are_unique_and_fixed(packets: dict[str, dict]) -> None:
    packet_ids = [packets[name]["packet_id"] for name in arps.OUTPUT_FILENAMES]
    assert len(packet_ids) == len(set(packet_ids)) == 4
    assert packet_ids == [item["packet_id"] for item in arps.SCENARIOS]


@pytest.mark.parametrize("filename", arps.OUTPUT_FILENAMES)
def test_each_packet_validates_with_format_checking(
    filename: str,
    corpus: arps.Corpus,
    packets: dict[str, dict],
) -> None:
    validator = jsonschema.Draft202012Validator(
        corpus.schema,
        format_checker=jsonschema.FormatChecker(),
    )
    validator.validate(packets[filename])


@pytest.mark.parametrize("filename", arps.OUTPUT_FILENAMES)
def test_each_packet_is_bound_to_pinned_graph_and_is_illustrative(
    filename: str,
    packets: dict[str, dict],
) -> None:
    value = packets[filename]
    assert value["graph_revision"] == arps.EXPECTED_GRAPH_REVISION
    assert value["repository_revision"] == arps.EXPECTED_REPOSITORY_REVISION
    assert value["illustrative"] is True
    assert "architecture_context" not in value


@pytest.mark.parametrize("filename", arps.OUTPUT_FILENAMES)
def test_each_packet_accounts_for_all_nine_nodes_exactly_once(
    filename: str,
    packets: dict[str, dict],
) -> None:
    value = packets[filename]
    selected = selected_ids(value)
    excluded = [item["document_id"] for item in value["excluded_sources"]]
    assert set(selected) | set(excluded) == arps.EXPECTED_DOCUMENT_IDS
    assert set(selected).isdisjoint(excluded)
    assert len(selected) == len(set(selected))
    assert len(excluded) == len(set(excluded))


def test_selected_metadata_and_authority_scopes_match_canonical_nodes(
    corpus: arps.Corpus,
    packets: dict[str, dict],
) -> None:
    for value in packets.values():
        for source in value["selected_sources"]:
            node = corpus.nodes_by_id[source["document_id"]]
            assert source["path"] == node["path"]
            assert source["authority_class"] == node["authority_class"]
            assert source["freshness_state"] == node["freshness"]["state"]
            assert source["evidence_class"] == node["evidence_class"]
            assert source["retrieval_priority"] == node["retrieval_policy"]["priority"]
            assert source["authority_scope"] in node["authority_scopes"]
            assert set(source.get("required_sections", [])) <= set(
                node["retrieval_policy"].get("section_hints", [])
            )


def test_graph_paths_use_only_forward_accepted_canonical_relations(
    corpus: arps.Corpus,
    packets: dict[str, dict],
) -> None:
    used_edges = set()
    for value in packets.values():
        for source in value["selected_sources"]:
            for step in source["graph_path"]:
                edge = (
                    step["from_document_id"],
                    step["relation_type"],
                    step["to_document_id"],
                )
                used_edges.add(edge)
                assert edge in corpus.accepted_edges
                assert (edge[2], edge[1], edge[0]) not in used_edges - {edge}
    assert used_edges


def test_declared_roots_are_selected_with_empty_paths_and_nonroots_are_connected(
    packets: dict[str, dict],
) -> None:
    for item in arps.SCENARIOS:
        value = packets[item["filename"]]
        by_id = {source["document_id"]: source for source in value["selected_sources"]}
        for root in item["roots"]:
            assert by_id[root]["graph_path"] == []
        for document_id, source in by_id.items():
            if document_id not in item["roots"]:
                assert source["graph_path"]
                assert source["graph_path"][0]["from_document_id"] in item["roots"]
                assert source["graph_path"][-1]["to_document_id"] == document_id


def test_all_reading_budgets_are_respected(packets: dict[str, dict]) -> None:
    for value in packets.values():
        budget = value["reading_budget"]
        assert len(value["selected_sources"]) <= budget["maximum_sources"]
        for source in value["selected_sources"]:
            assert len(source["graph_path"]) <= budget["maximum_hops"]
            assert len(source.get("required_sections", [])) <= budget[
                "maximum_sections_per_source"
            ]
        assert budget["maximum_total_chunks"] > 0


def test_no_selected_source_is_stale_retired_tombstoned_superseded_or_quarantined(
    corpus: arps.Corpus,
    packets: dict[str, dict],
) -> None:
    for value in packets.values():
        assert value["stale_warnings"] == []
        for source in value["selected_sources"]:
            node = corpus.nodes_by_id[source["document_id"]]
            assert node["freshness"]["state"] != "stale"
            assert node["lifecycle_state"] not in {"retired", "tombstoned"}
            assert node["disposition"] not in {"superseded", "quarantined"}


def test_release_packet_selects_current_state_only_and_excludes_every_other_class(
    packets: dict[str, dict],
) -> None:
    value = packet("representative-release-support.json", packets)
    assert selected_ids(value) == [arps.CURRENT_STATE]
    assert excluded_ids(value) == arps.EXPECTED_DOCUMENT_IDS - {arps.CURRENT_STATE}
    assert {arps.ADR_056, arps.ADR_057, arps.DLG_CONTRACT, arps.PRODUCT_LANES} <= excluded_ids(value)
    assert {arps.PUBLICATION_PROOF, arps.ADR_INDEX, arps.KB_ENTRYPOINT, arps.AXIS_README} <= excluded_ids(value)
    assert value["proof_gaps"] == []


def test_release_packet_preserves_scoped_authority_and_runtime_boundary(
    packets: dict[str, dict],
) -> None:
    source = packet("representative-release-support.json", packets)["selected_sources"][0]
    reason = source["selection_reason"].lower()
    assert source["authority_scope"] == "present release promise"
    assert "universal architecture authority" in reason
    assert "live-runtime proof" in reason


def test_architecture_packet_exact_order_and_exclusions(packets: dict[str, dict]) -> None:
    value = packet("representative-dlg-pao-architecture.json", packets)
    assert selected_ids(value) == [
        arps.ADR_056,
        arps.ADR_057,
        arps.DLG_CONTRACT,
        arps.PRODUCT_LANES,
    ]
    assert arps.PUBLICATION_PROOF not in selected_ids(value)
    assert excluded_ids(value) == {
        arps.ADR_INDEX,
        arps.CURRENT_STATE,
        arps.KB_ENTRYPOINT,
        arps.AXIS_README,
        arps.PUBLICATION_PROOF,
    }


def test_architecture_packet_exact_reviewed_paths(packets: dict[str, dict]) -> None:
    value = packet("representative-dlg-pao-architecture.json", packets)
    by_id = {source["document_id"]: source for source in value["selected_sources"]}
    assert by_id[arps.PRODUCT_LANES]["graph_path"] == []
    assert by_id[arps.ADR_057]["graph_path"] == [
        {
            "from_document_id": arps.PRODUCT_LANES,
            "relation_type": "governed_by",
            "to_document_id": arps.ADR_057,
        }
    ]
    assert by_id[arps.DLG_CONTRACT]["graph_path"] == [
        {
            "from_document_id": arps.PRODUCT_LANES,
            "relation_type": "depends_on",
            "to_document_id": arps.DLG_CONTRACT,
        }
    ]
    assert by_id[arps.ADR_056]["graph_path"] == [
        {
            "from_document_id": arps.PRODUCT_LANES,
            "relation_type": "governed_by",
            "to_document_id": arps.ADR_057,
        },
        {
            "from_document_id": arps.ADR_057,
            "relation_type": "depends_on",
            "to_document_id": arps.ADR_056,
        },
    ]


def test_architecture_packet_has_no_pao_assertion_context(packets: dict[str, dict]) -> None:
    value = packet("representative-dlg-pao-architecture.json", packets)
    assert "architecture_context" not in value
    assert value["proof_gaps"] == []
    assert value["conflicts"] == []
    assert value["stale_warnings"] == []


def test_history_packet_selects_proof_then_four_direct_targets(packets: dict[str, dict]) -> None:
    value = packet("representative-dlg-pao-publication-history.json", packets)
    assert selected_ids(value) == [
        arps.PUBLICATION_PROOF,
        arps.ADR_056,
        arps.ADR_057,
        arps.DLG_CONTRACT,
        arps.PRODUCT_LANES,
    ]
    assert len(value["excluded_sources"]) == 4
    assert value["proof_gaps"] == []


def test_history_packet_uses_only_direct_evidence_for_paths(packets: dict[str, dict]) -> None:
    value = packet("representative-dlg-pao-publication-history.json", packets)
    for source in value["selected_sources"]:
        if source["document_id"] == arps.PUBLICATION_PROOF:
            assert source["graph_path"] == []
            continue
        assert source["graph_path"] == [
            {
                "from_document_id": arps.PUBLICATION_PROOF,
                "relation_type": "evidence_for",
                "to_document_id": source["document_id"],
            }
        ]


def test_history_proof_remains_evidence_only_and_preacceptance_bounded(
    packets: dict[str, dict],
) -> None:
    value = packet("representative-dlg-pao-publication-history.json", packets)
    proof = value["selected_sources"][0]
    adr_057 = value["selected_sources"][2]
    assert proof["authority_class"] == "evidence_only"
    assert proof["evidence_class"] == "proven-test"
    assert "remaining evidence-only" in proof["selection_reason"]
    assert "does not independently prove later adr-057 acceptance" in adr_057[
        "selection_reason"
    ].lower()
    assert all("runtime behavior is proven" not in source["selection_reason"].lower() for source in value["selected_sources"])


def test_implementation_packet_selects_two_roots_and_exactly_two_proof_gaps(
    packets: dict[str, dict],
) -> None:
    value = packet("representative-dlg-runtime-retrieval-proof-gap.json", packets)
    assert selected_ids(value) == [arps.CURRENT_STATE, arps.DLG_CONTRACT]
    assert all(source["graph_path"] == [] for source in value["selected_sources"])
    assert len(value["proof_gaps"]) == 2
    assert {gap["required_evidence_class"] for gap in value["proof_gaps"]} == {
        "proven-code-path",
        "proven-live-runtime",
    }


def test_implementation_packet_reports_missing_evidence_without_unavailable_ids(
    packets: dict[str, dict],
) -> None:
    value = packet("representative-dlg-runtime-retrieval-proof-gap.json", packets)
    assert value["unavailable_sources"] == []
    assert value["conflicts"] == []
    assert value["stale_warnings"] == []
    assert value["human_decisions_required"] == []
    assert {gap["authority_scope"] for gap in value["proof_gaps"]} == {
        "DLG runtime retrieval implementation behavior",
        "DLG runtime retrieval live behavior",
    }


def test_implementation_packet_excludes_publication_and_decision_docs_as_runtime_proof(
    packets: dict[str, dict],
) -> None:
    value = packet("representative-dlg-runtime-retrieval-proof-gap.json", packets)
    exclusions = {
        item["document_id"]: item["exclusion_reason"].lower()
        for item in value["excluded_sources"]
    }
    assert "does not prove dlg runtime retrieval" in exclusions[arps.PUBLICATION_PROOF]
    assert "not proven code-path" in exclusions[arps.ADR_056]
    assert "not implementation evidence" in exclusions[arps.ADR_057]
    assert "does not prove runtime dlg retrieval" in exclusions[arps.PRODUCT_LANES]


def test_notices_disclaim_runtime_authority_and_proof_boundaries(
    packets: dict[str, dict],
) -> None:
    for value in packets.values():
        notice = value["notice"].lower()
        assert "representative dlg phase 3b calibration fixture" in notice
        assert "generated and reconstructable" in notice
        assert "not a runtime retrieval receipt" in notice
        assert "not execution authorization" in notice
        assert "not architecture approval" in notice
        assert "not proof beyond" in notice


def test_no_packet_contains_authority_score_or_unexpected_architecture_context(
    packets: dict[str, dict],
) -> None:
    for value in packets.values():
        serialized = json.dumps(value, sort_keys=True).lower()
        assert "authority_score" not in serialized
        assert "llm-generated authority score" not in serialized
        assert "architecture_context" not in value


def test_phase3a_findings_are_read_and_currently_empty(corpus: arps.Corpus) -> None:
    assert arps.STALE_RELATIVE_PATH.name == "stale-documents.json"
    assert arps.SUPERSESSION_RELATIVE_PATH.name == "supersession-map.json"
    assert arps.CONFLICT_RELATIVE_PATH.name == "authority-conflicts.json"
    assert corpus.stale_warnings == ()
    assert corpus.supersession_chains == ()
    assert corpus.conflicts == ()
    assert corpus.resolved_pointers == ()


def test_output_bytes_are_deterministic_for_fixed_created_at(corpus: arps.Corpus) -> None:
    first = arps.build_packets(corpus, CREATED_AT)
    second = arps.build_packets(corpus, CREATED_AT)
    for filename in arps.OUTPUT_FILENAMES:
        assert arps._pretty_json_bytes(first[filename]) == arps._pretty_json_bytes(
            second[filename]
        )


def test_check_generated_passes_for_all_four_packets(packets: dict[str, dict]) -> None:
    checked = arps.check_generated(REPO_ROOT, CREATED_AT)
    assert checked == packets


def test_changing_created_at_changes_bytes_but_not_graph_revision(corpus: arps.Corpus) -> None:
    first = arps.build_packets(corpus, CREATED_AT)
    second = arps.build_packets(corpus, "2026-08-08T18:27:29Z")
    for filename in arps.OUTPUT_FILENAMES:
        assert arps._pretty_json_bytes(first[filename]) != arps._pretty_json_bytes(
            second[filename]
        )
        assert first[filename]["graph_revision"] == second[filename]["graph_revision"]


def test_process_wall_clock_is_not_consulted_for_fixed_created_at(
    corpus: arps.Corpus,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    before = arps.build_packets(corpus, CREATED_AT)

    class ClockThatMustNotBeRead:
        @classmethod
        def fromisoformat(cls, value: str):
            return real_datetime.fromisoformat(value)

        @classmethod
        def now(cls, *args, **kwargs):
            raise AssertionError("wall clock must not be consulted")

    monkeypatch.setattr(arps, "datetime", ClockThatMustNotBeRead)
    after = arps.build_packets(corpus, CREATED_AT)
    assert before == after


def test_atomic_write_uses_same_directory_replace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "packet.json"
    real_replace = os.replace
    replacements: list[tuple[Path, Path]] = []

    def recording_replace(source: Path | str, destination: Path | str) -> None:
        replacements.append((Path(source), Path(destination)))
        real_replace(source, destination)

    monkeypatch.setattr(arps.os, "replace", recording_replace)
    arps.atomic_write_json(target, {"value": "UTF-8 ✓"})
    assert replacements[0][0].parent == target.parent
    assert replacements[0][1] == target
    assert target.read_text(encoding="utf-8").endswith("\n")


def test_generator_creates_no_fifth_packet(tmp_path: Path) -> None:
    output = tmp_path / "representative"
    generated = arps.generate(REPO_ROOT, CREATED_AT, output_dir=output)
    assert set(generated) == set(arps.OUTPUT_FILENAMES)
    assert sorted(path.name for path in output.iterdir()) == sorted(arps.OUTPUT_FILENAMES)


def test_generator_exposes_no_arbitrary_question_cli() -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT_PATH),
            "generate",
            "--created-at",
            CREATED_AT,
            "--question",
            "arbitrary input is prohibited",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 2
    assert "unrecognized arguments: --question" in completed.stderr


def test_generator_imports_no_network_or_runtime_clients() -> None:
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".", 1)[0])
    assert imported_roots.isdisjoint(
        {
            "aiohttp",
            "httpx",
            "requests",
            "socket",
            "urllib",
            "redis",
            "psycopg",
            "guardian",
            "openai",
        }
    )


def test_all_outputs_are_utf8_newline_terminated_json() -> None:
    for filename in arps.OUTPUT_FILENAMES:
        raw = (OUTPUT_DIR / filename).read_bytes()
        assert raw.endswith(b"\n")
        assert isinstance(json.loads(raw.decode("utf-8")), dict)


def test_representative_arps_have_plaintext_git_attributes_and_are_not_lfs_managed() -> None:
    paths = [(arps.OUTPUT_RELATIVE_DIR / name).as_posix() for name in arps.OUTPUT_FILENAMES]
    attributes = git("check-attr", "filter", "diff", "merge", "text", "--", *paths)
    for path in paths:
        matching = [line for line in attributes.splitlines() if line.startswith(path + ":")]
        assert any(": filter: unspecified" in line for line in matching)
        assert any(": diff: set" in line for line in matching)
        assert any(": merge: unspecified" in line for line in matching)
        assert any(": text: set" in line for line in matching)
    lfs_paths = set(git("lfs", "ls-files", "-n").splitlines())
    assert lfs_paths.isdisjoint(paths)


def _assert_files_match_phase3a_blobs(paths: list[Path]) -> None:
    for path in paths:
        relative = path.relative_to(REPO_ROOT).as_posix()
        baseline_blob = git("rev-parse", f"{PHASE3A_SHA}:{relative}")
        current_blob = git("hash-object", relative)
        assert current_blob == baseline_blob, relative


def test_canonical_nine_node_blobs_remain_unchanged() -> None:
    paths = sorted((REPO_ROOT / "docs/knowledge-graph/nodes").glob("*.json"))
    assert len(paths) == 9
    _assert_files_match_phase3a_blobs(paths)


def test_phase3a_six_generated_projection_blobs_remain_unchanged() -> None:
    paths = [
        REPO_ROOT / "docs/knowledge-graph/generated" / filename
        for filename in (
            "document-graph.json",
            "stale-documents.json",
            "supersession-map.json",
            "authority-conflicts.json",
            "collisions.json",
            "orphans.json",
        )
    ]
    _assert_files_match_phase3a_blobs(paths)


def test_governed_markdown_source_blobs_remain_unchanged(corpus: arps.Corpus) -> None:
    paths = [REPO_ROOT / node["path"] for node in corpus.nodes_by_id.values()]
    assert len(paths) == 9
    _assert_files_match_phase3a_blobs(paths)
