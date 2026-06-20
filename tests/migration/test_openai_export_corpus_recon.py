"""Tests for openai_export_corpus_recon — synthetic fixtures only."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from backend.rag.openai_export_corpus_recon import (
    CorpusReconStats,
    OpenAIExportCorpusRecon,
    ReconConversation,
    ReconMessage,
    _classify_path_family,
    _classify_size_bucket,
    _is_sharded_path,
    _is_workspace_or_files_asset,
    _linearize_mainline,
    _resolve_active_node,
    run_corpus_recon,
    write_conversation_index,
    write_corpus_stats,
    write_corpus_summary_markdown,
    write_recon_report,
)


# --- Synthetic fixture helpers ---


def _build_mapping_conversation(
    turns: list[tuple[str, str, float]],
    *,
    conversation_id: str = "test-conv",
    title: str = "Test Conversation",
) -> dict[str, Any]:
    mapping: dict[str, dict[str, Any]] = {}
    parent: str | None = None
    for idx, (role, text, create_time) in enumerate(turns, start=1):
        node_id = f"m{idx}"
        mapping[node_id] = {
            "id": node_id,
            "parent": parent,
            "children": [],
            "message": {
                "id": node_id,
                "author": {"role": role},
                "content": {"content_type": "text", "parts": [text]},
                "create_time": create_time,
            },
        }
        if parent and parent in mapping:
            mapping[parent]["children"].append(node_id)
        parent = node_id
    return {
        "conversation_id": conversation_id,
        "id": conversation_id,
        "title": title,
        "current_node": parent,
        "mapping": mapping,
    }


def _build_messages_container(
    messages: list[dict[str, Any]],
    *,
    conversation_id: str = "msg-conv",
    title: str = "Message Container",
) -> dict[str, Any]:
    return {
        "conversation_id": conversation_id,
        "title": title,
        "messages": messages,
    }


def _write_conversations_json(
    root: Path,
    conversations: list[dict[str, Any]],
    *,
    filename: str = "conversations-000.json",
    subdir: str | None = None,
) -> Path:
    if subdir:
        dest = root / subdir
        dest.mkdir(parents=True)
    else:
        dest = root
    path = dest / filename
    path.write_text(json.dumps(conversations), encoding="utf-8")
    return path


# --- ReconConversation unit tests ---


def test_recon_conversation_first_last_message():
    conv = ReconConversation(
        conversation_id="c1",
        title="Test",
        messages=[
            ReconMessage(text="First hello", timestamp=1.0),
            ReconMessage(text="Second response", timestamp=2.0),
            ReconMessage(text="Third goodbye", timestamp=3.0),
        ],
    )
    assert conv.message_count == 3
    assert "First hello" in conv.first_message
    assert "Third goodbye" in conv.last_message


def test_recon_conversation_boolean_detection():
    conv = ReconConversation(
        conversation_id="c2",
        title="Detect",
        messages=[
            ReconMessage(text="Codexify Task Prompt\n\nSome content here", timestamp=1.0),
            ReconMessage(text="```python\nprint('hello')\n```", timestamp=2.0),
            ReconMessage(text="Task Summary\n\nDone", timestamp=3.0),
            ReconMessage(
                text="See ![image](test.png) and [file](./data.csv) attachment", timestamp=4.0
            ),
        ],
    )
    assert conv.contains_task_prompt is True
    assert conv.contains_summary is True
    assert conv.contains_code is True
    assert conv.contains_images is True
    assert conv.contains_attachments is True


def test_recon_conversation_false_booleans():
    conv = ReconConversation(
        conversation_id="c3",
        title="Plain",
        messages=[
            ReconMessage(text="Just a normal message.", timestamp=1.0),
            ReconMessage(text="Another normal reply.", timestamp=2.0),
        ],
    )
    assert conv.contains_task_prompt is False
    assert conv.contains_summary is False
    assert conv.contains_code is False
    assert conv.contains_images is False
    assert conv.contains_attachments is False


def test_recon_conversation_empty():
    conv = ReconConversation(conversation_id="c4", title="Empty")
    assert conv.message_count == 0
    assert conv.first_message == ""
    assert conv.last_message == ""
    assert conv.contains_task_prompt is False


def test_recon_conversation_timestamps():
    conv = ReconConversation(
        conversation_id="c5",
        title="Times",
        messages=[
            ReconMessage(text="a", timestamp=10.0),
            ReconMessage(text="b", timestamp=None),
            ReconMessage(text="c", timestamp=20.0),
        ],
    )
    assert conv.first_timestamp == 10.0
    assert conv.last_timestamp == 20.0

    conv2 = ReconConversation(
        conversation_id="c6",
        title="No Times",
        messages=[ReconMessage(text="x", timestamp=None)],
    )
    assert conv2.first_timestamp is None
    assert conv2.last_timestamp is None


# --- Recon engine unit tests ---


def test_recon_scans_legacy_conversations_json(tmp_path: Path):
    export_root = tmp_path / "export"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Hello", 1.0), ("assistant", "Hi there", 2.0)]
            )
        ],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    assert stats.conversations_found == 1
    assert stats.messages_scanned == 2
    assert stats.files_scanned == 1
    assert stats.parse_failures == 0


def test_recon_handles_multiple_conversation_shards(tmp_path: Path):
    export_root = tmp_path / "sharded"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "A", 1.0)], conversation_id="c-a", title="Alpha"
            ),
            _build_mapping_conversation(
                [("user", "B", 2.0)], conversation_id="c-b", title="Beta"
            ),
        ],
        filename="conversations-000.json",
    )
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "C", 3.0)], conversation_id="c-c", title="Gamma"
            ),
        ],
        filename="conversations-001.json",
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    assert stats.conversations_found == 3
    assert stats.messages_scanned == 3
    titles = {c.title for c in stats.conversations}
    assert titles == {"Alpha", "Beta", "Gamma"}


def test_recon_counts_messages_by_year_month(tmp_path: Path):
    export_root = tmp_path / "timed"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Jan 2024", 1704067200.0)],  # 2024-01-01
                conversation_id="t1",
            ),
            _build_mapping_conversation(
                [("user", "Mar 2024", 1709251200.0)],  # 2024-03-01
                conversation_id="t2",
            ),
        ],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    assert stats.messages_by_year[2024] == 2
    assert stats.messages_by_year_month["2024-01"] == 1
    assert stats.messages_by_year_month["2024-03"] == 1


def test_recon_counts_keywords(tmp_path: Path):
    export_root = tmp_path / "keywords"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [("user", "Guardian helps Codexify and Codexify rocks.", 1.0)],
                conversation_id="kw1",
            ),
            _build_mapping_conversation(
                [("user", "Guardian and Scout are great.", 2.0)],
                conversation_id="kw2",
            ),
        ],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    # Per-occurrence: "Codexify" appears twice in kw1.
    assert stats.keyword_counts["Codexify"] == 2
    # "Guardian" appears once in kw1, once in kw2 → 2 occurrences.
    assert stats.keyword_counts["Guardian"] == 2
    assert stats.keyword_counts["Scout"] == 1
    assert stats.keyword_counts.get("PulseOS", 0) == 0


def test_recon_counts_headings(tmp_path: Path):
    export_root = tmp_path / "headings"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [
                    (
                        "user",
                        "## Codexify Task Prompt\n\nDo stuff.\n\n## Task Summary\n\nDid stuff.",
                        1.0,
                    ),
                ],
                conversation_id="h1",
            ),
            _build_mapping_conversation(
                [
                    (
                        "user",
                        "## Objective\n\nLearn.\n\n## Requirements\n\n- item 1",
                        2.0,
                    ),
                ],
                conversation_id="h2",
            ),
        ],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    assert stats.heading_counts["Codexify Task Prompt"] >= 1
    assert stats.heading_counts["Task Summary"] >= 1
    assert stats.heading_counts["Objective"] >= 1
    assert stats.heading_counts["Requirements"] >= 1


def test_recon_task_prompt_variant_counts(tmp_path: Path):
    export_root = tmp_path / "variants"
    export_root.mkdir()
    _write_conversations_json(
        export_root,
        [
            _build_mapping_conversation(
                [
                    (
                        "user",
                        "\n".join(
                            [
                                "Codexify Task Prompt",
                                "",
                                "Objective",
                                "",
                                "Requirements",
                                "",
                                "Implementation Notes",
                                "",
                                "Task Summary",
                                "",
                                "Definition of Done",
                                "",
                                "Files Changed",
                                "",
                                "Test Results",
                                "",
                                "Commit",
                                "",
                                "Execution Contract",
                            ]
                        ),
                        1.0,
                    ),
                ],
                conversation_id="v1",
            ),
        ],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    d = stats.to_dict()
    variants = d["task_prompt_summary_variants"]
    assert variants["Codexify Task Prompt"] >= 1
    assert variants["Task Summary"] >= 1
    assert variants["Definition of Done"] >= 1
    assert variants["Files Changed"] >= 1
    assert variants["Test Results"] >= 1
    assert variants["Commit"] >= 1
    assert variants["Execution Contract"] >= 1
    assert variants["Objective"] >= 1
    assert variants["Requirements"] >= 1
    assert variants["Implementation Notes"] >= 1


# --- Asset classification helpers ---


def test_classify_path_family():
    assert _classify_path_family("conversations__abc/foo.dat") == "conversations"
    assert _classify_path_family("workspace/x/y/file.png") == "workspace"
    assert _classify_path_family("files__xyz/bar.dat") == "files"
    assert _classify_path_family("Unassigned/data.bin") == "Unassigned"
    assert (
        _classify_path_family(
            "__export_file_manifests__/conversations.json"
        )
        == "__export_file_manifests__"
    )
    assert _classify_path_family("random/thing.txt") == "unknown"


def test_classify_size_bucket():
    assert _classify_size_bucket(0) == "empty"
    assert _classify_size_bucket(1) == "0-1KB"
    assert _classify_size_bucket(500) == "0-1KB"
    assert _classify_size_bucket(1024) == "1KB-1MB"
    assert _classify_size_bucket(500_000) == "1KB-1MB"
    assert _classify_size_bucket(2_000_000) == "1-10MB"
    assert _classify_size_bucket(50_000_000) == "10-100MB"
    assert _classify_size_bucket(200_000_000) == "100MB+"


def test_is_sharded_path():
    assert _is_sharded_path("conversations__abc/foo.dat") is True
    assert _is_sharded_path("files__xyz/data.dat") is True
    assert _is_sharded_path("workspace 2/something/file.png") is True
    assert _is_sharded_path("Unassigned/random.txt") is False
    assert _is_sharded_path("conversations.json") is False


def test_is_workspace_or_files_asset():
    assert _is_workspace_or_files_asset("workspace/images/photo.jpg") is True
    assert _is_workspace_or_files_asset("files/data.csv") is True
    assert _is_workspace_or_files_asset("conversations__abc/file.dat") is False
    assert _is_workspace_or_files_asset("Unassigned/random") is False


# --- Mapping mainline helpers ---


def test_linearize_mainline_simple_chain():
    mapping = {
        "a": {"id": "a", "parent": None, "children": ["b"], "message": {}},
        "b": {"id": "b", "parent": "a", "children": ["c"], "message": {}},
        "c": {"id": "c", "parent": "b", "children": [], "message": {}},
    }
    chain = _linearize_mainline(mapping, "c")
    assert len(chain) == 3
    assert [node_id for node_id, _ in chain] == ["a", "b", "c"]


def test_linearize_mainline_finds_leaf_when_missing_current():
    mapping = {
        "a": {"id": "a", "parent": None, "children": ["b"], "message": {}},
        "b": {"id": "b", "parent": "a", "children": [], "message": {}},
    }
    chain = _linearize_mainline(mapping, None)
    assert len(chain) == 2
    assert [node_id for node_id, _ in chain] == ["a", "b"]


def test_resolve_active_node_defaults_to_leaf():
    mapping = {
        "a": {"id": "a", "parent": None, "children": ["b"]},
        "b": {"id": "b", "parent": "a", "children": ["c"]},
        "c": {"id": "c", "parent": "b", "children": []},
    }
    result = _resolve_active_node(mapping, None)
    assert result == "c"


# --- Asset / orphan aggregation ---


def test_recon_distinguishes_orphan_vs_workspace_assets(tmp_path: Path):
    export_root = tmp_path / "asset-export"
    ws = export_root / "workspace"
    una = export_root / "Unassigned"
    ws.mkdir(parents=True)
    una.mkdir()

    (ws / "logo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
    (ws / "data.csv").write_text("a,b,c\n1,2,3\n", encoding="utf-8")
    (una / "orphan.dat").write_bytes(b"\xff\xd8\xff" + b"\x00" * 100)

    # Add a conversation shard so it's not counted as orphan
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "test", 1.0)])],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    assert stats.assets_found == 3
    assert stats.orphan_assets_found == 1  # only the Unassigned one


def test_recon_asset_size_bucket_counts(tmp_path: Path):
    export_root = tmp_path / "buckets"
    ws = export_root / "workspace"
    ws.mkdir(parents=True)

    (ws / "tiny.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"x" * 10)  # 0-1KB
    (ws / "big.png").write_bytes(
        b"\x89PNG\r\n\x1a\n" + b"x" * 2048
    )  # 1KB-1MB

    # Add a conversation
    _write_conversations_json(
        export_root,
        [_build_mapping_conversation([("user", "test", 1.0)])],
    )

    recon = OpenAIExportCorpusRecon()
    stats = recon.scan(export_root)

    d = stats.to_dict()
    buckets = d["asset_orphan_breakdown"]["by_size_bucket"]
    assert buckets.get("0-1KB", 0) >= 1
    assert buckets.get("1KB-1MB", 0) >= 1


# --- Output file tests ---


def test_write_conversation_index_csv(tmp_path: Path):
    conversations = [
        ReconConversation(
            conversation_id="c1",
            title="Test",
            messages=[
                ReconMessage(text="First", timestamp=1.0),
                ReconMessage(text="Second", timestamp=2.0),
            ],
        ),
        ReconConversation(
            conversation_id="c2",
            title="Empty",
            messages=[],
        ),
    ]
    output_path = tmp_path / "index.csv"
    write_conversation_index(conversations, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    lines = content.strip().split("\n")
    assert len(lines) == 3  # header + 2 rows
    # Verify fieldnames present
    assert "conversation_id" in lines[0]
    assert "message_count" in lines[0]
    assert "contains_task_prompt" in lines[0]
    # Sorted by message_count descending: c1 (2) before c2 (0)
    assert "c1" in lines[1]
    assert "c2" in lines[2]


def test_write_corpus_stats_json(tmp_path: Path):
    stats = CorpusReconStats()
    stats.files_scanned = 10
    stats.conversations_found = 3
    stats.messages_scanned = 42
    stats.conversations = [
        ReconConversation(
            conversation_id="c1",
            title="Largest",
            messages=[ReconMessage(text=str(i), timestamp=float(i)) for i in range(50)],
        ),
        ReconConversation(
            conversation_id="c2",
            title="Small",
            messages=[ReconMessage(text="hi", timestamp=1.0)],
        ),
    ]
    stats.messages_by_year[2024] = 42
    stats.messages_by_year_month["2024-01"] = 42
    stats.keyword_counts["Codexify"] = 1

    output_path = tmp_path / "stats.json"
    write_corpus_stats(stats, output_path)

    assert output_path.exists()
    data = json.loads(output_path.read_text(encoding="utf-8"))
    assert data["corpus_totals"]["files_scanned"] == 10
    assert data["corpus_totals"]["conversations_found"] == 3
    assert data["corpus_totals"]["messages_scanned"] == 42
    assert data["messages_by_year"]["2024"] == 42
    assert data["largest_conversations"][0]["message_count"] == 50
    assert data["keyword_counts"]["Codexify"] == 1


def test_write_corpus_summary_markdown(tmp_path: Path):
    stats = CorpusReconStats()
    stats.files_scanned = 5
    stats.conversations_found = 2
    stats.messages_scanned = 10
    stats.conversations = [
        ReconConversation(
            conversation_id="c1",
            title="Test Conv",
            messages=[ReconMessage(text="hello", timestamp=1.0)],
        ),
    ]
    stats.messages_by_year[2025] = 10
    stats.keyword_counts["Guardian"] = 2

    output_path = tmp_path / "summary.md"
    write_corpus_summary_markdown(stats, output_path)

    assert output_path.exists()
    content = output_path.read_text(encoding="utf-8")
    assert "OpenAI Export Corpus Reconnaissance Report" in content
    assert "Files scanned: 5" in content
    assert "Conversations found: 2" in content
    assert "Messages scanned: 10" in content
    assert "Guardian" in content


def test_write_recon_report_creates_diagnostics(tmp_path: Path):
    stats = CorpusReconStats()
    stats.files_scanned = 1

    out_dir = tmp_path / "export_archaeology"
    write_recon_report(stats, out_dir)

    diag_dir = out_dir / "diagnostics"
    assert (diag_dir / "recon_report.json").exists()
    assert (diag_dir / "recon_report.md").exists()


def test_run_corpus_recon_full_pipeline(tmp_path: Path):
    export_root = tmp_path / "corpus"
    out_dir = tmp_path / "export_archaeology"

    # Build a realistic synthetic corpus
    conv_root = export_root / "Unassigned" / "conversations__test"
    conv_root.mkdir(parents=True)

    conversations = [
        _build_mapping_conversation(
            [
                ("user", "# Codexify Task Prompt\n\nDo X.", 1704067200.0),
                ("assistant", "```js\nconsole.log(1)\n```", 1704067260.0),
                ("user", "![screenshot](img.png)", 1704067300.0),
            ],
            conversation_id="conv-task",
            title="Task Conv",
        ),
        _build_mapping_conversation(
            [
                ("user", "Plain chat about Guardian.", 1704153600.0),
                ("assistant", "Yes, Guardian works.", 1704153660.0),
            ],
            conversation_id="conv-chat",
            title="Chat Conv",
        ),
    ]
    (conv_root / "conversations-000.json").write_text(
        json.dumps(conversations), encoding="utf-8"
    )

    # Add some asset files
    ws = export_root / "workspace"
    ws.mkdir(parents=True)
    (ws / "photo.jpg").write_bytes(b"\xff\xd8\xff" + b"\x00" * 2000)
    (ws / "doc.pdf").write_bytes(b"%PDF-1.0\n" + b"\x00" * 500)

    # Orphan asset
    unassigned = export_root / "Unassigned"
    (unassigned / "orphan.dat").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)

    stats = run_corpus_recon(export_root, output_dir=out_dir)

    assert stats.conversations_found == 2
    assert stats.messages_scanned == 5
    assert stats.assets_found == 3
    assert stats.orphan_assets_found == 1
    assert stats.messages_by_year[2024] == 5
    assert stats.keyword_counts.get("Guardian", 0) > 0
    assert stats.keyword_counts.get("Codexify", 0) > 0

    assert (out_dir / "conversation_index.csv").exists()
    assert (out_dir / "corpus_stats.json").exists()
    assert (out_dir / "corpus_summary.md").exists()
    assert (out_dir / "diagnostics" / "recon_report.json").exists()
    assert (out_dir / "diagnostics" / "recon_report.md").exists()

    # Verify CSV content
    csv_content = (out_dir / "conversation_index.csv").read_text(encoding="utf-8")
    assert "conv-task" in csv_content
    assert "conv-chat" in csv_content
    assert "true" in csv_content  # task prompt and code booleans
    assert "false" in csv_content  # non-matching booleans

    # Verify JSON content
    json_data = json.loads(
        (out_dir / "corpus_stats.json").read_text(encoding="utf-8")
    )
    assert json_data["corpus_totals"]["conversations_found"] == 2
    assert json_data["corpus_totals"]["messages_scanned"] == 5

    # Verify markdown content
    md_content = (out_dir / "corpus_summary.md").read_text(encoding="utf-8")
    assert "conversations_found" not in md_content.lower()  # Uses friendly names
    assert "Conversations found: 2" in md_content
    assert "Messages scanned: 5" in md_content
