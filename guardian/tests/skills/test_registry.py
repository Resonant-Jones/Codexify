"""Tests for guardian.skills registry (Phase 3).

Covers: load/list/get round-trip, name-collision coexistence, cache
invalidation on mtime change and root change, and singleton lifecycle.
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

from guardian.skills.contracts import TrustTier
from guardian.skills.discovery import ScanRoot
from guardian.skills.registry import (
    SkillRegistry,
    get_skill_registry,
    reset_skill_registry,
)


def _make_skill(root: Path, name: str, description: str = "d") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


@pytest.fixture(autouse=True)
def _isolate_singleton():
    reset_skill_registry()
    yield
    reset_skill_registry()


class TestRegistryBasics:
    def test_load_list_get_roundtrip(self, tmp_path):
        root = tmp_path / "skills"
        _make_skill(root, "alpha")
        _make_skill(root, "beta")

        registry = SkillRegistry(roots=[ScanRoot("t", root, TrustTier.LOCAL)])
        count = registry.load()
        assert count == 2
        assert len(registry) == 2

        alpha = registry.get("t:alpha")
        assert alpha is not None
        assert alpha.name == "alpha"

        names = [r.name for r in registry.list()]
        assert names == ["alpha", "beta"]  # discovery order (sorted)

    def test_get_missing_returns_none(self, tmp_path):
        registry = SkillRegistry(roots=[ScanRoot("t", tmp_path, TrustTier.LOCAL)])
        registry.load()
        assert registry.get("t:nope") is None

    def test_name_collision_coexists(self, tmp_path):
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        _make_skill(root_a, "same", "from a")
        _make_skill(root_b, "same", "from b")

        registry = SkillRegistry(
            roots=[
                ScanRoot("a", root_a, TrustTier.IMPORTED),
                ScanRoot("b", root_b, TrustTier.IMPORTED),
            ]
        )
        registry.load()
        assert len(registry) == 2
        both = registry.get_by_name("same")
        assert [r.source_key for r in both] == ["a", "b"]

    def test_roster_lines(self, tmp_path):
        root = tmp_path / "skills"
        _make_skill(root, "alpha", "first skill")
        registry = SkillRegistry(roots=[ScanRoot("t", root, TrustTier.LOCAL)])
        registry.load()
        assert registry.get_frontmatter_roster() == ["alpha — first skill"]


class TestCacheInvalidation:
    def test_cached_load_skips_rescan(self, tmp_path):
        root = tmp_path / "skills"
        _make_skill(root, "alpha")

        registry = SkillRegistry(roots=[ScanRoot("t", root, TrustTier.LOCAL)])
        assert registry.load() == 1

        # Add a skill WITHOUT forcing: cache probe stats candidate dirs,
        # sees the new SKILL.md is unknown, and rescans.
        _make_skill(root, "beta")
        assert registry.load() == 2

    def test_mtime_change_invalidates(self, tmp_path):
        root = tmp_path / "skills"
        skill_dir = _make_skill(root, "alpha")

        registry = SkillRegistry(roots=[ScanRoot("t", root, TrustTier.LOCAL)])
        registry.load()
        record = registry.get("t:alpha")
        assert record is not None
        original_mtime = record.mtime_ns

        # Ensure a different mtime_ns (some filesystems have coarse stamps)
        time.sleep(0.01)
        (skill_dir / "SKILL.md").write_text(
            "---\nname: alpha\ndescription: updated\n---\n\n# alpha\n",
            encoding="utf-8",
        )
        os.utime(skill_dir / "SKILL.md")

        registry.load()
        updated = registry.get("t:alpha")
        assert updated is not None
        assert updated.description == "updated"
        assert updated.mtime_ns != original_mtime

    def test_root_change_invalidates(self, tmp_path):
        root_a = tmp_path / "a"
        root_b = tmp_path / "b"
        _make_skill(root_a, "alpha")
        _make_skill(root_b, "beta")

        registry = SkillRegistry(roots=[ScanRoot("a", root_a, TrustTier.LOCAL)])
        assert registry.load() == 1

        registry._roots = [ScanRoot("b", root_b, TrustTier.LOCAL)]
        assert registry.load() == 1
        assert registry.get("b:beta") is not None
        assert registry.get("a:alpha") is None

    def test_force_rescan(self, tmp_path):
        root = tmp_path / "skills"
        _make_skill(root, "alpha")
        registry = SkillRegistry(roots=[ScanRoot("t", root, TrustTier.LOCAL)])
        registry.load()

        # Corrupt the cached index directly. The cache probe detects the
        # inconsistency (known mtime but missing from the index) and
        # self-heals on the next load() — even without force.
        registry._skills_by_id.pop("t:alpha")
        assert registry.load() == 1  # probe caught it and rescanned
        assert registry.get("t:alpha") is not None
        assert registry.load(force=True) == 1  # force also rebuilds


class TestSingleton:
    def test_singleton_identity(self):
        first = get_skill_registry()
        second = get_skill_registry()
        assert first is second

    def test_reset_clears_singleton(self):
        first = get_skill_registry()
        reset_skill_registry()
        second = get_skill_registry()
        assert first is not second


class TestLiveRegistry:
    def test_default_roots_find_marketing(self):
        import pathlib

        repo_root = pathlib.Path(__file__).resolve().parents[3]
        registry = SkillRegistry(
            roots=[
                root
                for root in (
                    ScanRoot(
                        "project:native",
                        repo_root / "guardian" / "skills",
                        TrustTier.LOCAL,
                    ),
                )
            ]
        )
        registry.load()
        assert registry.get("project:native:marketing") is not None
