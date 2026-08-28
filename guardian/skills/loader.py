"""SKILL.md loader: parse frontmatter + body into SkillRecords.

Standard: Agent Skills open format — skill-name/SKILL.md with YAML
frontmatter (name, description) and a markdown body. Unknown frontmatter
fields are preserved in raw_frontmatter and ignored (tolerant reading).
Malformed files log a warning and are skipped — never crash discovery.
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

import yaml

from guardian.skills.contracts import (
    MAX_DESCRIPTION_LENGTH,
    MAX_NAME_LENGTH,
    SkillRecord,
    TrustTier,
)

logger = logging.getLogger(__name__)

SKILL_FILENAME = "SKILL.md"


def estimate_tokens(text: str) -> int:
    """Conservative token estimate using the repo-standard heuristic.

    Mirrors guardian.cognition.modular_prompt_builder.estimate_tokens so
    skills budget accounting is consistent with the rest of prompt assembly.
    """

    if not text:
        return 0
    return max(1, -(-len(text) // 4))  # ceil division without math import


def split_frontmatter(raw: str) -> tuple[dict[str, Any], str]:
    """Split a markdown document into (frontmatter_dict, body).

    Returns ({}, raw) when there is no well-formed frontmatter block.
    Malformed YAML raises yaml.YAMLError, caught by the caller (parse_skill).
    """

    if not raw.startswith("---"):
        return {}, raw

    lines = raw.splitlines()
    if len(lines) < 3:
        return {}, raw

    end_index = None
    for idx in range(1, len(lines)):
        if lines[idx].strip() == "---":
            end_index = idx
            break

    if end_index is None:
        return {}, raw

    frontmatter_raw = "\n".join(lines[1:end_index])
    body = "\n".join(lines[end_index + 1 :])
    data = yaml.safe_load(frontmatter_raw) if frontmatter_raw.strip() else {}
    if data is None:
        data = {}
    return data, body


def _clean_name(raw: Any) -> str | None:
    if raw is None:
        return None
    value = str(raw).strip()
    if not value:
        return None
    if len(value) > MAX_NAME_LENGTH:
        logger.warning("Skill name exceeds %d chars, truncating.", MAX_NAME_LENGTH)
        value = value[:MAX_NAME_LENGTH]
    return value


def _clean_description(raw: Any, fallback: str) -> str:
    if raw is None:
        return fallback
    value = str(raw).strip()
    if not value:
        return fallback
    if len(value) > MAX_DESCRIPTION_LENGTH:
        logger.warning(
            "Skill description exceeds %d chars, truncating.",
            MAX_DESCRIPTION_LENGTH,
        )
        value = value[:MAX_DESCRIPTION_LENGTH]
    return value


def parse_skill(
    skill_dir: Path,
    *,
    source_key: str,
    trust: TrustTier,
) -> SkillRecord | None:
    """Parse skill_dir/SKILL.md into a SkillRecord.

    Returns None (with a logged warning) when the file is missing,
    unreadable, or malformed. Never raises for content problems.
    """

    skill_path = skill_dir / SKILL_FILENAME
    try:
        raw = skill_path.read_text(encoding="utf-8")
        mtime_ns = skill_path.stat().st_mtime_ns
    except OSError as exc:
        logger.warning("Skill unreadable at %s: %s", skill_path, exc)
        return None

    try:
        frontmatter, body = split_frontmatter(raw)
    except yaml.YAMLError as exc:
        logger.warning("Skill %s has malformed YAML frontmatter: %s", skill_path, exc)
        return None

    if not isinstance(frontmatter, dict):
        logger.warning(
            "Skill %s frontmatter is not a mapping (got %s); skipping.",
            skill_path,
            type(frontmatter).__name__,
        )
        return None

    name = _clean_name(frontmatter.get("name")) or skill_dir.name
    description = _clean_description(
        frontmatter.get("description"),
        fallback=f"Skill '{skill_dir.name}' (no description)",
    )
    when_to_use_raw = frontmatter.get("when_to_use")
    when_to_use = (
        str(when_to_use_raw).strip() or None if when_to_use_raw is not None else None
    )

    known = {"name", "description", "when_to_use"}
    raw_frontmatter = {
        key: value for key, value in frontmatter.items() if key not in known
    }

    frontmatter_text = " ".join(
        part for part in (name, description, when_to_use or "") if part
    )

    return SkillRecord(
        skill_id=f"{source_key}:{name}",
        name=name,
        description=description,
        when_to_use=when_to_use,
        body_path=skill_path,
        base_dir=skill_dir.resolve(),
        trust=trust,
        source_key=source_key,
        frontmatter_tokens=estimate_tokens(frontmatter_text),
        body_tokens=estimate_tokens(body),
        mtime_ns=mtime_ns,
        raw_frontmatter=raw_frontmatter,
    )


def load_skill_body(record: SkillRecord) -> str:
    """Read and return a skill's markdown body (fresh, uncached).

    Raises OSError on read failure; callers decide how to surface that.
    """

    raw = record.body_path.read_text(encoding="utf-8")
    _, body = split_frontmatter(raw)
    return body


def load_reference_file(record: SkillRecord, relative_path: str) -> str:
    """Read a file from the skill's directory, confined to base_dir.

    Path traversal outside base_dir raises ValueError.
    """

    base = record.base_dir.resolve()
    candidate = (base / relative_path).resolve()
    if not candidate.is_relative_to(base):
        raise ValueError(
            f"Reference path {relative_path!r} escapes skill directory "
            f"{record.base_dir}"
        )
    return candidate.read_text(encoding="utf-8")
