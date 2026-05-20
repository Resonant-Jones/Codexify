from __future__ import annotations

import dataclasses
import inspect

from guardian.context.memory_preselector import (
    MemoryCandidateHeader,
    MemoryPreselectorRequest,
    select_memory_candidates,
)


def _candidate(**overrides: object) -> MemoryCandidateHeader:
    payload: dict[str, object] = {
        "candidate_id": "cand-1",
        "user_id": "user-1",
        "kind": "episodic",
        "title": "Alpha title",
        "summary": "Alpha summary",
        "tags": ("alpha",),
        "silo": "midterm",
        "project_id": "project-1",
        "thread_id": "thread-1",
        "persona_id": "persona-1",
        "identity_depth": "light",
        "diary_excluded": False,
    }
    payload.update(overrides)
    return MemoryCandidateHeader(**payload)


def _request(**overrides: object) -> MemoryPreselectorRequest:
    payload: dict[str, object] = {
        "query": "alpha",
        "user_id": "user-1",
        "project_id": "project-1",
        "thread_id": "thread-1",
        "persona_id": "persona-1",
        "allowed_silos": (),
        "identity_depth": "light",
        "include_diary_excluded": False,
        "limit": 20,
        "min_score": 1,
    }
    payload.update(overrides)
    return MemoryPreselectorRequest(**payload)


def test_missing_request_user_id_suppresses_all_with_missing_user_scope() -> None:
    result = select_memory_candidates(
        [_candidate(candidate_id="a"), _candidate(candidate_id="b")],
        _request(user_id=""),
    )

    assert result.selected == ()
    assert {entry.candidate_id for entry in result.suppressed} == {"a", "b"}
    assert all(entry.reason == "missing_user_scope" for entry in result.suppressed)


def test_candidate_user_id_mismatch_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(user_id="someone-else")],
        _request(),
    )

    assert result.selected == ()
    assert result.suppressed[0].reason == "user_scope_mismatch"


def test_matching_user_id_candidate_can_be_selected() -> None:
    result = select_memory_candidates([_candidate()], _request(query="alpha"))
    assert len(result.selected) == 1
    assert result.selected[0].candidate_id == "cand-1"


def test_project_scope_mismatch_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(project_id="project-2")],
        _request(project_id="project-1"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "project_scope_mismatch"


def test_thread_scope_mismatch_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(thread_id="thread-2")],
        _request(thread_id="thread-1"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "thread_scope_mismatch"


def test_persona_scope_mismatch_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(persona_id="persona-2")],
        _request(persona_id="persona-1"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "persona_scope_mismatch"


def test_allowed_silo_mismatch_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(silo="longterm")],
        _request(allowed_silos=("midterm",)),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "silo_not_allowed"


def test_diary_excluded_candidate_suppressed_when_include_false() -> None:
    result = select_memory_candidates(
        [_candidate(diary_excluded=True)],
        _request(include_diary_excluded=False),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "diary_excluded"


def test_diary_excluded_candidate_can_be_selected_when_include_true() -> None:
    result = select_memory_candidates(
        [_candidate(diary_excluded=True)],
        _request(include_diary_excluded=True),
    )
    assert len(result.selected) == 1
    assert result.selected[0].candidate_id == "cand-1"


def test_deep_candidate_suppressed_when_request_depth_is_light() -> None:
    result = select_memory_candidates(
        [_candidate(identity_depth="deep")],
        _request(identity_depth="light"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "identity_depth_exceeded"


def test_light_candidate_allowed_when_request_depth_is_light() -> None:
    result = select_memory_candidates(
        [_candidate(identity_depth="light")],
        _request(identity_depth="light"),
    )
    assert len(result.selected) == 1


def test_unknown_candidate_identity_depth_is_suppressed() -> None:
    result = select_memory_candidates(
        [_candidate(identity_depth="mystery")],
        _request(identity_depth="deep"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "identity_depth_exceeded"


def test_unknown_request_identity_depth_fails_closed() -> None:
    result = select_memory_candidates(
        [_candidate(identity_depth="light")],
        _request(identity_depth="unknown-depth"),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "identity_depth_exceeded"


def test_blank_query_selects_no_candidates() -> None:
    result = select_memory_candidates([_candidate()], _request(query="   "))
    assert result.selected == ()
    assert result.suppressed[0].reason == "not_relevant"


def test_query_matches_candidate_title() -> None:
    result = select_memory_candidates(
        [_candidate(title="Neural lattice mapping")],
        _request(query="lattice"),
    )
    assert len(result.selected) == 1


def test_query_matches_candidate_summary() -> None:
    result = select_memory_candidates(
        [_candidate(summary="Foundational memory scaffold")],
        _request(query="scaffold"),
    )
    assert len(result.selected) == 1


def test_query_matches_candidate_tags() -> None:
    result = select_memory_candidates(
        [_candidate(tags=("federation", "ledger"))],
        _request(query="ledger"),
    )
    assert len(result.selected) == 1


def test_query_matches_candidate_silo() -> None:
    result = select_memory_candidates(
        [_candidate(silo="longterm", title="no match", summary="no match", tags=("x",))],
        _request(query="longterm"),
    )
    assert len(result.selected) == 1


def test_query_matches_candidate_kind() -> None:
    result = select_memory_candidates(
        [_candidate(kind="document", title="no match", summary="none", tags=("z",))],
        _request(query="document"),
    )
    assert len(result.selected) == 1


def test_title_match_outranks_summary_only_match() -> None:
    result = select_memory_candidates(
        [
            _candidate(candidate_id="b", title="vector policy", summary="none"),
            _candidate(candidate_id="a", title="none", summary="vector policy"),
        ],
        _request(query="vector"),
    )
    assert len(result.selected) == 2
    assert result.selected[0].candidate_id == "b"
    assert result.selected[1].candidate_id == "a"


def test_tie_break_is_deterministic_by_candidate_id() -> None:
    first = _candidate(candidate_id="b", title="same score")
    second = _candidate(candidate_id="a", title="same score")
    result = select_memory_candidates([first, second], _request(query="same"))
    assert [item.candidate_id for item in result.selected] == ["a", "b"]


def test_min_score_suppresses_low_score_candidates() -> None:
    result = select_memory_candidates(
        [_candidate(title="only title hit", summary="")],
        _request(query="title", min_score=999),
    )
    assert result.selected == ()
    assert result.suppressed[0].reason == "score_too_low"


def test_limit_is_respected() -> None:
    candidates = [
        _candidate(candidate_id=f"cand-{idx}", title="alpha match")
        for idx in range(5)
    ]
    result = select_memory_candidates(candidates, _request(limit=2))
    assert len(result.selected) == 2


def test_limit_is_clamped_to_safe_maximum() -> None:
    candidates = [
        _candidate(candidate_id=f"cand-{idx:03d}", title="alpha match")
        for idx in range(60)
    ]
    result = select_memory_candidates(candidates, _request(limit=500))
    assert len(result.selected) == 50


def test_selected_candidate_includes_matched_terms() -> None:
    result = select_memory_candidates(
        [_candidate(title="Alpha bridge", summary="beta lane", tags=("gamma",))],
        _request(query="alpha gamma"),
    )
    assert len(result.selected) == 1
    assert set(result.selected[0].matched_terms) == {"alpha", "gamma"}


def test_selected_candidate_includes_relevant_boost_hints() -> None:
    result = select_memory_candidates(
        [
            _candidate(
                title="alpha title",
                summary="alpha summary",
                tags=("alpha",),
                project_id="project-1",
                thread_id="thread-1",
                persona_id="persona-1",
                silo="midterm",
            )
        ],
        _request(
            query="alpha",
            project_id="project-1",
            thread_id="thread-1",
            persona_id="persona-1",
            allowed_silos=("midterm",),
        ),
    )
    assert len(result.selected) == 1
    hints = set(result.selected[0].boost_hints)
    assert "title_match" in hints
    assert "tag_match" in hints
    assert "summary_match" in hints
    assert "same_project" in hints
    assert "same_thread" in hints
    assert "same_persona" in hints
    assert "silo_match" in hints


def test_suppressed_result_preserves_candidate_id_and_reason() -> None:
    result = select_memory_candidates(
        [_candidate(candidate_id="cand-x", user_id="user-z")],
        _request(user_id="user-1"),
    )
    assert len(result.suppressed) == 1
    assert result.suppressed[0].candidate_id == "cand-x"
    assert result.suppressed[0].reason == "user_scope_mismatch"


def test_result_separates_selected_and_suppressed_candidates() -> None:
    result = select_memory_candidates(
        [
            _candidate(candidate_id="selected", title="alpha", summary=""),
            _candidate(
                candidate_id="suppressed",
                title="beta",
                summary="",
                tags=("omega",),
            ),
        ],
        _request(query="alpha"),
    )
    assert [item.candidate_id for item in result.selected] == ["selected"]
    assert any(item.candidate_id == "suppressed" for item in result.suppressed)


def test_selector_does_not_require_or_call_db_vector_or_llm_dependencies() -> None:
    import guardian.context.memory_preselector as module

    source = inspect.getsource(module)
    forbidden_tokens = (
        "sqlalchemy",
        "redis",
        "requests",
        "openai",
        "anthropic",
        "chromadb",
        "vector_store",
    )
    for token in forbidden_tokens:
        assert token not in source

    result = select_memory_candidates([_candidate()], _request())
    assert len(result.selected) == 1


def test_header_only_behavior_exposes_no_raw_memory_body_field() -> None:
    header_fields = {field.name for field in dataclasses.fields(MemoryCandidateHeader)}
    selected_fields = {
        field.name
        for field in dataclasses.fields(
            type(select_memory_candidates([_candidate()], _request()).selected[0])
        )
    }

    assert "content" not in header_fields
    assert "body" not in header_fields
    assert "raw_body" not in header_fields
    assert "content" not in selected_fields
    assert "body" not in selected_fields
