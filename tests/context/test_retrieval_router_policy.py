from guardian.context.retrieval_router_policy import (
    ROUTER_POLICY,
    EscalationStep,
    GraphAllowance,
    PolicyRule,
    QueryIntent,
    RetrievalDepth,
    TimeMode,
    resolve_retrieval_plan,
)


def test_conversation_only_disables_retrieval_and_global_fallback() -> None:
    plan = resolve_retrieval_plan(
        "hello",
        RetrievalDepth.AUTO,
        intent=QueryIntent.CONVERSATION_ONLY,
    )

    assert plan.retrieval_needed is False
    assert plan.effective_depth == RetrievalDepth.SHALLOW
    assert plan.escalation_order == ()
    assert plan.allow_global_fallback is False


def test_timeline_recall_uses_chronological_time_mode() -> None:
    plan = resolve_retrieval_plan(
        "when did that happen?",
        RetrievalDepth.AUTO,
        intent=QueryIntent.TIMELINE_RECALL,
    )

    assert plan.time_mode == TimeMode.CHRONOLOGICAL


def test_provenance_prefers_graph_more_than_direct_qa() -> None:
    qa_plan = resolve_retrieval_plan(
        "answer this question",
        RetrievalDepth.AUTO,
        intent=QueryIntent.DIRECT_QA,
    )
    provenance_plan = resolve_retrieval_plan(
        "where did this come from?",
        RetrievalDepth.AUTO,
        intent=QueryIntent.PROVENANCE,
    )

    assert qa_plan.graph_allowance == GraphAllowance.DISALLOW
    assert provenance_plan.graph_allowance == GraphAllowance.PREFER_ENRICHMENT


def test_scope_locked_local_disables_adjacent_and_global_expansion() -> None:
    plan = resolve_retrieval_plan(
        "only in this thread",
        RetrievalDepth.AUTO,
        intent=QueryIntent.SCOPE_LOCKED_LOCAL,
    )

    assert EscalationStep.ADJACENT_LOCAL not in plan.escalation_order
    assert EscalationStep.GLOBAL_SEARCH not in plan.escalation_order
    assert plan.allow_global_fallback is False


def test_auto_depth_resolves_per_intent_instead_of_always_deep() -> None:
    direct_plan = resolve_retrieval_plan(
        "what is the status?",
        RetrievalDepth.AUTO,
        intent=QueryIntent.DIRECT_QA,
    )
    memory_plan = resolve_retrieval_plan(
        "what do you remember about this?",
        RetrievalDepth.AUTO,
        intent=QueryIntent.MEMORY_RECALL,
    )
    conversation_plan = resolve_retrieval_plan(
        "thanks",
        RetrievalDepth.AUTO,
        intent=QueryIntent.CONVERSATION_ONLY,
    )

    assert direct_plan.effective_depth == RetrievalDepth.NORMAL
    assert memory_plan.effective_depth == RetrievalDepth.DEEP
    assert conversation_plan.effective_depth == RetrievalDepth.SHALLOW


def test_policy_registry_is_stable_and_complete() -> None:
    assert set(ROUTER_POLICY) == set(QueryIntent)

    for intent, rule in ROUTER_POLICY.items():
        assert isinstance(rule, PolicyRule)
        assert rule.intent is intent
