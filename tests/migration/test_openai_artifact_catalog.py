"""Tests for openai_artifact_catalog — synthetic fixtures only."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from backend.rag.openai_artifact_catalog import (
    ArtifactCatalog,
    ArtifactRecord,
    KeystoneConversation,
    build_artifact_catalog,
)


# --- Synthetic fixture helpers ---


def _write_artifact_json(
    artifact_dir: Path,
    artifact_id: str,
    artifact_type: str,
    conversation_id: str,
    *,
    created_at: str = "2025-01-01T00:00:00+00:00",
    source_path: str = "conversations-000.json",
    confidence: float = 1.0,
) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    meta = {
        "artifact_id": artifact_id,
        "artifact_type": artifact_type,
        "confidence": confidence,
        "content_sha256": "abc123",
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
    path = artifact_dir / f"{artifact_id}.json"
    path.write_text(
        json.dumps({"metadata": meta, "parsed_fields": {}, "raw_file": f"{artifact_id}.md"}),
        encoding="utf-8",
    )
    return path


def _write_artifact_md(artifact_dir: Path, artifact_id: str, text: str) -> Path:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    path = artifact_dir / f"{artifact_id}.md"
    path.write_text(text, encoding="utf-8")
    return path


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


# --- Unit tests ---


def test_artifact_record_to_row():
    record = ArtifactRecord(
        artifact_id="tp-1",
        artifact_type="codexify_task_prompt",
        conversation_id="conv-a",
        title="Test Conv",
        message_count=42,
        contains_code=True,
        contains_commit=False,
        created_at="2025-06-01",
        source_path="conversations-000.json",
        codexify_mentions=5,
        guardian_mentions=3,
    )
    row = record.to_row()
    assert row["artifact_id"] == "tp-1"
    assert row["contains_code"] == "true"
    assert row["codexify_mentions"] == 5


def test_keystone_conversation_to_row():
    kc = KeystoneConversation(
        conversation_id="conv-z",
        title="Key Conv",
        message_count=100,
        task_prompt_count=3,
        summary_count=1,
        contains_code=True,
        contains_commit=True,
        codexify_mentions=15,
        guardian_mentions=10,
        keyword_density=0.25,
        keystone_score=5.25,
    )
    row = kc.to_row()
    assert row["conversation_id"] == "conv-z"
    assert row["keystone_score"] == 5.25
    assert row["keyword_density"] == 0.25


# --- Integration tests ---


def test_catalog_correlates_artifacts_with_index(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"
    ts_dir = scraper / "task_summaries"

    # Two task prompts, one summary
    _write_artifact_json(tp_dir, "tp-a", "codexify_task_prompt", "conv-1")
    _write_artifact_md(tp_dir, "tp-a", "Codexify does X. Guardian helps.")
    _write_artifact_json(tp_dir, "tp-b", "codexify_task_prompt", "conv-1")
    _write_artifact_md(tp_dir, "tp-b", "Another Codexify task. git commit abc1234")
    _write_artifact_json(ts_dir, "ts-x", "task_summary", "conv-2")
    _write_artifact_md(ts_dir, "ts-x", "Summary: Guardian and Codexify done.")

    _write_conversation_index(
        index_path,
        [
            {
                "conversation_id": "conv-1",
                "title": "Alpha Conv",
                "message_count": "50",
                "contains_code": "true",
            },
            {
                "conversation_id": "conv-2",
                "title": "Beta Conv",
                "message_count": "10",
                "contains_code": "false",
            },
        ],
    )

    results = build_artifact_catalog(
        scraper_dir=scraper,
        conversation_index_path=index_path,
        output_dir=out_dir,
    )

    assert results["total_artifacts"] == 3
    assert results["task_prompts"] == 2
    assert results["task_summaries"] == 1
    assert results["unique_conversations"] == 2

    # Verify catalog CSV
    cat_path = out_dir / "artifact_catalog.csv"
    assert cat_path.exists()
    with cat_path.open("r", encoding="utf-8") as fh:
        reader = list(csv.DictReader(fh))
    assert len(reader) == 3
    artifacts_by_id = {r["artifact_id"]: r for r in reader}
    assert artifacts_by_id["tp-a"]["title"] == "Alpha Conv"
    assert artifacts_by_id["tp-a"]["codexify_mentions"] == "1"
    assert artifacts_by_id["tp-b"]["contains_commit"] == "true"
    assert artifacts_by_id["ts-x"]["title"] == "Beta Conv"


def test_keystone_scoring_ranks_conversations(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"

    # conv-A: many task prompts, code, commit, high keyword density
    for i in range(3):
        _write_artifact_json(tp_dir, f"tp-a{i}", "codexify_task_prompt", "conv-A")
        _write_artifact_md(
            tp_dir,
            f"tp-a{i}",
            "Codexify task #1. Guardian rocks. git commit deadbeef",
        )
    # conv-B: one task prompt, no code, low density
    _write_artifact_json(tp_dir, "tp-b0", "codexify_task_prompt", "conv-B")
    _write_artifact_md(tp_dir, "tp-b0", "Simple task.")

    _write_conversation_index(
        index_path,
        [
            {
                "conversation_id": "conv-A",
                "title": "High Value",
                "message_count": "20",
                "contains_code": "true",
            },
            {
                "conversation_id": "conv-B",
                "title": "Low Value",
                "message_count": "100",
                "contains_code": "false",
            },
        ],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    ks_path = out_dir / "keystone_conversations.csv"
    assert ks_path.exists()
    with ks_path.open("r", encoding="utf-8") as fh:
        reader = list(csv.DictReader(fh))
    assert len(reader) == 2

    # conv-A should rank above conv-B
    assert reader[0]["conversation_id"] == "conv-A"
    assert reader[1]["conversation_id"] == "conv-B"
    assert float(reader[0]["keystone_score"]) > float(reader[1]["keystone_score"])

    # conv-A should have 3 task prompts
    assert reader[0]["task_prompt_count"] == "3"


def test_empty_scraper_dir_produces_empty_outputs(tmp_path: Path):
    scraper = tmp_path / "empty_scraper"
    scraper.mkdir()
    index_path = tmp_path / "conversation_index.csv"
    _write_conversation_index(
        index_path,
        [{"conversation_id": "conv-x", "title": "X", "message_count": "1"}],
    )
    out_dir = tmp_path / "out"

    results = build_artifact_catalog(scraper, index_path, out_dir)

    assert results["total_artifacts"] == 0
    assert results["unique_conversations"] == 0

    # All CSVs should exist but be empty (header only)
    for name in [
        "artifact_catalog.csv",
        "task_prompt_index.csv",
        "task_summary_index.csv",
        "keystone_conversations.csv",
    ]:
        path = out_dir / name
        assert path.exists()
        with path.open("r", encoding="utf-8") as fh:
            lines = fh.readlines()
        assert len(lines) == 1  # header only


def test_missing_conversation_in_index_uses_defaults(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"
    _write_artifact_json(tp_dir, "tp-orphan", "codexify_task_prompt", "conv-missing")
    _write_artifact_md(tp_dir, "tp-orphan", "Orphan task about Codexify.")

    _write_conversation_index(
        index_path,
        [],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    cat_path = out_dir / "artifact_catalog.csv"
    with cat_path.open("r", encoding="utf-8") as fh:
        reader = list(csv.DictReader(fh))
    assert len(reader) == 1
    assert reader[0]["title"] == ""
    assert reader[0]["message_count"] == "0"


def test_commit_detection_in_raw_text(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"

    # With commit
    _write_artifact_json(tp_dir, "tp-commit", "codexify_task_prompt", "conv-c")
    _write_artifact_md(
        tp_dir, "tp-commit", "## Commit\na1b2c3d Task done."
    )
    # Without commit
    _write_artifact_json(tp_dir, "tp-nocommit", "codexify_task_prompt", "conv-d")
    _write_artifact_md(tp_dir, "tp-nocommit", "Just a task description.")

    _write_conversation_index(
        index_path,
        [
            {
                "conversation_id": "conv-c",
                "title": "With Commit",
                "message_count": "10",
            },
            {
                "conversation_id": "conv-d",
                "title": "No Commit",
                "message_count": "10",
            },
        ],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    cat_path = out_dir / "artifact_catalog.csv"
    with cat_path.open("r", encoding="utf-8") as fh:
        reader = {r["artifact_id"]: r for r in csv.DictReader(fh)}

    assert reader["tp-commit"]["contains_commit"] == "true"
    assert reader["tp-nocommit"]["contains_commit"] == "false"


def test_task_prompt_index_excludes_summaries(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"
    ts_dir = scraper / "task_summaries"
    _write_artifact_json(tp_dir, "tp-1", "codexify_task_prompt", "conv-1")
    _write_artifact_md(tp_dir, "tp-1", "Task.")
    _write_artifact_json(ts_dir, "ts-1", "task_summary", "conv-1")
    _write_artifact_md(ts_dir, "ts-1", "Summary.")

    _write_conversation_index(
        index_path,
        [{"conversation_id": "conv-1", "title": "C1", "message_count": "1"}],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    with (out_dir / "task_prompt_index.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["artifact_type"] == "codexify_task_prompt"

    with (out_dir / "task_summary_index.csv").open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["artifact_type"] == "task_summary"


def test_partial_matches_appear_in_catalog(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    partial_dir = scraper / "unknown_or_partial_matches"
    _write_artifact_json(
        partial_dir, "partial-1", "unknown_or_partial", "conv-p", confidence=0.35
    )
    _write_artifact_md(partial_dir, "partial-1", "Partial Codexify mention.")

    _write_conversation_index(
        index_path,
        [{"conversation_id": "conv-p", "title": "Partial Conv", "message_count": "5"}],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    cat_path = out_dir / "artifact_catalog.csv"
    with cat_path.open("r", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 1
    assert rows[0]["artifact_type"] == "unknown_or_partial"
    assert rows[0]["confidence"] == "0.35"

    # Should appear in keystone with partial_count=1
    ks_path = out_dir / "keystone_conversations.csv"
    with ks_path.open("r", encoding="utf-8") as fh:
        ks_rows = list(csv.DictReader(fh))
    assert len(ks_rows) == 1
    assert ks_rows[0]["partial_count"] == "1"


def test_keyword_mentions_aggregate_across_artifacts_in_same_conversation(
    tmp_path: Path,
):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"
    _write_artifact_json(tp_dir, "tp-1", "codexify_task_prompt", "conv-multi")
    _write_artifact_md(tp_dir, "tp-1", "Codexify here. Guardian there.")
    _write_artifact_json(tp_dir, "tp-2", "codexify_task_prompt", "conv-multi")
    _write_artifact_md(tp_dir, "tp-2", "Codexify again. Codexify everywhere.")

    _write_conversation_index(
        index_path,
        [{"conversation_id": "conv-multi", "title": "Multi", "message_count": "20"}],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    ks_path = out_dir / "keystone_conversations.csv"
    with ks_path.open("r", encoding="utf-8") as fh:
        ks_rows = list(csv.DictReader(fh))
    assert len(ks_rows) == 1
    # tp-1: 1 Codexify, 1 Guardian. tp-2: 2 Codexify. Total: 3 Codexify, 1 Guardian
    assert ks_rows[0]["codexify_mentions"] == "3"
    assert ks_rows[0]["guardian_mentions"] == "1"


def test_normalized_density_within_0_1_range(tmp_path: Path):
    scraper = tmp_path / "export_scraper"
    index_path = tmp_path / "conversation_index.csv"
    out_dir = tmp_path / "out"

    tp_dir = scraper / "codexify_task_prompts"

    # conv-dense: high keyword count vs small message_count
    _write_artifact_json(tp_dir, "tp-d", "codexify_task_prompt", "conv-dense")
    _write_artifact_md(
        tp_dir, "tp-d", "Codexify Guardian " * 20
    )
    # conv-sparse: low keyword count vs large message_count
    _write_artifact_json(tp_dir, "tp-s", "codexify_task_prompt", "conv-sparse")
    _write_artifact_md(tp_dir, "tp-s", "One Codexify mention.")

    _write_conversation_index(
        index_path,
        [
            {
                "conversation_id": "conv-dense",
                "title": "Dense",
                "message_count": "10",
            },
            {
                "conversation_id": "conv-sparse",
                "title": "Sparse",
                "message_count": "100",
            },
        ],
    )

    build_artifact_catalog(scraper, index_path, out_dir)

    ks_path = out_dir / "keystone_conversations.csv"
    with ks_path.open("r", encoding="utf-8") as fh:
        ks_rows = {r["conversation_id"]: r for r in csv.DictReader(fh)}

    dense_density = float(ks_rows["conv-dense"]["keyword_density"])
    sparse_density = float(ks_rows["conv-sparse"]["keyword_density"])
    # raw density: mentions / message_count (not 0-1 normalized)
    assert dense_density > sparse_density
    # conv-dense: 40 mentions / 10 msgs = 4.0
    assert dense_density == pytest.approx(4.0)
    # conv-sparse: 1 mention / 100 msgs = 0.01
    assert sparse_density == pytest.approx(0.01)
