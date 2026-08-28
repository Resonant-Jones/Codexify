"""Tests for guardian.skills exposure (Phase 4).

Covers: roster block budget/line trimming, activation block body+references,
UNTRUSTED tier reference suppression, path extraction, and the extended
PromptBudgets skills segment in build_system_prompt.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardian.cognition.modular_prompt_builder import PromptBudgets, build_system_prompt
from guardian.skills.contracts import SkillRecord, TrustTier
from guardian.skills.exposure import (
    build_activation_block,
    build_roster_block,
    extract_reference_paths,
)
from guardian.skills.loader import parse_skill


def _skill_dir(tmp_path: Path, name: str = "demo", body: str | None = None) -> Path:
    skill_dir = tmp_path / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    default_body = f"# {name}\n\nBody text."
    (skill_dir / "SKILL.md").write_text(
        "---\n"
        f"name: {name}\ndescription: A demo skill\n"
        "when_to_use: When demoing\n"
        "---\n\n"
        f"{body or default_body}",
        encoding="utf-8",
    )
    return skill_dir


def _record(
    tmp_path: Path, name: str = "demo", body: str | None = None, **kwargs
) -> SkillRecord:
    skill_dir = _skill_dir(tmp_path, name, body=body)
    record = parse_skill(skill_dir, source_key="t", trust=TrustTier.LOCAL)
    assert record is not None
    return record.model_copy(update=kwargs) if kwargs else record


class TestRosterBlock:
    def test_empty_registry_yields_empty_block(self):
        block, meta = build_roster_block([])
        assert block == ""
        assert meta == {}

    def test_roster_lines_include_description(self, tmp_path):
        records = [
            _record(tmp_path, "alpha"),
            _record(tmp_path, "beta"),
        ]
        block, meta = build_roster_block(records)
        assert "Available skills:" in block
        assert "alpha — A demo skill" in block
        assert "beta — A demo skill" in block
        assert "skill_invocation" in block  # activation instruction present
        assert meta["skill_count"] == 2
        assert meta["truncated"] is False

    def test_budget_drops_whole_lines_from_end(self, tmp_path):
        records = [_record(tmp_path, f"skill-{i}") for i in range(20)]
        block, meta = build_roster_block(records, max_tokens=50)
        assert meta["truncated"] is True
        assert meta["lines_dropped"] > 0
        assert meta["lines_included"] == len(records) - meta["lines_dropped"]
        # The last line in the block must be a complete roster line
        lines = block.splitlines()
        assert "Available skills:" in block
        assert all("—" in line or line.startswith("To activate") for line in lines[1:])

    def test_no_budget_no_truncation(self, tmp_path):
        records = [_record(tmp_path, f"skill-{i}") for i in range(20)]
        block, meta = build_roster_block(records, max_tokens=None)
        assert meta["truncated"] is False
        assert meta["lines_dropped"] == 0
        assert block.count("—") == 20


class TestActivationBlock:
    def test_body_included_with_header(self, tmp_path):
        record = _record(tmp_path, body="# Demo\n\nDo the thing.\n")
        block, meta = build_activation_block(record)
        assert "Skill: demo" in block
        assert "Do the thing." in block
        assert "When to use: When demoing" in block
        assert meta["skill_id"] == "t:demo"

    def test_references_resolved_from_body(self, tmp_path):
        record = _record(
            tmp_path,
            body=(
                "# Demo\n\nSee [notes](references/notes.md) and "
                "`assets/logo.png` for details.\n"
            ),
        )
        (record.base_dir / "references").mkdir()
        (record.base_dir / "references" / "notes.md").write_text(
            "the notes", encoding="utf-8"
        )
        (record.base_dir / "assets").mkdir()
        (record.base_dir / "assets" / "logo.png").write_text(
            "PNGDATA", encoding="utf-8"
        )
        block, meta = build_activation_block(record)
        assert "the notes" in block
        assert "PNGDATA" in block
        assert meta["references_resolved"] == [
            "references/notes.md",
            "assets/logo.png",
        ]
        assert meta["references_found"] == 2

    def test_missing_reference_skipped(self, tmp_path):
        record = _record(
            tmp_path,
            body="# Demo\n\nSee `references/missing.md`.\n",
        )
        block, meta = build_activation_block(record)
        # The path mention stays in the body text, but no reference section
        # is appended and nothing is marked as resolved.
        assert "--- reference:" not in block
        assert meta["references_resolved"] == []
        assert meta["references_found"] == 1

    def test_untrusted_never_resolves_references(self, tmp_path):
        record = _record(
            tmp_path,
            body="# Demo\n\nSee `references/secret.md`.\n",
            trust=TrustTier.UNTRUSTED,
        )
        (record.base_dir / "references").mkdir()
        (record.base_dir / "references" / "secret.md").write_text(
            "SECRET", encoding="utf-8"
        )
        block, meta = build_activation_block(record)
        assert "SECRET" not in block
        assert meta["references_resolved"] == []
        assert meta["trust"] == "untrusted"

    def test_activation_budget_truncates_with_marker(self, tmp_path):
        record = _record(tmp_path, body="# Demo\n\n" + "x" * 4000 + "\n")
        block, meta = build_activation_block(record, max_tokens=200)
        assert meta["truncated"] is True
        assert "TRUNCATED DUE TO TOKEN BUDGET" in block


class TestReferenceExtraction:
    def test_extracts_links_and_backticks(self):
        body = (
            "See [a](references/a.md), `docs/b.md`, [skip](https://x.com), `#anchor`."
        )
        assert extract_reference_paths(body) == ["references/a.md", "docs/b.md"]

    def test_dedupes_and_ignores_non_paths(self):
        body = "`a.md` `a.md` `plain` `/abs/path` `~/home`"
        assert extract_reference_paths(body) == ["a.md"]


class TestPromptBuilderSkillsSegment:
    def test_skills_segment_included(self):
        prompt, meta = build_system_prompt(
            base_system_prompt="BASE",
            skills_block="alpha — first skill",
            budgets={"skills_max_tokens": 1000},
        )
        assert "=== SKILLS ===" in prompt
        assert "alpha — first skill" in prompt
        segment = next(s for s in meta["segments"] if s["name"] == "skills")
        assert segment["estimated_tokens"] > 0
        assert segment["truncated"] is False

    def test_skills_budget_truncation_note(self):
        prompt, meta = build_system_prompt(
            base_system_prompt="BASE",
            skills_block="alpha — " + "x" * 2000,
            budgets=PromptBudgets(skills_max_tokens=10),
        )
        assert "TRUNCATED DUE TO TOKEN BUDGET" in prompt
        assert any(
            "skills segment truncated" in note for note in meta["truncation_notes"]
        )

    def test_skills_segment_ordered_before_scratchpad(self):
        prompt, meta = build_system_prompt(
            base_system_prompt="BASE",
            skills_block="SKILLS",
            scratchpad_block="SCRATCH",
        )
        assert prompt.index("=== SKILLS ===") < prompt.index("=== SCRATCHPAD ===")

    def test_skills_segment_cached_by_total_budget(self):
        prompt, meta = build_system_prompt(
            base_system_prompt="BASE",
            skills_block="alpha — a skill",
            budgets={"total_max_tokens": 4},  # base takes 1, skills needs 4
        )
        skills_segment = next(s for s in meta["segments"] if s["name"] == "skills")
        assert skills_segment["truncated"] is True
