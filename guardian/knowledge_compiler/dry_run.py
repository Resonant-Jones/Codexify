"""Deterministic project-scoped dry-run harness for the Knowledge Compiler."""

from __future__ import annotations

import hashlib

from guardian.knowledge_compiler.contracts import (
    CompiledKnowledgeArtifact,
    KnowledgeArtifactKind,
    KnowledgeChangeState,
    KnowledgeCompilerDryRunRequest,
    KnowledgeCompilerProofReport,
    KnowledgeReviewState,
    KnowledgeScopeKind,
    KnowledgeSourceChange,
    KnowledgeSourceItem,
)


def _stable_digest(parts: tuple[str, ...]) -> str:
    payload = "\n".join(parts).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _build_run_id(request: KnowledgeCompilerDryRunRequest) -> str:
    source_fingerprint = tuple(
        f"{source.source_id}:{source.content_hash}"
        for source in sorted(request.sources, key=lambda item: item.source_id)
    )
    previous_hash_fingerprint = tuple(
        f"{source_id}:{request.previous_hashes[source_id]}"
        for source_id in sorted(request.previous_hashes)
    )
    digest = _stable_digest(
        (
            request.scope_kind.value,
            request.scope_id,
            request.trigger_kind,
            *source_fingerprint,
            *previous_hash_fingerprint,
            str(request.budget.max_sources),
            str(request.budget.max_artifacts),
            str(request.budget.max_model_calls),
            str(request.budget.max_wall_time_seconds),
            str(request.budget.max_graph_edges),
            str(request.budget.max_write_operations),
        )
    )
    return f"kcdryrun_{digest[:16]}"


def _build_artifact_id(source: KnowledgeSourceItem) -> str:
    digest = _stable_digest(
        (
            source.scope_kind.value,
            source.scope_id,
            source.source_id,
            source.content_hash,
        )
    )
    return f"kcdraft_{digest[:16]}"


def _detect_change(
    source: KnowledgeSourceItem,
    previous_hashes: dict[str, str],
) -> KnowledgeSourceChange:
    previous_hash = previous_hashes.get(source.source_id)
    if previous_hash is None:
        return KnowledgeSourceChange(
            source_id=source.source_id,
            change_state=KnowledgeChangeState.NEW,
            previous_hash=None,
            current_hash=source.content_hash,
            reason="no previous hash recorded",
        )
    if previous_hash != source.content_hash:
        return KnowledgeSourceChange(
            source_id=source.source_id,
            change_state=KnowledgeChangeState.CHANGED,
            previous_hash=previous_hash,
            current_hash=source.content_hash,
            reason="content hash changed",
        )
    return KnowledgeSourceChange(
        source_id=source.source_id,
        change_state=KnowledgeChangeState.UNCHANGED,
        previous_hash=previous_hash,
        current_hash=source.content_hash,
        reason="content hash unchanged",
    )


def _build_excluded_change(source: KnowledgeSourceItem) -> KnowledgeSourceChange:
    return KnowledgeSourceChange(
        source_id=source.source_id,
        change_state=KnowledgeChangeState.EXCLUDED,
        previous_hash=None,
        current_hash=source.content_hash,
        reason="skipped because max_sources budget was exceeded",
    )


def _build_draft_artifact(
    source: KnowledgeSourceItem,
    change: KnowledgeSourceChange,
) -> CompiledKnowledgeArtifact:
    title = source.title or f"Draft knowledge artifact for {source.source_id}"
    body = "\n".join(
        (
            "Draft Codex knowledge artifact proposal",
            f"Scope: {source.scope_kind.value}/{source.scope_id}",
            f"Source ID: {source.source_id}",
            f"Source Type: {source.source_type.value}",
            f"Change State: {change.change_state.value}",
            f"Content Hash: {source.content_hash}",
            "",
            source.content,
        )
    )
    return CompiledKnowledgeArtifact(
        artifact_id=_build_artifact_id(source),
        artifact_kind=KnowledgeArtifactKind.CODEX_ENTRY_DRAFT,
        scope_kind=source.scope_kind,
        scope_id=source.scope_id,
        title=title,
        body=body,
        source_ids=(source.source_id,),
        review_state=KnowledgeReviewState.DRAFT,
        retrieval_visible=False,
        metadata={
            "source_type": source.source_type.value,
            "change_state": change.change_state.value,
        },
    )


def run_project_knowledge_compiler_dry_run(
    request: KnowledgeCompilerDryRunRequest,
) -> KnowledgeCompilerProofReport:
    """Run the first pure project-scoped Knowledge Compiler dry-run harness."""

    if request.scope_kind != KnowledgeScopeKind.PROJECT:
        raise ValueError(
            "run_project_knowledge_compiler_dry_run only supports project scope."
        )
    if request.budget.max_model_calls > 0:
        raise ValueError("Dry-run budgets must not allow model calls.")
    if request.budget.max_write_operations > 0:
        raise ValueError("Dry-run budgets must not allow write operations.")

    sorted_sources = tuple(
        sorted(request.sources, key=lambda item: item.source_id)
    )
    included_sources = sorted_sources[: request.budget.max_sources]
    skipped_sources = sorted_sources[request.budget.max_sources :]

    source_changes: list[KnowledgeSourceChange] = []
    changed_sources_detected = 0

    for source in included_sources:
        change = _detect_change(source, request.previous_hashes)
        source_changes.append(change)
        if change.change_state in (
            KnowledgeChangeState.NEW,
            KnowledgeChangeState.CHANGED,
        ):
            changed_sources_detected += 1

    for source in skipped_sources:
        source_changes.append(_build_excluded_change(source))

    artifacts: list[CompiledKnowledgeArtifact] = []
    for change in source_changes:
        if change.change_state not in (
            KnowledgeChangeState.NEW,
            KnowledgeChangeState.CHANGED,
        ):
            continue
        if len(artifacts) >= request.budget.max_artifacts:
            break
        source = next(
            item for item in included_sources if item.source_id == change.source_id
        )
        artifacts.append(_build_draft_artifact(source, change))

    return KnowledgeCompilerProofReport(
        run_id=_build_run_id(request),
        scope_kind=request.scope_kind,
        scope_id=request.scope_id,
        trigger_kind=request.trigger_kind,
        source_candidates_discovered=len(sorted_sources),
        changed_sources_detected=changed_sources_detected,
        sources_skipped=tuple(source.source_id for source in skipped_sources),
        source_changes=tuple(source_changes),
        draft_artifacts_generated=len(artifacts),
        artifacts_approved=0,
        artifacts_published=0,
        retrieval_cards_generated=0,
        graph_edges_proposed=0,
        budget_used={
            "sources_considered": len(included_sources),
            "sources_skipped": len(skipped_sources),
            "artifacts_generated": len(artifacts),
            "model_calls": 0,
            "graph_edges": 0,
            "write_operations": 0,
            "wall_time_seconds": 0,
        },
        errors=(),
        policy_exclusions=(),
        review_status="draft_only",
        artifacts=tuple(artifacts),
    )


__all__ = ["run_project_knowledge_compiler_dry_run"]
