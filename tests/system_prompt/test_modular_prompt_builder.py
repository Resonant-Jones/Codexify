from __future__ import annotations

from guardian.cognition.modular_prompt_builder import (
    PromptBudgets,
    build_system_prompt,
)


def test_build_system_prompt_returns_single_string_and_fixed_order() -> None:
    system_prompt, meta = build_system_prompt(
        base_system_prompt="Base rules",
        imprint_block="Imprint guidance",
        persona_block="Persona guidance",
        system_docs_block="System docs guidance",
        scratchpad_block="Scratchpad guidance",
    )

    assert isinstance(system_prompt, str)
    assert "=== BASE SYSTEM ===" in system_prompt
    assert "=== IMPRINT_ZERO ===" in system_prompt
    assert "=== PERSONA ===" in system_prompt
    assert "=== SYSTEM DOCS ===" in system_prompt
    assert "=== SCRATCHPAD ===" in system_prompt

    assert system_prompt.index("=== BASE SYSTEM ===") < system_prompt.index(
        "=== IMPRINT_ZERO ==="
    )
    assert system_prompt.index("=== IMPRINT_ZERO ===") < system_prompt.index(
        "=== PERSONA ==="
    )
    assert system_prompt.index("=== PERSONA ===") < system_prompt.index(
        "=== SYSTEM DOCS ==="
    )
    assert system_prompt.index("=== SYSTEM DOCS ===") < system_prompt.index(
        "=== SCRATCHPAD ==="
    )

    segments = meta["segments"]
    assert [segment["name"] for segment in segments] == [
        "base",
        "imprint",
        "persona",
        "system_docs",
        "scratchpad",
    ]
    assert segments[0]["text"] == "Base rules"
    assert segments[0]["cacheable"] is True
    assert segments[-1]["cacheable"] is False
    assert meta["estimated_tokens_total"] == sum(
        segment["estimated_tokens"] for segment in segments
    )


def test_build_system_prompt_meta_includes_segment_token_counts() -> None:
    _prompt, meta = build_system_prompt(
        base_system_prompt="Base rules",
        imprint_block="I" * 40,
        persona_block="P" * 20,
    )
    segments = {segment["name"]: segment for segment in meta["segments"]}
    assert segments["base"]["estimated_tokens"] > 0
    assert segments["imprint"]["estimated_tokens"] > 0
    assert segments["persona"]["estimated_tokens"] > 0
    assert segments["system_docs"]["estimated_tokens"] == 0
    assert segments["scratchpad"]["estimated_tokens"] == 0


def test_build_system_prompt_truncates_only_target_segment() -> None:
    prompt, meta = build_system_prompt(
        base_system_prompt="Base rules",
        imprint_block="I" * 200,
        persona_block="Persona guidance",
        system_docs_block="Docs guidance",
        budgets=PromptBudgets(imprint_max_tokens=5),
    )
    segments = {segment["name"]: segment for segment in meta["segments"]}

    assert segments["imprint"]["truncated"] is True
    assert segments["persona"]["truncated"] is False
    assert segments["system_docs"]["truncated"] is False
    assert "imprint segment truncated" in " ".join(meta["truncation_notes"])
    assert prompt.count("=== IMPRINT_ZERO ===") == 1
    assert prompt.count("=== PERSONA ===") == 1


def test_build_system_prompt_delimiters_once_for_included_segments() -> None:
    prompt, _meta = build_system_prompt(
        base_system_prompt="Base rules",
        persona_block="Persona guidance",
    )
    assert prompt.count("=== BASE SYSTEM ===") == 1
    assert prompt.count("=== PERSONA ===") == 1
    assert prompt.count("=== IMPRINT_ZERO ===") == 0
    assert prompt.count("=== SYSTEM DOCS ===") == 0
    assert prompt.count("=== SCRATCHPAD ===") == 0
