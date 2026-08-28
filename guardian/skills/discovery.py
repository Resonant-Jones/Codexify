"""Multi-root skill discovery: scan, dedupe, and ingest SKILL.md directories.

Scans the standard locations used by other harnesses so migration into
Codexify requires zero steps — skills already on disk are simply found:

  project:  .agents/skills, .claude/skills, .cursor/skills,
            .codex/skills, .gemini/skills
  user:     ~/.agents/skills, ~/.claude/skills, ~/.codex/skills
  native:   guardian/skills (Codexify-owned)
  plugin:   guardian/plugins/*/skills

Precedence is scan-root order (first wins); the same physical skill
directory reached through two roots (e.g. symlinked) is discovered once,
attributed to the earlier root. Outside-repo scanning is on by default
(user decision, 2026-08-24) and can be disabled per call.

Trust tiers in v1 are provenance metadata, not behavioral gates:
LOCAL = Codexify-owned (native + plugins), IMPORTED = another harness's
directory (still local disk, still trusted reads). UNTRUSTED is reserved
for future MCP/remote sources.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import NamedTuple

from guardian.skills.contracts import SkillRecord, TrustTier
from guardian.skills.loader import parse_skill

logger = logging.getLogger(__name__)

_GUARDIAN_PACKAGE_ROOT = Path(__file__).resolve().parents[1]

# (source_key, path-under-project-root) for project-level harness dirs,
# in precedence order. `.agents` first: the neutral ecosystem default.
_PROJECT_HARNESS_ROOTS: tuple[tuple[str, str], ...] = (
    ("project:.agents", ".agents/skills"),
    ("project:.claude", ".claude/skills"),
    ("project:.cursor", ".cursor/skills"),
    ("project:.codex", ".codex/skills"),
    ("project:.gemini", ".gemini/skills"),
)

# (source_key, path-under-home) for user-global dirs.
_USER_HARNESS_ROOTS: tuple[tuple[str, str], ...] = (
    ("user:.agents", ".agents/skills"),
    ("user:.claude", ".claude/skills"),
    ("user:.codex", ".codex/skills"),
)

# Where Codexify's own skills live, anchored to the guardian package so the
# scanner works regardless of the process CWD.
NATIVE_SKILLS_DIR = _GUARDIAN_PACKAGE_ROOT / "skills"


class ScanRoot(NamedTuple):
    """One directory to scan for skill-name/SKILL.md entries."""

    source_key: str
    path: Path
    trust: TrustTier


def default_scan_roots(
    project_root: Path | None = None,
    *,
    include_user_dirs: bool = True,
    home: Path | None = None,
) -> list[ScanRoot]:
    """Build the standard scan-root list in precedence order.

    Args:
        project_root: root for project-level harness dirs (default: CWD).
        include_user_dirs: also scan user-global dirs (default True).
        home: override for the user's home (tests); default Path.home().
    """

    root = (project_root or Path.cwd()).resolve()
    user_home = (home or Path.home()).resolve()

    roots: list[ScanRoot] = []

    for source_key, rel in _PROJECT_HARNESS_ROOTS:
        roots.append(ScanRoot(source_key, root / rel, TrustTier.IMPORTED))

    if include_user_dirs:
        for source_key, rel in _USER_HARNESS_ROOTS:
            roots.append(ScanRoot(source_key, user_home / rel, TrustTier.IMPORTED))

    roots.append(ScanRoot("project:native", NATIVE_SKILLS_DIR, TrustTier.LOCAL))

    plugins_root = _GUARDIAN_PACKAGE_ROOT / "plugins"
    if plugins_root.is_dir():
        for entry in sorted(plugins_root.iterdir()):
            skills_dir = entry / "skills"
            if skills_dir.is_dir():
                roots.append(
                    ScanRoot(f"plugin:{entry.name}", skills_dir, TrustTier.LOCAL)
                )

    return roots


def discover_skills(roots: list[ScanRoot]) -> list[SkillRecord]:
    """Scan all roots and return parsed skills in precedence order.

    Missing roots are skipped silently. Malformed skills log a warning and
    are skipped without aborting the scan. Physical duplicates (same real
    SKILL.md path via different roots) resolve to the earliest root.
    """

    records: list[SkillRecord] = []
    seen_real_paths: set[str] = set()

    for root in roots:
        try:
            entries = sorted(os.scandir(root.path), key=lambda e: e.name)
        except OSError:
            continue  # root missing or unreadable — normal, not an error

        for entry in entries:
            if not entry.is_dir():
                continue

            skill_dir = Path(entry.path)
            skill_file = skill_dir / "SKILL.md"
            try:
                real_path = str(skill_file.resolve())
            except OSError:
                continue

            if real_path in seen_real_paths:
                continue

            record = parse_skill(
                skill_dir, source_key=root.source_key, trust=root.trust
            )
            if record is None:
                continue  # parse_skill already logged the reason

            seen_real_paths.add(real_path)
            records.append(record)

    return records
