from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.rag.openai_export_task_scraper import scrape_openai_export_tasks


def _write_conversations_json(
    root: Path,
    message_texts: list[str],
    *,
    thread_id: str = "scrape-thread",
) -> None:
    mapping: dict[str, dict[str, Any]] = {}
    parent: str | None = None
    for index, text in enumerate(message_texts, start=1):
        node_id = f"m{index}"
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "id": node_id,
                "author": {"role": "user"},
                "content": {"content_type": "text", "parts": [text]},
                "create_time": index,
            },
        }
        if parent:
            mapping[parent]["children"].append(node_id)
        parent = node_id

    (root / "conversations.json").write_text(
        json.dumps(
            [
                {
                    "id": thread_id,
                    "conversation_id": thread_id,
                    "title": "Scraper Fixture",
                    "current_node": parent,
                    "mapping": mapping,
                }
            ]
        ),
        encoding="utf-8",
    )


def _artifact_files(output_root: Path, dirname: str) -> tuple[list[Path], list[Path]]:
    target = output_root / dirname
    return sorted(target.glob("*.md")), sorted(target.glob("*.json"))


def test_scraper_extracts_exact_codexify_task_prompt(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    export_root.mkdir()
    raw_prompt = """Codexify Task Prompt

TASK-ID
TASK-2026-06-20-001_EXTRACT_PROMPTS

Context
Extract this exact task prompt without changing wording.

Requirements
- Preserve raw text.
- Do not write to the database.
"""
    _write_conversations_json(export_root, [raw_prompt])

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    assert report.counts()["codexify_task_prompt_hits"] == 1
    md_files, json_files = _artifact_files(output_root, "codexify_task_prompts")
    assert len(md_files) == 1
    assert len(json_files) == 1
    assert md_files[0].read_text(encoding="utf-8") == raw_prompt.strip()
    sidecar = json.loads(json_files[0].read_text(encoding="utf-8"))
    metadata = sidecar["metadata"]
    assert metadata["source"] == "openai_export"
    assert metadata["source_conversation_id"] == "scrape-thread"
    assert metadata["source_message_id"] == "m1"
    assert metadata["extractor"] == "codexify_task_prompt_v1"
    assert metadata["artifact_id"].startswith("codexify_task_prompt-")


def test_scraper_extracts_exact_task_summary_from_markdown(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    export_root.mkdir()
    summary = """## Task Summary

- Updated the importer.
- Tests passed.

## Verification

This heading is outside the summary artifact.
"""
    (export_root / "summary.md").write_text(summary, encoding="utf-8")

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    assert report.counts()["task_summary_hits"] == 1
    md_files, json_files = _artifact_files(output_root, "task_summaries")
    assert len(md_files) == 1
    assert len(json_files) == 1
    assert md_files[0].read_text(encoding="utf-8") == (
        "## Task Summary\n\n- Updated the importer.\n- Tests passed."
    )


def test_scraper_extracts_multiple_matches_from_one_conversation(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    export_root.mkdir()
    message = """Codexify Task Prompt

TASK-ID
TASK-2026-06-20-002_MULTI

Context
One message can contain multiple canonical artifacts.

Task Summary

- Prompt extracted.
- Summary extracted.

Execution Contract

Scope
- Internal prototype only.

Acceptance Criteria
- Writes artifacts.

Rollback
- Delete generated files.
"""
    _write_conversations_json(export_root, [message], thread_id="multi-thread")

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    counts = report.counts()
    assert counts["codexify_task_prompt_hits"] == 1
    assert counts["task_summary_hits"] == 1
    assert counts["execution_contract_hits"] == 1
    assert len(_artifact_files(output_root, "codexify_task_prompts")[0]) == 1
    assert len(_artifact_files(output_root, "task_summaries")[0]) == 1
    assert len(_artifact_files(output_root, "execution_contracts")[0]) == 1
    summary_md = _artifact_files(output_root, "task_summaries")[0][0].read_text(
        encoding="utf-8"
    )
    assert "Execution Contract" not in summary_md


def test_scraper_routes_partial_match_to_unknown(tmp_path: Path) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        ["Codexify Task Prompt\n\nTODO"],
        thread_id="partial-thread",
    )

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    counts = report.counts()
    assert counts["codexify_task_prompt_hits"] == 0
    assert counts["partial_or_ambiguous_hits"] == 1
    md_files, json_files = _artifact_files(output_root, "unknown_or_partial_matches")
    assert len(md_files) == 1
    assert len(json_files) == 1
    assert "TODO" in md_files[0].read_text(encoding="utf-8")


def test_scraper_no_match_produces_no_artifacts_but_diagnostics(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        ["A normal conversation with no canonical labels."],
        thread_id="no-match-thread",
    )

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    assert report.artifacts == []
    diagnostic_json = output_root / "diagnostics" / "scraper_report.json"
    diagnostic_md = output_root / "diagnostics" / "scraper_report.md"
    assert diagnostic_json.exists()
    assert diagnostic_md.exists()
    payload = json.loads(diagnostic_json.read_text(encoding="utf-8"))
    assert payload["files_scanned"] == 1
    assert payload["messages_scanned"] == 1
    assert payload["codexify_task_prompt_hits"] == 0


def test_scraper_reads_sharded_dat_json_and_writes_sidecars(
    tmp_path: Path,
) -> None:
    export_root = tmp_path / "export"
    output_root = tmp_path / "export_scraper"
    part = export_root / "conversations__tasks.part-0001"
    part.mkdir(parents=True)
    text = """Task Summary

- Sharded export message found.
- Sidecar metadata preserved.
"""
    (part / "file_0000000000000001.dat").write_text(
        json.dumps(
            {
                "conversation_id": "sharded-task-thread",
                "messages": [
                    {
                        "message_id": "sharded-message-1",
                        "role": "assistant",
                        "content": text,
                        "create_time": 1,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )

    report = scrape_openai_export_tasks(export_root, output_dir=output_root)

    assert report.counts()["task_summary_hits"] == 1
    md_files, json_files = _artifact_files(output_root, "task_summaries")
    assert len(md_files) == 1
    assert len(json_files) == 1
    metadata = json.loads(json_files[0].read_text(encoding="utf-8"))["metadata"]
    assert metadata["source_thread_id"] == "sharded-task-thread"
    assert metadata["source_message_id"] == "sharded-message-1"
    assert metadata["source_file_path"].endswith("file_0000000000000001.dat")
