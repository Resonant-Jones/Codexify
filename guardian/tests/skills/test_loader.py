"""Tests for guardian.skills loader and contracts (Phase 1).

Covers: frontmatter splitting, tolerant unknown-field preservation, name/
description fallbacks and truncation, malformed-YAML skip, path confinement
for reference files, and the real marketing skill in guardian/skills/.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from guardian.skills.contracts import MAX_NAME_LENGTH, SkillRecord, TrustTier
from guardian.skills.loader import (
    estimate_tokens,
    load_reference_file,
    load_skill_body,
    parse_skill,
    split_frontmatter,
)

REPO_ROOT = Path(__file__).resolve().parents[3]
REAL_MARKETING_SKILL = REPO_ROOT / "guardian" / "skills" / "marketing"


def _write_skill(
    root: Path,
    name: str = "demo",
    frontmatter: str = "name: demo\ndescription: A demo skill\n",
    body: str = "# Demo\n\nDo the thing.\n",
) -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\n{frontmatter}---\n\n{body}", encoding="utf-8"
    )
    return skill_dir


class TestSplitFrontmatter:
    def test_no_frontmatter(self):
        fm, body = split_frontmatter("# Just a body\n")
        assert fm == {}
        assert body == "# Just a body\n"

    def test_standard_block(self):
        raw = "---\nname: x\ndescription: y\n---\n\nBody here\n"
        fm, body = split_frontmatter(raw)
        assert fm == {"name": "x", "description": "y"}
        assert body == "\nBody here"  # splitlines drops the trailing newline

    def test_unclosed_block_returns_untouched(self):
        raw = "---\nname: x\nno closing delimiter"
        fm, body = split_frontmatter(raw)
        assert fm == {}
        assert body == raw

    def test_empty_frontmatter(self):
        raw = "---\n---\n\nBody\n"
        fm, body = split_frontmatter(raw)
        assert fm == {}
        assert body == "\nBody"

    def test_malformed_yaml_raises(self):
        raw = "---\nname: [unclosed\n---\n\nBody\n"
        with pytest.raises(Exception):
            split_frontmatter(raw)


class TestParseSkill:
    def test_standard_skill(self, tmp_path):
        skill_dir = _write_skill(tmp_path)
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        assert record.name == "demo"
        assert record.description == "A demo skill"
        assert record.trust == TrustTier.LOCAL
        assert record.source_key == "test"
        assert record.skill_id == "test:demo"
        assert record.body_tokens > 0
        assert record.frontmatter_tokens > 0
        assert record.mtime_ns > 0

    def test_unknown_frontmatter_preserved_and_ignored(self, tmp_path):
        skill_dir = _write_skill(
            tmp_path,
            frontmatter=(
                "name: demo\ndescription: A demo\n"
                "allowed-tools: [Bash, FileEdit]\n"
                "context: fork\n"
                "some-future-field: 42\n"
            ),
        )
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.IMPORTED)
        assert record is not None
        assert "allowed-tools" in record.raw_frontmatter
        assert record.raw_frontmatter["context"] == "fork"
        assert "name" not in record.raw_frontmatter  # known fields stripped

    def test_name_falls_back_to_directory_name(self, tmp_path):
        skill_dir = _write_skill(
            tmp_path,
            name="fallback-dir",
            frontmatter="description: described\n",
        )
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        assert record.name == "fallback-dir"

    def test_description_falls_back_when_missing(self, tmp_path):
        skill_dir = _write_skill(tmp_path, name="nodesc", frontmatter="name: nodesc\n")
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        assert "no description" in record.description

    def test_malformed_yaml_skips_with_none(self, tmp_path):
        skill_dir = _write_skill(tmp_path, frontmatter="name: [unclosed\n")
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is None

    def test_missing_file_returns_none(self, tmp_path):
        empty_dir = tmp_path / "ghost"
        empty_dir.mkdir()
        assert parse_skill(empty_dir, source_key="test", trust=TrustTier.LOCAL) is None

    def test_overlong_name_truncated(self, tmp_path):
        long_name = "x" * (MAX_NAME_LENGTH + 10)
        skill_dir = _write_skill(
            tmp_path, frontmatter=f"name: {long_name}\ndescription: d\n"
        )
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        assert len(record.name) == MAX_NAME_LENGTH

    def test_scalar_frontmatter_not_mapping_skips(self, tmp_path):
        skill_dir = _write_skill(tmp_path, frontmatter="just a string\n")
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is None


class TestBodiesAndReferences:
    def test_load_body_roundtrip(self, tmp_path):
        skill_dir = _write_skill(tmp_path)
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        body = load_skill_body(record)
        assert "# Demo" in body
        assert "name: demo" not in body  # frontmatter stripped

    def test_reference_file_within_base_dir(self, tmp_path):
        skill_dir = _write_skill(tmp_path)
        (skill_dir / "references").mkdir()
        (skill_dir / "references" / "notes.md").write_text(
            "reference content", encoding="utf-8"
        )
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        content = load_reference_file(record, "references/notes.md")
        assert content == "reference content"

    def test_reference_path_traversal_rejected(self, tmp_path):
        skill_dir = _write_skill(tmp_path)
        record = parse_skill(skill_dir, source_key="test", trust=TrustTier.LOCAL)
        assert record is not None
        with pytest.raises(ValueError):
            load_reference_file(record, "../../etc/passwd")


class TestTokenEstimation:
    def test_empty_is_zero(self):
        assert estimate_tokens("") == 0

    def test_positive_for_content(self):
        assert estimate_tokens("hello world") == 3

    def test_matches_roster_line_shape(self):
        # Roster lines are name — description; both contribute tokens.
        assert estimate_tokens("demo — A demo skill") >= 4


class TestRealMarketingSkill:
    """The one skill that already exists in the repo — must parse clean."""

    @pytest.mark.skipif(
        not REAL_MARKETING_SKILL.is_dir(),
        reason="guardian/skills/marketing not present",
    )
    def test_marketing_skill_parses(self):
        record = parse_skill(
            REAL_MARKETING_SKILL,
            source_key="project:native",
            trust=TrustTier.LOCAL,
        )
        assert record is not None, "marketing SKILL.md failed to parse"
        assert record.name == "marketing"
        assert "Codexify" in record.description or record.description
        assert record.body_tokens > 100  # it's a substantial skill
        assert record.base_dir.name == "marketing"
        # templates/ sidecar exists and is reachable as a reference
        template = load_reference_file(record, "templates/core-brief.md")
        assert template  # non-empty

    @pytest.mark.skipif(
        not REAL_MARKETING_SKILL.is_dir(),
        reason="guardian/skills/marketing not present",
    )
    def test_marketing_roster_line(self):
        record = parse_skill(
            REAL_MARKETING_SKILL,
            source_key="project:native",
            trust=TrustTier.LOCAL,
        )
        assert record is not None
        line = record.roster_line()
        assert line.startswith("marketing")


class TestContractModel:
    def test_skill_record_rejects_extra_fields(self):
        with pytest.raises(Exception):
            SkillRecord(
                skill_id="t:x",
                name="x",
                description="d",
                body_path="/tmp/x",
                base_dir="/tmp/x",
                trust=TrustTier.LOCAL,
                source_key="t",
                frontmatter_tokens=1,
                body_tokens=1,
                mtime_ns=1,
                sneaky_field="no",
            )
