"""Skill registry: in-memory index of discovered skills with cache invalidation.

Mirrors guardian.tools.registry.ToolRegistry's shape (load/list/get) so the
two registries feel native to each other. Discovery is expensive (filesystem
scan), so the registry caches parsed records and re-scans only when a known
skill's mtime changes or the set of candidate directories changes.

State-machine note (CLAUDE.md): the registry is startup-or-rescan state.
Per-request work (roster blocks, activation blocks) reads from it but never
writes to it. A rescan enqueued does not mean a rescan executed; callers
that need fresh data must call load() and use what it returns.
"""

from __future__ import annotations

import logging
import threading
from pathlib import Path

from guardian.skills.contracts import SkillRecord
from guardian.skills.discovery import ScanRoot, default_scan_roots, discover_skills

logger = logging.getLogger(__name__)


class SkillRegistry:
    """In-memory registry of discovered skills."""

    def __init__(self, roots: list[ScanRoot] | None = None) -> None:
        self._roots = roots
        self._skills_by_id: dict[str, SkillRecord] = {}
        self._skills_by_name: dict[str, list[SkillRecord]] = {}
        self._lock = threading.RLock()

    # -- loading -----------------------------------------------------------

    def load(self, *, force: bool = False) -> int:
        """Scan the configured roots and (re)build the index.

        Skips the filesystem scan when nothing has changed since the last
        load (same candidate dirs, same mtimes) unless force=True. Returns
        the number of registered skills after the load.
        """

        with self._lock:
            roots = self._roots if self._roots is not None else default_scan_roots()

            if not force and self._cache_is_valid(roots):
                return len(self._skills_by_id)

            records = discover_skills(roots)
            self._skills_by_id = {record.skill_id: record for record in records}
            self._skills_by_name = {}
            for record in records:
                self._skills_by_name.setdefault(record.name, []).append(record)

            self._last_roots = [
                (root.source_key, str(root.path), root.trust) for root in roots
            ]
            self._last_mtimes = {record.skill_id: record.mtime_ns for record in records}
            return len(self._skills_by_id)

    def _cache_is_valid(self, roots: list[ScanRoot]) -> bool:
        """True when root set and all known skill mtimes are unchanged.

        A quick stat-only probe: cheaper than re-parsing every SKILL.md.
        New candidate dirs are detected because an unchanged mtime map plus
        identical root set implies no new skills appeared inside them (any
        new skill would be a new dir with a new SKILL.md; the probe re-stats
        every candidate dir's entries).

        Implementation detail: this walks each root's entries and stats each
        SKILL.md, comparing against the cached map. Anything missing, added,
        or re-stamped invalidates.
        """

        current_roots = [
            (root.source_key, str(root.path), root.trust) for root in roots
        ]
        if current_roots != getattr(self, "_last_roots", None):
            return False
        if not self._skills_by_id:
            return False

        import os

        for root in roots:
            try:
                entries = list(os.scandir(root.path))
            except OSError:
                continue
            for entry in entries:
                if not entry.is_dir():
                    continue
                skill_file = Path(entry.path) / "SKILL.md"
                try:
                    mtime_ns = skill_file.stat().st_mtime_ns
                except OSError:
                    continue
                skill_id = f"{root.source_key}:{entry.name}"
                if self._last_mtimes.get(skill_id) != mtime_ns:
                    return False
                if skill_id not in self._skills_by_id:
                    return False
        return True

    # -- reads -------------------------------------------------------------

    def list(self) -> list[SkillRecord]:
        """All registered skills, in discovery (precedence) order."""

        with self._lock:
            return list(self._skills_by_id.values())

    def get(self, skill_id: str) -> SkillRecord | None:
        with self._lock:
            return self._skills_by_id.get(skill_id)

    def get_by_name(self, name: str) -> list[SkillRecord]:
        """All skills registered under a name (usually zero or one).

        Same-name skills in different scan roots coexist with distinct
        skill_ids; precedence order is preserved within the list.
        """

        with self._lock:
            return list(self._skills_by_name.get(name, []))

    def get_frontmatter_roster(self) -> list[str]:
        """Roster lines (name — description) for prompt injection."""

        with self._lock:
            return [record.roster_line() for record in self._skills_by_id.values()]

    def __len__(self) -> int:
        with self._lock:
            return len(self._skills_by_id)


_registry: SkillRegistry | None = None
_registry_lock = threading.Lock()


def get_skill_registry() -> SkillRegistry:
    """Process-wide default registry (scans default roots)."""

    global _registry
    with _registry_lock:
        if _registry is None:
            _registry = SkillRegistry()
        return _registry


def reset_skill_registry() -> None:
    """Test hook: drop the singleton so tests get isolated registries."""

    global _registry
    with _registry_lock:
        _registry = None
