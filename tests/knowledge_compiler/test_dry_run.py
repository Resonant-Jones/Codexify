from __future__ import annotations

import hashlib
import importlib.util
import sys
import types
from pathlib import Path

import pytest


def _load_knowledge_compiler_package() -> types.ModuleType:
    repo_root = Path(__file__).resolve().parents[2]
    guardian_root = repo_root / "guardian"
    package_root = guardian_root / "knowledge_compiler"

    guardian_package = types.ModuleType("guardian")
    guardian_package.__path__ = [str(guardian_root)]
    sys.modules["guardian"] = guardian_package

    spec = importlib.util.spec_from_file_location(
        "guardian.knowledge_compiler",
        package_root / "__init__.py",
        submodule_search_locations=[str(package_root)],
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load guardian.knowledge_compiler package.")

    module = importlib.util.module_from_spec(spec)
    sys.modules["guardian.knowledge_compiler"] = module
    spec.loader.exec_module(module)
    return module


knowledge_compiler = _load_knowledge_compiler_package()

KnowledgeArtifactKind = knowledge_compiler.KnowledgeArtifactKind
KnowledgeChangeState = knowledge_compiler.KnowledgeChangeState
KnowledgeCompilerBudget = knowledge_compiler.KnowledgeCompilerBudget
KnowledgeCompilerDryRunRequest = knowledge_compiler.KnowledgeCompilerDryRunRequest
KnowledgeReviewState = knowledge_compiler.KnowledgeReviewState
KnowledgeScopeKind = knowledge_compiler.KnowledgeScopeKind
KnowledgeSourceItem = knowledge_compiler.KnowledgeSourceItem
KnowledgeSourceProvenance = knowledge_compiler.KnowledgeSourceProvenance
KnowledgeSourceType = knowledge_compiler.KnowledgeSourceType
run_project_knowledge_compiler_dry_run = (
    knowledge_compiler.run_project_knowledge_compiler_dry_run
)


def _hash_for(content: str) -> str:
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def _source(
    source_id: str,
    *,
    content: str | None = None,
    scope_kind: KnowledgeScopeKind = KnowledgeScopeKind.PROJECT,
    scope_id: str = "project-123",
    source_type: KnowledgeSourceType = KnowledgeSourceType.DOCUMENT,
    title: str | None = None,
) -> KnowledgeSourceItem:
    normalized_content = content or f"content for {source_id}"
    return KnowledgeSourceItem(
        source_id=source_id,
        scope_kind=scope_kind,
        scope_id=scope_id,
        source_type=source_type,
        title=title or f"Title for {source_id}",
        content=normalized_content,
        content_hash=_hash_for(normalized_content),
        created_at="2026-05-19T00:00:00Z",
        updated_at="2026-05-19T00:00:00Z",
        provenance=KnowledgeSourceProvenance(
            project_id=scope_id,
            document_id=f"doc-{source_id}",
        ),
    )


def _budget(
    *,
    max_sources: int = 10,
    max_artifacts: int = 10,
    max_model_calls: int = 0,
    max_wall_time_seconds: int = 30,
    max_graph_edges: int = 0,
    max_write_operations: int = 0,
) -> KnowledgeCompilerBudget:
    return KnowledgeCompilerBudget(
        max_sources=max_sources,
        max_artifacts=max_artifacts,
        max_model_calls=max_model_calls,
        max_wall_time_seconds=max_wall_time_seconds,
        max_graph_edges=max_graph_edges,
        max_write_operations=max_write_operations,
    )


def _request(
    *sources: KnowledgeSourceItem,
    scope_kind: KnowledgeScopeKind = KnowledgeScopeKind.PROJECT,
    scope_id: str = "project-123",
    trigger_kind: str = "manual",
    previous_hashes: dict[str, str] | None = None,
    budget: KnowledgeCompilerBudget | None = None,
) -> KnowledgeCompilerDryRunRequest:
    return KnowledgeCompilerDryRunRequest(
        scope_kind=scope_kind,
        scope_id=scope_id,
        trigger_kind=trigger_kind,
        sources=tuple(sources),
        previous_hashes=previous_hashes or {},
        budget=budget or _budget(),
    )


def test_project_dry_run_accepts_bounded_project_sources() -> None:
    first = _source("source-2", source_type=KnowledgeSourceType.MESSAGE)
    second = _source("source-1", source_type=KnowledgeSourceType.DOCUMENT)

    report = run_project_knowledge_compiler_dry_run(_request(first, second))

    assert report.scope_kind == KnowledgeScopeKind.PROJECT
    assert report.source_candidates_discovered == 2
    assert [change.source_id for change in report.source_changes] == [
        "source-1",
        "source-2",
    ]
    assert report.draft_artifacts_generated == 2


def test_non_project_scope_is_rejected() -> None:
    source = _source(
        "source-1",
        scope_kind=KnowledgeScopeKind.WORKSPACE,
        scope_id="workspace-123",
    )
    request = _request(
        source,
        scope_kind=KnowledgeScopeKind.WORKSPACE,
        scope_id="workspace-123",
    )

    with pytest.raises(ValueError, match="only supports project scope"):
        run_project_knowledge_compiler_dry_run(request)


def test_new_source_detection() -> None:
    source = _source("source-1")

    report = run_project_knowledge_compiler_dry_run(_request(source))

    assert report.changed_sources_detected == 1
    assert report.source_changes[0].change_state == KnowledgeChangeState.NEW
    assert report.artifacts[0].metadata["change_state"] == "new"


def test_changed_source_detection() -> None:
    source = _source("source-1", content="new content")
    request = _request(
        source,
        previous_hashes={"source-1": _hash_for("old content")},
    )

    report = run_project_knowledge_compiler_dry_run(request)

    assert report.changed_sources_detected == 1
    assert report.source_changes[0].change_state == KnowledgeChangeState.CHANGED


def test_unchanged_source_does_not_produce_a_draft_artifact() -> None:
    source = _source("source-1")
    request = _request(
        source,
        previous_hashes={"source-1": source.content_hash},
    )

    report = run_project_knowledge_compiler_dry_run(request)

    assert report.changed_sources_detected == 0
    assert report.source_changes[0].change_state == KnowledgeChangeState.UNCHANGED
    assert report.draft_artifacts_generated == 0
    assert report.artifacts == ()


def test_skipped_sources_are_reported_when_over_max_sources() -> None:
    first = _source("source-1")
    second = _source("source-2")
    third = _source("source-3")
    request = _request(
        third,
        first,
        second,
        budget=_budget(max_sources=2, max_artifacts=10),
    )

    report = run_project_knowledge_compiler_dry_run(request)

    assert report.sources_skipped == ("source-3",)
    assert report.source_changes[-1].change_state == KnowledgeChangeState.EXCLUDED
    assert report.budget_used["sources_skipped"] == 1


def test_max_artifacts_is_enforced() -> None:
    request = _request(
        _source("source-1"),
        _source("source-2"),
        _source("source-3"),
        budget=_budget(max_sources=3, max_artifacts=2),
    )

    report = run_project_knowledge_compiler_dry_run(request)

    assert report.changed_sources_detected == 3
    assert report.draft_artifacts_generated == 2
    assert len(report.artifacts) == 2


def test_generated_artifact_ids_are_deterministic() -> None:
    request = _request(_source("source-1", content="stable"))

    first_report = run_project_knowledge_compiler_dry_run(request)
    second_report = run_project_knowledge_compiler_dry_run(request)

    assert first_report.run_id == second_report.run_id
    assert first_report.artifacts[0].artifact_id == second_report.artifacts[0].artifact_id


def test_generated_artifacts_are_draft_only_and_not_retrieval_visible() -> None:
    report = run_project_knowledge_compiler_dry_run(_request(_source("source-1")))

    artifact = report.artifacts[0]
    assert artifact.artifact_kind == KnowledgeArtifactKind.CODEX_ENTRY_DRAFT
    assert artifact.review_state == KnowledgeReviewState.DRAFT
    assert artifact.retrieval_visible is False


def test_provenance_source_ids_are_preserved() -> None:
    source = _source("source-1")

    report = run_project_knowledge_compiler_dry_run(_request(source))

    assert report.artifacts[0].source_ids == ("source-1",)


def test_model_call_budget_greater_than_zero_is_rejected() -> None:
    with pytest.raises(ValueError, match="model calls"):
        _request(_source("source-1"), budget=_budget(max_model_calls=1))


def test_write_operation_budget_greater_than_zero_is_rejected() -> None:
    with pytest.raises(ValueError, match="write operations"):
        _request(_source("source-1"), budget=_budget(max_write_operations=1))


def test_no_mutable_default_leakage_between_reports() -> None:
    request = _request(_source("source-1"))

    first_report = run_project_knowledge_compiler_dry_run(request)
    second_report = run_project_knowledge_compiler_dry_run(request)

    first_report.budget_used["artifacts_generated"] = 999
    first_report.artifacts[0].metadata["change_state"] = "mutated"

    assert second_report.budget_used["artifacts_generated"] == 1
    assert second_report.artifacts[0].metadata["change_state"] == "new"


def test_proof_report_counts_match_generated_artifacts_and_changes() -> None:
    new_source = _source("source-1", content="new source")
    changed_source = _source("source-2", content="changed source")
    unchanged_source = _source("source-3", content="unchanged source")
    request = _request(
        new_source,
        changed_source,
        unchanged_source,
        previous_hashes={
            "source-2": _hash_for("old changed source"),
            "source-3": unchanged_source.content_hash,
        },
        budget=_budget(max_sources=3, max_artifacts=10),
    )

    report = run_project_knowledge_compiler_dry_run(request)

    assert report.source_candidates_discovered == 3
    assert report.changed_sources_detected == 2
    assert report.draft_artifacts_generated == 2
    assert len(report.artifacts) == 2
    assert len(report.source_changes) == 3
    assert report.artifacts_approved == 0
    assert report.artifacts_published == 0
    assert report.retrieval_cards_generated == 0
    assert report.graph_edges_proposed == 0
