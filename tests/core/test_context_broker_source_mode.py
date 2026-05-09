from __future__ import annotations

from guardian.context.retrieval_router_policy import (
    SOURCE_MODE_CONVERSATION,
    SOURCE_MODE_OBSIDIAN_ONLY,
    SOURCE_MODE_PERSONAL_KNOWLEDGE,
    SOURCE_MODE_PROJECT,
    SOURCE_MODE_WORKSPACE,
    normalize_source_mode,
    source_mode_boundary_label,
)


def test_source_mode_normalization_aliases_are_stable() -> None:
    assert normalize_source_mode("obsidian") == SOURCE_MODE_OBSIDIAN_ONLY
    assert normalize_source_mode("workspace") == SOURCE_MODE_WORKSPACE
    assert normalize_source_mode("project") == SOURCE_MODE_PROJECT
    assert normalize_source_mode("conversation") == SOURCE_MODE_CONVERSATION


def test_source_mode_boundary_labels_are_stable() -> None:
    assert (
        source_mode_boundary_label(SOURCE_MODE_PROJECT)
        == "same_user_same_project"
    )
    assert (
        source_mode_boundary_label(SOURCE_MODE_PERSONAL_KNOWLEDGE)
        == "same_user_only"
    )
    assert (
        source_mode_boundary_label(SOURCE_MODE_OBSIDIAN_ONLY)
        == "same_user_only"
    )
    assert (
        source_mode_boundary_label(SOURCE_MODE_CONVERSATION)
        == "active_conversation_only"
    )


def test_source_mode_registry_helpers_are_bounded() -> None:
    assert {
        SOURCE_MODE_PROJECT,
        SOURCE_MODE_PERSONAL_KNOWLEDGE,
        SOURCE_MODE_CONVERSATION,
        SOURCE_MODE_OBSIDIAN_ONLY,
        SOURCE_MODE_WORKSPACE,
    } == {
        "project",
        "personal_knowledge",
        "conversation",
        "obsidian_only",
        "workspace",
    }
