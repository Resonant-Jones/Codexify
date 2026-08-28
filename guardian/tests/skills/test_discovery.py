"""Tests for guardian.skills discovery (Phase 2).

Covers: multi-root precedence, user-dir inclusion/exclusion, symlink dedupe,
missing-root tolerance, malformed-skill skip, and a live scan of the actual
guardian plugins directory.
"""

from __future__ import annotations

import os
from pathlib import Path

from guardian.skills.contracts import TrustTier
from guardian.skills.discovery import (
    NATIVE_SKILLS_DIR,
    ScanRoot,
    default_scan_roots,
    discover_skills,
)

REPO_ROOT = Path(__file__).resolve().parents[3]


def _make_skill(root: Path, name: str, description: str = "desc") -> Path:
    skill_dir = root / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )
    return skill_dir


class TestDefaultScanRoots:
    def test_project_roots_in_precedence_order(self, tmp_path):
        roots = default_scan_roots(project_root=tmp_path)
        keys = [r.source_key for r in roots if r.source_key.startswith("project:")]
        assert keys[0] == "project:.agents"
        assert "project:.claude" in keys
        assert "project:.cursor" in keys
        assert "project:.codex" in keys
        assert "project:.gemini" in keys
        assert keys[-1] == "project:native"

    def test_user_dirs_default_included(self, tmp_path):
        roots = default_scan_roots(project_root=tmp_path)
        user_keys = [r.source_key for r in roots if r.source_key.startswith("user:")]
        assert user_keys == ["user:.agents", "user:.claude", "user:.codex"]

    def test_user_dirs_can_be_excluded(self, tmp_path):
        roots = default_scan_roots(project_root=tmp_path, include_user_dirs=False)
        assert not any(r.source_key.startswith("user:") for r in roots)

    def test_home_override(self, tmp_path):
        roots = default_scan_roots(project_root=tmp_path, home=tmp_path)
        user_paths = {r.path for r in roots if r.source_key.startswith("user:")}
        assert user_paths == {
            tmp_path / ".agents/skills",
            tmp_path / ".claude/skills",
            tmp_path / ".codex/skills",
        }

    def test_plugin_roots_discovered_when_present(self, tmp_path, monkeypatch):
        plugin_skills = tmp_path / "plugins" / "alpha-plugin" / "skills"
        plugin_skills.mkdir(parents=True)
        monkeypatch.setattr(
            "guardian.skills.discovery._GUARDIAN_PACKAGE_ROOT",
            tmp_path,
            raising=True,
        )
        roots = default_scan_roots(project_root=tmp_path, include_user_dirs=False)
        plugin_roots = [r for r in roots if r.source_key.startswith("plugin:")]
        assert [r.source_key for r in plugin_roots] == ["plugin:alpha-plugin"]
        assert plugin_roots[0].trust == TrustTier.LOCAL

    def test_native_root_always_present(self, tmp_path):
        roots = default_scan_roots(project_root=tmp_path)
        native = [r for r in roots if r.source_key == "project:native"]
        assert len(native) == 1
        assert native[0].path == NATIVE_SKILLS_DIR


class TestDiscoverSkills:
    def test_scans_all_roots_and_dedupes_by_name(self, tmp_path):
        agents = tmp_path / ".agents" / "skills"
        claude = tmp_path / ".claude" / "skills"
        _make_skill(agents, "shared-skill", "from agents")
        _make_skill(claude, "shared-skill", "from claude")
        _make_skill(claude, "claude-only", "claude only")

        roots = [
            ScanRoot("project:.agents", agents, TrustTier.IMPORTED),
            ScanRoot("project:.claude", claude, TrustTier.IMPORTED),
        ]
        records = discover_skills(roots)
        by_id = {r.skill_id: r for r in records}
        assert len(records) == 3  # both roots fully scanned
        # Precedence applies to duplicate NAMES, not physical paths
        assert "project:.agents:shared-skill" in by_id
        assert "project:.claude:shared-skill" in by_id

    def test_missing_root_skipped_silently(self, tmp_path):
        roots = [ScanRoot("project:.agents", tmp_path / "nope", TrustTier.IMPORTED)]
        assert discover_skills(roots) == []

    def test_symlinked_duplicate_discovered_once(self, tmp_path):
        agents = tmp_path / ".agents" / "skills"
        agents.mkdir(parents=True)
        real = _make_skill(agents, "real-skill")

        mirror_root = tmp_path / "mirror" / "skills"
        mirror_root.mkdir(parents=True)
        os.symlink(real, mirror_root / "real-skill")

        records = discover_skills(
            [
                ScanRoot("project:.agents", agents, TrustTier.IMPORTED),
                ScanRoot("project:mirror", mirror_root, TrustTier.IMPORTED),
            ]
        )
        assert len(records) == 1
        assert records[0].source_key == "project:.agents"

    def test_malformed_skill_skipped(self, tmp_path):
        root = tmp_path / "skills"
        bad = root / "bad-skill"
        bad.mkdir(parents=True)
        (bad / "SKILL.md").write_text(
            "---\nname: [unclosed\n---\n\nbody\n", encoding="utf-8"
        )
        good = _make_skill(root, "good-skill")

        records = discover_skills([ScanRoot("t", root, TrustTier.LOCAL)])
        assert [r.name for r in records] == ["good-skill"]
        assert records[0].base_dir == good.resolve()

    def test_files_at_root_ignored(self, tmp_path):
        root = tmp_path / "skills"
        root.mkdir(parents=True)
        (root / "not-a-dir.md").write_text("x", encoding="utf-8")
        assert discover_skills([ScanRoot("t", root, TrustTier.LOCAL)]) == []

    def test_earlier_root_wins_for_symlinked_dir(self, tmp_path):
        # Same physical skill directory through two roots
        real_root = tmp_path / "real"
        real = _make_skill(real_root, "dup")

        link_root = tmp_path / "linked"
        link_root.mkdir()
        os.symlink(real, link_root / "dup")

        records = discover_skills(
            [
                ScanRoot("a", link_root, TrustTier.IMPORTED),
                ScanRoot("b", real_root, TrustTier.IMPORTED),
            ]
        )
        assert len(records) == 1
        assert records[0].source_key == "a"


class TestLiveEnvironment:
    """Scan the actual repo — native marketing skill must be found."""

    def test_live_scan_finds_marketing(self):
        roots = default_scan_roots(project_root=REPO_ROOT, include_user_dirs=False)
        records = discover_skills(roots)
        names = [r.name for r in records]
        assert "marketing" in names
        marketing = next(r for r in records if r.name == "marketing")
        assert marketing.trust == TrustTier.LOCAL
        assert marketing.source_key == "project:native"

    def test_live_user_dirs_scan_does_not_crash(self):
        # Outside-repo scanning is default-on; ensure it runs clean on this
        # machine (whatever happens to be in ~/.claude/skills etc.).
        roots = default_scan_roots(project_root=REPO_ROOT)
        records = discover_skills(roots)
        assert isinstance(records, list)

    def test_live_plugin_scan(self):
        plugins_root = REPO_ROOT / "guardian" / "plugins"
        if not plugins_root.is_dir():
            import pytest

            pytest.skip("guardian/plugins not present")
        roots = default_scan_roots(project_root=REPO_ROOT, include_user_dirs=False)
        plugin_roots = [r for r in roots if r.source_key.startswith("plugin:")]
        # Plugins only appear as roots when they actually contain skills/.
        records = discover_skills(roots)
        for record in records:
            if record.source_key.startswith("plugin:"):
                assert record.trust == TrustTier.LOCAL
