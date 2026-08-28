"""Canonical contracts for the Guardian skills system.

A SkillRecord is the parsed, validated form of a skill-name/SKILL.md file
(Agent Skills open standard). Unknown frontmatter fields are preserved in
raw_frontmatter and ignored — tolerant reading, no private dialect.
"""

from __future__ import annotations

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

# Frontmatter fields defined by the open standard.
STANDARD_FRONTMATTER_FIELDS = frozenset(
    {
        "name",
        "description",
        "license",
        "metadata",
        "compatibility",
        "allowed-tools",
        "when_to_use",
    }
)

# Max lengths from the Agent Skills standard (verified 2026-06-07).
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024


class TrustTier(str, Enum):
    """How much authority a skill's content gets in prompt assembly."""

    LOCAL = "local"  # guardian/skills/, project dirs — trusted
    IMPORTED = "imported"  # scanned from other harnesses — trusted read
    UNTRUSTED = "untrusted"  # MCP or remote — verbatim injection only


class SkillRecord(BaseModel):
    """One discovered skill, parsed from SKILL.md."""

    model_config = ConfigDict(extra="forbid")

    skill_id: str = Field(min_length=1, max_length=256)
    name: str = Field(min_length=1, max_length=MAX_NAME_LENGTH)
    description: str = Field(max_length=MAX_DESCRIPTION_LENGTH)
    when_to_use: str | None = Field(default=None, max_length=2048)
    body_path: Path
    base_dir: Path
    trust: TrustTier
    source_key: str = Field(min_length=1, max_length=128)
    frontmatter_tokens: int = Field(ge=0)
    body_tokens: int = Field(ge=0)
    mtime_ns: int = Field(ge=0)
    raw_frontmatter: dict = Field(default_factory=dict)

    def roster_line(self) -> str:
        """One-line roster entry: name — description."""
        if self.description:
            return f"{self.name} — {self.description}"
        return self.name
