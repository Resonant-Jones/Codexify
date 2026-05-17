from __future__ import annotations

from guardian.command_bus.search import (
    CommandSearchQuery,
    CommandSearchRecord,
    records_from_manifest,
    search_commands,
)


def _records() -> list[CommandSearchRecord]:
    return [
        CommandSearchRecord(
            command_id="op::health_check",
            method="GET",
            path="/health",
            summary="Health check endpoint",
            description="Read runtime health diagnostics",
            aliases=("route::GET::/health", "health-alias"),
            tags=("system", "status"),
            command_class="read",
            internal=True,
        ),
        CommandSearchRecord(
            command_id="op::github.list_repos",
            method="GET",
            path="/connectors/github/repos",
            summary="List GitHub repositories",
            description="Reads connector metadata for repositories",
            aliases=("repo-list",),
            tags=("github", "connector"),
            command_class="connector",
            internal=True,
        ),
        CommandSearchRecord(
            command_id="op::document.semantic_query",
            method="POST",
            path="/documents/search",
            summary="Search documents",
            description="Semantic ranking over indexed documents",
            aliases=("doc-find",),
            tags=("documents", "semantic"),
            command_class="memory",
            internal=True,
        ),
    ]


def test_blank_query_returns_empty_results() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="   "))
    assert results == []


def test_simple_term_matches_command_id() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="health_check"))
    assert results[0].command_id == "op::health_check"


def test_simple_term_matches_alias() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="repo-list"))
    assert results[0].command_id == "op::github.list_repos"


def test_simple_term_matches_method() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="post"))
    assert results[0].command_id == "op::document.semantic_query"


def test_simple_term_matches_path() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="/health"))
    assert results[0].command_id == "op::health_check"


def test_simple_term_matches_summary() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="repositories"))
    assert results[0].command_id == "op::github.list_repos"


def test_simple_term_matches_description() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="diagnostics"))
    assert results[0].command_id == "op::health_check"


def test_simple_term_matches_tags() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="semantic"))
    assert results[0].command_id == "op::document.semantic_query"


def test_simple_term_matches_command_class() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="connector"))
    assert results[0].command_id == "op::github.list_repos"


def test_case_insensitive_matching_works() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="GITHUB"))
    assert results[0].command_id == "op::github.list_repos"


def test_required_term_filters_out_non_matching_records() -> None:
    results = search_commands(_records(), CommandSearchQuery(query="+github"))
    assert [item.command_id for item in results] == ["op::github.list_repos"]


def test_multiple_required_terms_must_all_match() -> None:
    results = search_commands(
        _records(),
        CommandSearchQuery(query="+github +repos"),
    )
    assert [item.command_id for item in results] == ["op::github.list_repos"]


def test_non_required_terms_contribute_to_score_but_are_not_mandatory() -> None:
    results = search_commands(
        _records(),
        CommandSearchQuery(query="+github health"),
    )
    assert [item.command_id for item in results] == ["op::github.list_repos"]


def test_exact_command_id_match_outranks_alias_and_description_matches() -> None:
    records = [
        CommandSearchRecord(
            command_id="health",
            aliases=(),
            description="",
        ),
        CommandSearchRecord(
            command_id="op::health_alias",
            aliases=("health",),
            description="",
        ),
        CommandSearchRecord(
            command_id="op::health_desc",
            aliases=(),
            description="health",
        ),
    ]
    results = search_commands(records, CommandSearchQuery(query="health"))
    assert [item.command_id for item in results] == [
        "health",
        "op::health_alias",
        "op::health_desc",
    ]


def test_alias_match_outranks_description_match() -> None:
    records = [
        CommandSearchRecord(
            command_id="op::alias_target",
            aliases=("needle",),
            description="",
        ),
        CommandSearchRecord(
            command_id="op::desc_target",
            aliases=(),
            description="needle",
        ),
    ]
    results = search_commands(records, CommandSearchQuery(query="needle"))
    assert [item.command_id for item in results] == [
        "op::alias_target",
        "op::desc_target",
    ]


def test_tie_break_is_deterministic_by_command_id_ascending() -> None:
    records = [
        CommandSearchRecord(command_id="op::zeta", description="common"),
        CommandSearchRecord(command_id="op::alpha", description="common"),
    ]
    results = search_commands(records, CommandSearchQuery(query="common"))
    assert [item.command_id for item in results] == ["op::alpha", "op::zeta"]


def test_limit_is_respected() -> None:
    records = [
        CommandSearchRecord(command_id=f"op::{idx}", description="term")
        for idx in range(10)
    ]
    results = search_commands(records, CommandSearchQuery(query="term", limit=3))
    assert len(results) == 3


def test_limit_is_clamped_to_safe_maximum() -> None:
    records = [
        CommandSearchRecord(command_id=f"op::{idx}", description="term")
        for idx in range(80)
    ]
    results = search_commands(records, CommandSearchQuery(query="term", limit=999))
    assert len(results) == 50


def test_result_includes_score_matched_terms_and_required_terms() -> None:
    results = search_commands(
        _records(),
        CommandSearchQuery(query="+health diagnostics"),
    )
    assert results[0].score > 0
    assert results[0].matched_terms == ("health", "diagnostics")
    assert results[0].required_terms == ("health",)


def test_manifest_adapter_produces_records_from_manifest_metadata() -> None:
    manifest = {
        "commands": [
            {
                "command_id": "op::health_check",
                "aliases": ["route::GET::/health"],
                "method": "GET",
                "path_template": "/health",
                "operation_id": "health_check",
                "effect": "read",
                "internal": True,
            }
        ]
    }

    records = records_from_manifest(manifest)
    assert len(records) == 1
    record = records[0]
    assert record.command_id == "op::health_check"
    assert record.method == "GET"
    assert record.path == "/health"
    assert record.aliases == ("route::GET::/health",)
    assert record.summary == "health_check"
    assert record.command_class == "read"
    assert record.internal is True
