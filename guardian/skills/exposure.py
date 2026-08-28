"""Skill exposure: roster block (progressive disclosure) + activation block.

Roster block
    Frontmatter-only lines (name — description) injected into the system
    prompt so the model knows skills exist without paying body tokens.
    Line-level trimming: whole lines are dropped from the end until the
    budget fits — never a half-rendered roster line.

Activation block
    Full body + resolved reference files, produced on skill invocation.
    References are markdown-link targets and backticked paths that resolve
    within the skill's base_dir. UNTRUSTED skills get the verbatim body with
    NO reference resolution (remote content is injected or nothing — never
    interpreted).

Neither block ever executes anything. Execution authority stays with the
sandbox/permission layer (see design doc §6).
"""

from __future__ import annotations

import re
from typing import Any

from guardian.cognition.modular_prompt_builder import estimate_tokens
from guardian.skills.contracts import SkillRecord, TrustTier
from guardian.skills.loader import load_reference_file, load_skill_body

DEFAULT_ROSTER_MAX_TOKENS = 1000
DEFAULT_ACTIVATION_MAX_TOKENS = 4000

_ROSTER_HEADER = "Available skills:"
_ROSTER_FOOTER = "To activate a skill, invoke the skill_invocation tool with its name."

# Markdown link targets: [text](target)
_LINK_RE = re.compile(r"\]\(([^)#\s][^)#]*?)\)")
# Backticked paths: `path/to/file`
_BACKTICK_RE = re.compile(r"`([^`\s]+)`")
# Anything that is not a local relative path
_NON_LOCAL_PREFIXES = ("http://", "https://", "mailto:", "#", "/", "~")


def _is_local_relative_path(candidate: str) -> bool:
    candidate = candidate.strip().removeprefix("./")
    if not candidate or candidate.startswith(_NON_LOCAL_PREFIXES):
        return False
    if "://" in candidate or candidate.startswith(("#", "/", "~")):
        return False
    # Must look like a path: contains a separator or a known extension
    return "." in candidate or "/" in candidate


def extract_reference_paths(body: str) -> list[str]:
    """Relative file paths mentioned in a skill body, in order, deduped.

    Sources: markdown link targets and backticked code spans. External URLs,
    anchors, and absolute paths are excluded. The caller resolves each
    candidate against the skill's base_dir (load_reference_file enforces
    confinement).
    """

    seen: set[str] = set()
    paths: list[str] = []
    for raw in _LINK_RE.findall(body) + _BACKTICK_RE.findall(body):
        candidate = raw.strip().removeprefix("./").split("#")[0]
        if not _is_local_relative_path(candidate):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        paths.append(candidate)
    return paths


def _fit_lines_to_budget(
    header: str, lines: list[str], max_tokens: int | None
) -> tuple[str, int]:
    """Join header + lines, dropping whole lines from the end to fit.

    Returns (block_text, dropped_line_count). max_tokens=None means no cap.
    """

    if not lines:
        return "", 0

    if max_tokens is None:
        return f"{header}\n" + "\n".join(lines), 0

    budget = max(0, int(max_tokens))
    kept = list(lines)
    dropped = 0

    # Drop whole lines until the joined block fits (header is required).
    while kept and estimate_tokens(f"{header}\n" + "\n".join(kept)) > budget:
        kept.pop()
        dropped += 1

    if not kept:
        # Header alone must fit; if even that is impossible, return empty.
        if estimate_tokens(header) > budget:
            return "", dropped
        return header, dropped

    return f"{header}\n" + "\n".join(kept), dropped


def build_roster_block(
    records: list[SkillRecord],
    *,
    max_tokens: int | None = DEFAULT_ROSTER_MAX_TOKENS,
) -> tuple[str, dict[str, Any]]:
    """Build the system-prompt roster block for the given skills.

    Returns (block_text, meta) where meta carries token counts and how many
    lines were dropped for budget. Empty input yields ("", {}).
    """

    if not records:
        return "", {}

    lines = [record.roster_line() for record in records]
    header = f"{_ROSTER_HEADER}\n{_ROSTER_FOOTER}"

    # Footer must survive budget trimming; keep it attached to the header.
    block, dropped = _fit_lines_to_budget(header, lines, max_tokens)

    meta: dict[str, Any] = {
        "skill_count": len(records),
        "lines_included": len(lines) - dropped,
        "lines_dropped": dropped,
        "estimated_tokens": estimate_tokens(block),
        "truncated": dropped > 0,
    }
    return block, meta


def build_activation_block(
    record: SkillRecord,
    *,
    max_tokens: int | None = DEFAULT_ACTIVATION_MAX_TOKENS,
) -> tuple[str, dict[str, Any]]:
    """Build the activation block (body + resolved references) for a skill.

    Returns (block_text, meta). Reference files are resolved only for
    trusted tiers; UNTRUSTED skills inject the verbatim body with no
    reference resolution and no path interpretation.
    """

    body = load_skill_body(record)

    header_lines = [f"Skill: {record.name}"]
    if record.description:
        header_lines.append(record.description)
    if record.when_to_use:
        header_lines.append(f"When to use: {record.when_to_use}")
    header = "\n".join(header_lines)

    parts: list[str] = [header, body]
    refs_resolved: list[str] = []

    if record.trust is not TrustTier.UNTRUSTED:
        for rel in extract_reference_paths(body):
            try:
                content = load_reference_file(record, rel)
            except (OSError, ValueError):
                continue
            refs_resolved.append(rel)
            parts.append(f"--- reference: {rel} ---\n{content}")

    combined = "\n\n".join(parts)

    if max_tokens is None:
        block, truncated = combined, False
    else:
        budget = max(0, int(max_tokens))
        if estimate_tokens(combined) <= budget:
            block, truncated = combined, False
        else:
            max_chars = budget * 4
            marker = "\n[TRUNCATED DUE TO TOKEN BUDGET]"
            if max_chars <= len(marker):
                block, truncated = marker[:max_chars], True
            else:
                block = combined[: max_chars - len(marker)].rstrip() + marker
                truncated = True

    meta: dict[str, Any] = {
        "skill_id": record.skill_id,
        "trust": record.trust.value,
        "references_found": len(extract_reference_paths(body)),
        "references_resolved": refs_resolved,
        "estimated_tokens": estimate_tokens(block),
        "truncated": truncated,
    }
    return block, meta


__all__ = [
    "build_activation_block",
    "build_roster_block",
    "extract_reference_paths",
    "DEFAULT_ACTIVATION_MAX_TOKENS",
    "DEFAULT_ROSTER_MAX_TOKENS",
]
