"""Task Prompt Archive — normalize scraper artifacts into a structured archive.

Reads scraper JSON+MD artifacts and conversation index, produces
a canonical JSON+CSV+MD task prompt archive. No DB, no models, no mutations.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# --- Section extraction ---

# Mapping: canonical_section_name → list of heading patterns
_SECTION_MAP: list[tuple[str, list[str]]] = [
    ("title", ["Task Title", "Title"]),
    ("objective", ["Objective", "Goal", "Task"]),
    ("context", ["Context", "Background"]),
    (
        "requirements",
        [
            "Requirements",
            "Constraints",
            "Required behavior",
            "Non-Negotiable Constraints",
            "Requirements:",
        ],
    ),
    (
        "instructions",
        [
            "Instructions",
            "Implementation Scope",
            "Summary of changes to implement",
            "Output must include",
            "Output contract",
            "This change belongs in",
        ],
    ),
    (
        "definition_of_done",
        [
            "Definition of Done",
            "Success Criteria",
            "Acceptance Criteria",
            "Deliverables",
        ],
    ),
    (
        "tests",
        [
            "Tests",
            "Test commands",
            "Tests Required",
            "Validation Commands",
            "Validation",
            "Final Report Requirements",
        ],
    ),
    ("commit", ["Commit", "Git", "Git commands"]),
    ("files_changed", ["Files Changed"]),
    ("branch", ["Branch"]),
    ("repository", ["Repository"]),
]

# Heading line pattern (markdown or plaintext bold-ish)
_HEADING_LINE = re.compile(
    r"^(?:#{1,4}\s+)?(.+?)(?:\s*:)?\s*$"
)

# Build a reverse map: heading_text → canonical_section
_HEADING_TO_SECTION: dict[str, str] = {}
for _section, _patterns in _SECTION_MAP:
    for _pat in _patterns:
        _HEADING_TO_SECTION[_pat.lower()] = _section

# Sorted unique known heading texts (longest first to avoid partial match issues)
_KNOWN_HEADINGS = sorted(
    set(p.lower() for _, patterns in _SECTION_MAP for p in patterns),
    key=len,
    reverse=True,
)

# Known section heading regex: match markdown headings, plaintext headings,
# and bold-text headings like **Objective:**
_KNOWN_HEADINGS_PATTERN = "|".join(
    re.escape(h) for h in _KNOWN_HEADINGS
)
_KNOWN_HEADING_RE = re.compile(
    r"^(?:#{1,4}\s+)?"
    r"(?:\*\*(" + _KNOWN_HEADINGS_PATTERN + r"):?\*\*"
    r"|"
    r"(" + _KNOWN_HEADINGS_PATTERN + r")"
    r")(?:\s*:)?\s*$",
    re.IGNORECASE | re.MULTILINE,
)


@dataclass
class TaskPromptArchiveEntry:
    task_id: str
    source_artifact_id: str
    conversation_id: str
    title: str
    sections: dict[str, str]
    full_text: str
    created_at: str
    message_count: int
    contains_code: bool
    contains_commit: bool
    codexify_mentions: int
    guardian_mentions: int
    source_path: str
    keyword_density: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "source_artifact_id": self.source_artifact_id,
            "conversation_id": self.conversation_id,
            "title": self.title,
            "sections": {
                k: v
                for k, v in self.sections.items()
                if v.strip()
            },
            "full_text": self.full_text,
            "created_at": self.created_at,
            "message_count": self.message_count,
            "contains_code": self.contains_code,
            "contains_commit": self.contains_commit,
            "codexify_mentions": self.codexify_mentions,
            "guardian_mentions": self.guardian_mentions,
            "source_path": self.source_path,
            "keyword_density": self.keyword_density,
        }

    def to_csv_row(self) -> dict[str, str]:
        return {
            "task_id": self.task_id,
            "source_artifact_id": self.source_artifact_id,
            "conversation_id": self.conversation_id,
            "title": self.title,
            "objective": _trunc(self.sections.get("objective", "")),
            "requirements": _trunc(self.sections.get("requirements", "")),
            "instructions": _trunc(self.sections.get("instructions", "")),
            "definition_of_done": _trunc(
                self.sections.get("definition_of_done", "")
            ),
            "tests": _trunc(self.sections.get("tests", "")),
            "files_changed": _trunc(
                self.sections.get("files_changed", "")
            ),
            "commit_info": _trunc(self.sections.get("commit", "")),
            "created_at": self.created_at,
            "message_count": str(self.message_count),
            "contains_code": str(self.contains_code).lower(),
            "contains_commit": str(self.contains_commit).lower(),
            "codexify_mentions": str(self.codexify_mentions),
            "guardian_mentions": str(self.guardian_mentions),
            "keyword_density": f"{self.keyword_density:.4f}",
            "source_path": self.source_path,
        }


# --- Section extractor ---


def extract_sections(raw_text: str) -> tuple[str, dict[str, str]]:
    """Parse raw task prompt text into title and canonical sections.

    Returns (title, {canonical_section: text}).
    """
    sections: dict[str, str] = {}
    current_section = "_preamble"
    last_pos = 0

    # Find all heading boundaries
    boundaries: list[tuple[int, int, str, str]] = []
    for match in _KNOWN_HEADING_RE.finditer(raw_text):
        heading_text = (match.group(1) or match.group(2)).strip()
        canonical = _HEADING_TO_SECTION.get(heading_text.lower())
        if canonical:
            boundaries.append(
                (match.start(), match.end(), canonical, heading_text)
            )

    if not boundaries:
        # No known section headings — use entire text as body
        title = _extract_title_fallback(raw_text)
        sections["_body"] = raw_text.strip()
        return title, sections

    # Extract text between boundaries
    for i, (start, end, canonical, _heading) in enumerate(boundaries):
        content_start = end
        content_end = (
            boundaries[i + 1][0] if i + 1 < len(boundaries) else len(raw_text)
        )
        content = raw_text[content_start:content_end].strip()

        # If existing content for this section, append
        if canonical in sections:
            sections[canonical] += "\n\n" + content
        else:
            sections[canonical] = content

    # Preamble: before first heading
    first_heading_start = boundaries[0][0]
    preamble = raw_text[:first_heading_start].strip()

    # Extract title from title section or preamble
    title = ""
    if "title" in sections:
        title = _first_line(sections["title"])
        del sections["title"]
    if not title:
        title = _extract_title_fallback(preamble)

    # Store preamble as context if no explicit context section
    if "context" not in sections and preamble:
        sections["context"] = preamble

    # Clean up empty sections
    sections = {k: v for k, v in sections.items() if v.strip()}

    return title, sections


def _extract_title_fallback(text: str) -> str:
    """Extract a title from task prompt text."""
    # Bold title: **Title:** Restore Event Emission
    m = re.search(
        r"^\*\*Title:\*\*\s*(.+)$", text, re.MULTILINE
    )
    if m:
        return m.group(1).strip()[:200]

    # TASK-ID line
    m = re.search(r"^TASK[- ]ID\s*[:\-]?\s*(.+)$", text, re.MULTILINE)
    if m:
        return m.group(1).strip()[:200]

    # Bold prompt: **Prompt** or **Goal:**
    m = re.search(
        r"^\*\*(?:Prompt|Goal|Task):?\*\*\s*:?\s*$",
        text,
        re.MULTILINE | re.IGNORECASE,
    )
    if m:
        # Look for the next substantive line after the **Prompt** marker
        rest = text[m.end():]
        for line in rest.splitlines():
            stripped = line.strip()
            if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
                if len(stripped) > 10:
                    return stripped[:200]

    # Try first markdown heading (skip "Codexify Task Prompt" if it's the only one)
    headings = re.findall(r"^#{1,3}\s+(.+)$", text, re.MULTILINE)
    for h in headings:
        h_stripped = h.strip()
        if h_stripped.lower() not in {"codexify task prompt", "task prompt"}:
            return h_stripped[:200]
    if headings:
        return headings[0].strip()[:200]

    # First non-empty, non-heading line
    for line in text.splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and not stripped.startswith("**"):
            if len(stripped) > 5:
                return stripped[:200]
    return "Untitled Task"


def _first_line(text: str) -> str:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:200]
    return ""


def _trunc(text: str, limit: int = 500) -> str:
    text = text.strip().replace("\n", " ¶ ").replace('"', "'")
    text = " ".join(text.split())
    if len(text) <= limit:
        return text
    return text[: limit - 3] + "..."


# --- Archive builder ---

_CSV_FIELDS = [
    "task_id",
    "source_artifact_id",
    "conversation_id",
    "title",
    "objective",
    "requirements",
    "instructions",
    "definition_of_done",
    "tests",
    "files_changed",
    "commit_info",
    "created_at",
    "message_count",
    "contains_code",
    "contains_commit",
    "codexify_mentions",
    "guardian_mentions",
    "keyword_density",
    "source_path",
]


def build_task_prompt_archive(
    scraper_dir: str | Path = "export_scraper",
    conversation_index_path: str | Path = "export_archaeology/conversation_index.csv",
    output_dir: str | Path = "export_archaeology",
) -> dict[str, int]:
    scraper = Path(scraper_dir).expanduser().resolve()
    idx_path = Path(conversation_index_path).expanduser().resolve()
    out = Path(output_dir).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)

    # Load conversation index
    conv_index = _load_index(idx_path)

    prompts_dir = scraper / "codexify_task_prompts"
    if not prompts_dir.exists():
        return {"entries": 0}

    entries: list[TaskPromptArchiveEntry] = []
    for json_file in sorted(prompts_dir.glob("*.json")):
        entry = _build_entry(json_file, prompts_dir, conv_index)
        if entry:
            entries.append(entry)

    # Sort by message_count descending
    entries.sort(key=lambda e: e.message_count, reverse=True)

    # Write JSON
    (out / "task_prompt_archive.json").write_text(
        json.dumps(
            [e.to_dict() for e in entries],
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    # Write CSV
    with (out / "task_prompt_archive.csv").open(
        "w", newline="", encoding="utf-8"
    ) as fh:
        writer = csv.DictWriter(fh, fieldnames=_CSV_FIELDS)
        writer.writeheader()
        for e in entries:
            writer.writerow(e.to_csv_row())

    # Write Markdown summary
    _write_markdown(entries, out / "task_prompt_archive.md")

    return {
        "entries": len(entries),
        "with_objective": sum(1 for e in entries if "objective" in e.sections),
        "with_requirements": sum(
            1 for e in entries if "requirements" in e.sections
        ),
        "with_definition_of_done": sum(
            1 for e in entries if "definition_of_done" in e.sections
        ),
        "with_tests": sum(1 for e in entries if "tests" in e.sections),
        "with_commit": sum(1 for e in entries if "commit" in e.sections),
        "with_files_changed": sum(
            1 for e in entries if "files_changed" in e.sections
        ),
    }


def _load_index(path: Path) -> dict[str, dict[str, str]]:
    index: dict[str, dict[str, str]] = {}
    if not path.exists():
        return index
    with path.open("r", encoding="utf-8") as fh:
        for row in csv.DictReader(fh):
            cid = row.get("conversation_id", "").strip()
            if cid:
                index[cid] = row
    return index


def _build_entry(
    json_path: Path,
    prompts_dir: Path,
    conv_index: dict[str, dict[str, str]],
) -> TaskPromptArchiveEntry | None:
    try:
        data = json.loads(json_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    metadata = data.get("metadata", {})
    conv_id = (metadata.get("source_conversation_id") or "").strip()
    if not conv_id:
        return None

    artifact_id = metadata.get("artifact_id", json_path.stem)
    created_at = metadata.get("source_created_at", "")
    source_path = metadata.get("source_file_path", "")

    # Read raw text
    md_path = prompts_dir / f"{artifact_id}.md"
    raw_text = ""
    if md_path.exists():
        raw_text = md_path.read_text(encoding="utf-8", errors="replace")

    # Content-addressable task_id
    normalized = _normalize_for_id(raw_text)
    task_id = "task-" + hashlib.sha256(
        normalized.encode("utf-8")
    ).hexdigest()[:24]

    # Extract sections
    title, sections = extract_sections(raw_text)

    # Conversation metadata
    conv_row = conv_index.get(conv_id, {})
    try:
        msg_count = int(conv_row.get("message_count", 0))
    except (ValueError, TypeError):
        msg_count = 0
    contains_code = conv_row.get("contains_code", "false").lower() == "true"

    # Keyword counts
    codexify_mentions = len(
        re.findall(r"\bCodexify\b", raw_text, re.IGNORECASE)
    )
    guardian_mentions = len(
        re.findall(r"\bGuardian\b", raw_text, re.IGNORECASE)
    )
    keyword_density = (
        (codexify_mentions + guardian_mentions) / msg_count
        if msg_count > 0
        else 0.0
    )

    # Commit detection
    commit_pat = re.compile(
        r"(?im)^(?:#{1,6}\s*)?Commit[\s:]|git\s+commit|committed\s+in\s+[0-9a-f]{7}"
    )
    contains_commit = bool(commit_pat.search(raw_text))

    return TaskPromptArchiveEntry(
        task_id=task_id,
        source_artifact_id=artifact_id,
        conversation_id=conv_id,
        title=title,
        sections=sections,
        full_text=raw_text,
        created_at=created_at,
        message_count=msg_count,
        contains_code=contains_code,
        contains_commit=contains_commit,
        codexify_mentions=codexify_mentions,
        guardian_mentions=guardian_mentions,
        source_path=source_path,
        keyword_density=keyword_density,
    )


def _normalize_for_id(text: str) -> str:
    """Normalize text for stable content-addressed ID."""
    # Strip trailing whitespace, normalize line endings
    return text.strip().replace("\r\n", "\n").replace("\r", "\n")


def _write_markdown(
    entries: list[TaskPromptArchiveEntry], output_path: Path
) -> None:
    lines = [
        "# Task Prompt Archive",
        "",
        f"Total entries: {len(entries)}",
        "",
        "## Section Coverage",
        "",
    ]

    coverage = {
        "objective": sum(
            1 for e in entries if "objective" in e.sections
        ),
        "requirements": sum(
            1 for e in entries if "requirements" in e.sections
        ),
        "instructions": sum(
            1 for e in entries if "instructions" in e.sections
        ),
        "definition_of_done": sum(
            1 for e in entries if "definition_of_done" in e.sections
        ),
        "tests": sum(1 for e in entries if "tests" in e.sections),
        "commit": sum(1 for e in entries if "commit" in e.sections),
        "files_changed": sum(
            1 for e in entries if "files_changed" in e.sections
        ),
        "context": sum(
            1 for e in entries if "context" in e.sections
        ),
    }
    for section, count in sorted(coverage.items()):
        pct = f"({count * 100 // len(entries)}%)" if entries else "(0%)"
        lines.append(f"- **{section}**: {count} {pct}")

    lines.extend(["", "## Top 30 Entries by Message Count", ""])

    for i, entry in enumerate(entries[:30], 1):
        lines.append(
            f"### {i}. {entry.title[:120] or 'Untitled'}"
        )
        lines.append("")
        lines.append(
            f"- **Task ID**: `{entry.task_id}`"
        )
        lines.append(
            f"- **Conversation**: `{entry.conversation_id}` ({entry.message_count} msgs)"
        )
        lines.append(
            f"- **Created**: {entry.created_at[:19]}"
        )
        lines.append(
            f"- **Sections present**: {', '.join(sorted(entry.sections.keys()))}"
        )
        lines.append(
            f"- **Keywords**: Codexify={entry.codexify_mentions}, Guardian={entry.guardian_mentions}"
        )
        if entry.contains_commit:
            lines.append("- **Commit detected**: yes")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
