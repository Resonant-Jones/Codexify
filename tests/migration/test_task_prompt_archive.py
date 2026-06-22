"""Tests for task_prompt_archive — synthetic fixtures only."""

from __future__ import annotations

import csv
import json
from pathlib import Path

from backend.rag.task_prompt_archive import (
    TaskPromptArchiveEntry,
    build_task_prompt_archive,
    extract_sections,
    _normalize_for_id,
)


# --- Synthetic helpers ---


def _write_scraper_artifact(
    prompts_dir: Path,
    artifact_id: str,
    conversation_id: str,
    raw_text: str,
    *,
    created_at: str = "2025-01-01T00:00:00+00:00",
    source_path: str = "conversations-000.json",
) -> tuple[Path, Path]:
    prompts_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "artifact_id": artifact_id,
        "artifact_type": "codexify_task_prompt",
        "confidence": 1.0,
        "content_sha256": "abc",
        "extracted_at": "2025-01-01T00:00:00+00:00",
        "extractor": "test_v1",
        "import_batch_id": "test-batch",
        "source": "openai_export",
        "source_conversation_id": conversation_id,
        "source_thread_id": conversation_id,
        "source_message_id": "msg-1",
        "source_file_path": source_path,
        "source_created_at": created_at,
        "source_updated_at": created_at,
    }
    json_path = prompts_dir / f"{artifact_id}.json"
    json_path.write_text(
        json.dumps(
            {
                "metadata": meta,
                "parsed_fields": {"label": "Codexify Task Prompt"},
                "raw_file": f"{artifact_id}.md",
            }
        ),
        encoding="utf-8",
    )
    md_path = prompts_dir / f"{artifact_id}.md"
    md_path.write_text(raw_text, encoding="utf-8")
    return json_path, md_path


def _write_conversation_index(
    path: Path,
    rows: list[dict[str, str]],
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "conversation_id",
        "title",
        "message_count",
        "first_message",
        "last_message",
        "contains_task_prompt",
        "contains_summary",
        "contains_attachments",
        "contains_code",
        "contains_images",
    ]
    with path.open("w", newline="", encoding="utf-8") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            complete = {
                "conversation_id": row["conversation_id"],
                "title": row.get("title", "Untitled"),
                "message_count": row.get("message_count", "0"),
                "first_message": row.get("first_message", ""),
                "last_message": row.get("last_message", ""),
                "contains_task_prompt": row.get("contains_task_prompt", "false"),
                "contains_summary": row.get("contains_summary", "false"),
                "contains_attachments": row.get("contains_attachments", "false"),
                "contains_code": row.get("contains_code", "false"),
                "contains_images": row.get("contains_images", "false"),
            }
            writer.writerow(complete)
    return path


# --- Section extraction tests ---


def test_extract_sections_from_standard_format():
    text = """Codexify Task Prompt

Context
Build a thing.

## Objective
Make it work.

## Requirements
- Item 1
- Item 2

## Definition of Done
All tests pass.

## Tests
pytest tests/

## Files Changed
backend/rag/foo.py

## Commit
fix: made it work
"""
    title, sections = extract_sections(text)
    assert title == "Codexify Task Prompt"
    assert "context" in sections
    assert "Build a thing." in sections["context"]
    assert sections["objective"] == "Make it work."
    assert "Item 1" in sections["requirements"]
    assert "All tests pass" in sections["definition_of_done"]
    assert "pytest tests/" in sections["tests"]
    assert "backend/rag/foo.py" in sections["files_changed"]
    assert "fix: made it work" in sections["commit"]


def test_extract_sections_with_task_title():
    text = """## Codexify Task Prompt

## Task Title
Mobile Sidebar Fix

## Objective
Fix the sidebar.

## Instructions
Edit the file carefully.
"""
    title, sections = extract_sections(text)
    assert title == "Mobile Sidebar Fix"
    assert sections["objective"] == "Fix the sidebar."
    assert "Edit the file carefully" in sections["instructions"]


def test_extract_sections_minimal_format():
    text = """# Codexify Task Prompt

Fix the bug in the auth module.
"""
    title, sections = extract_sections(text)
    assert title == "Codexify Task Prompt"
    # No known section headings, so entire body goes to _body
    assert "_body" in sections
    assert "Fix the bug" in sections["_body"]


def test_extract_sections_with_constraints_as_requirements():
    text = """## Objective
Make it fast.

## Constraints
- Must use Python 3.10+
- No new dependencies
"""
    title, sections = extract_sections(text)
    assert sections["requirements"] is not None
    assert "Python 3.10" in sections["requirements"]


def test_extract_sections_treats_required_behavior_as_requirements():
    text = """## Required behavior
The button must close on tap.

## Definition of Done
Works on mobile.
"""
    title, sections = extract_sections(text)
    assert "requirements" in sections
    assert "button must close" in sections["requirements"]


def test_extract_sections_detects_repository_and_branch():
    text = """## Repository
Resonant-Jones/Codexify

## Branch
feature/my-feature

## Objective
Add feature X.
"""
    title, sections = extract_sections(text)
    assert sections["repository"] == "Resonant-Jones/Codexify"
    assert sections["branch"] == "feature/my-feature"


def test_extract_sections_no_known_headings():
    text = """Just a random task.

Do this thing.

Then do that thing.
"""
    title, sections = extract_sections(text)
    # Should fall through to body
    assert "_body" in sections


# --- Normalization test ---


def test_normalize_for_id_is_deterministic():
    text1 = "Codexify Task Prompt\n\nDo X.\n"
    text2 = "Codexify Task Prompt\n\nDo X."
    id1 = _normalize_for_id(text1)
    id2 = _normalize_for_id(text2)
    assert id1 == id2


# --- Archive entry tests ---


def test_entry_to_dict():
    entry = TaskPromptArchiveEntry(
        task_id="task-abc123",
        source_artifact_id="codexify_task_prompt-xxx",
        conversation_id="conv-1",
        title="Test Task",
        sections={"objective": "Do X", "requirements": "- Item 1"},
        full_text="Full text here",
        created_at="2025-01-01",
        message_count=50,
        contains_code=True,
        contains_commit=False,
        codexify_mentions=5,
        guardian_mentions=3,
        source_path="conversations-000.json",
        keyword_density=0.16,
    )
    d = entry.to_dict()
    assert d["task_id"] == "task-abc123"
    assert d["sections"]["objective"] == "Do X"
    assert d["message_count"] == 50


def test_entry_to_csv_row():
    entry = TaskPromptArchiveEntry(
        task_id="task-abc",
        source_artifact_id="codexify_task_prompt-yyy",
        conversation_id="conv-2",
        title="CSV Test",
        sections={"objective": "Do Y"},
        full_text="text",
        created_at="2025-02-01",
        message_count=30,
        contains_code=False,
        contains_commit=True,
        codexify_mentions=1,
        guardian_mentions=0,
        source_path="conversations-001.json",
        keyword_density=0.0333,
    )
    row = entry.to_csv_row()
    assert row["task_id"] == "task-abc"
    assert row["contains_code"] == "false"
    assert row["contains_commit"] == "true"


# --- Full pipeline integration tests ---


def test_build_archive_with_multiple_prompts(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    prompts_dir = scraper / "codexify_task_prompts"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    _write_scraper_artifact(
        prompts_dir,
        "tp-1",
        "conv-a",
        """## Codexify Task Prompt

## Task Title
First Task

## Objective
Build the archive.

## Requirements
- Test coverage

## Tests
pytest tests/
""",
    )
    _write_scraper_artifact(
        prompts_dir,
        "tp-2",
        "conv-b",
        """## Objective
Fix the bug.

## Instructions
Edit backend/rag/foo.py
""",
    )

    _write_conversation_index(
        index_path,
        [
            {
                "conversation_id": "conv-a",
                "title": "Alpha",
                "message_count": "100",
                "contains_code": "true",
            },
            {
                "conversation_id": "conv-b",
                "title": "Beta",
                "message_count": "20",
                "contains_code": "false",
            },
        ],
    )

    results = build_task_prompt_archive(
        scraper_dir=scraper,
        conversation_index_path=index_path,
        output_dir=out_dir,
    )

    assert results["entries"] == 2
    assert results["with_objective"] == 2
    assert results["with_requirements"] == 1
    assert results["with_tests"] == 1

    # Verify JSON
    json_path = out_dir / "task_prompt_archive.json"
    assert json_path.exists()
    data = json.loads(json_path.read_text())
    assert len(data) == 2
    # Sorted by message_count descending: conv-a (100) before conv-b (20)
    assert data[0]["conversation_id"] == "conv-a"
    assert data[0]["title"] == "First Task"
    assert data[0]["message_count"] == 100
    assert "task_id" in data[0]
    assert data[0]["task_id"].startswith("task-")
    assert len(data[0]["task_id"]) == 29  # "task-" + 24 hex chars

    # Verify CSV
    csv_path = out_dir / "task_prompt_archive.csv"
    assert csv_path.exists()
    with csv_path.open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 2
    assert rows[0]["title"] == "First Task"
    assert rows[0]["contains_code"] == "true"

    # Verify MD
    md_path = out_dir / "task_prompt_archive.md"
    assert md_path.exists()
    md_text = md_path.read_text()
    assert "Task Prompt Archive" in md_text
    assert "First Task" in md_text


def test_build_archive_empty_scraper_dir(tmp_path: Path):
    scraper = tmp_path / "empty_scraper"
    scraper.mkdir()
    index_path = tmp_path / "conversation_index.csv"
    _write_conversation_index(
        index_path,
        [{"conversation_id": "c1", "title": "X", "message_count": "1"}],
    )
    out_dir = tmp_path / "out"

    results = build_task_prompt_archive(scraper, index_path, out_dir)

    assert results["entries"] == 0


def test_task_id_is_content_addressed_and_stable(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    prompts_dir = scraper / "codexify_task_prompts"
    index_path = tmp_path / "conversation_index.csv"
    out1 = tmp_path / "out1"
    out2 = tmp_path / "out2"

    text = """## Objective
Do the same thing twice."""

    _write_scraper_artifact(prompts_dir, "tp-same-1", "conv-x", text)
    _write_scraper_artifact(prompts_dir, "tp-same-2", "conv-x", text)
    _write_conversation_index(
        index_path,
        [{"conversation_id": "conv-x", "title": "X", "message_count": "10"}],
    )

    results1 = build_task_prompt_archive(scraper, index_path, out1)
    results2 = build_task_prompt_archive(scraper, index_path, out2)

    assert results1["entries"] == 2
    assert results2["entries"] == 2

    data1 = json.loads((out1 / "task_prompt_archive.json").read_text())
    data2 = json.loads((out2 / "task_prompt_archive.json").read_text())

    # Same content → same task_id
    assert data1[0]["task_id"] == data2[0]["task_id"]
    assert data1[1]["task_id"] == data2[1]["task_id"]


def test_missing_conversation_index_defaults(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    prompts_dir = scraper / "codexify_task_prompts"
    index_path = tmp_path / "nonexistent.csv"
    out_dir = tmp_path / "out"

    _write_scraper_artifact(
        prompts_dir, "tp-orphan", "conv-missing", "## Objective\nDo X."
    )

    results = build_task_prompt_archive(scraper, index_path, out_dir)
    assert results["entries"] == 1

    data = json.loads((out_dir / "task_prompt_archive.json").read_text())
    assert data[0]["message_count"] == 0
    assert data[0]["contains_code"] is False
