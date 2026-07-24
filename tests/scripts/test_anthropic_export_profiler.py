"""Synthetic tests for the read-only Anthropic account-export profiler.

These tests use ONLY temporary synthetic files. No real Anthropic export and no
real profile report is ever committed or read here. The profiler is loaded
directly from its script path so the test exercises the real standalone module.
"""

from __future__ import annotations

import importlib.util
import json
import os
import stat
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "anthropic_import" / "profile_anthropic_export.py"


@pytest.fixture(scope="module")
def profiler():
    spec = importlib.util.spec_from_file_location(
        "anthropic_export_profiler", SCRIPT_PATH
    )
    module = importlib.util.module_from_spec(spec)
    # Register before exec so dataclass annotation resolution can find the module.
    sys.modules["anthropic_export_profiler"] = module
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------
# Synthetic data builders
# --------------------------------------------------------------------------

CANARY_TEXT = "CANARY_MESSAGE_TEXT_hunter2_secret"
CANARY_TITLE = "CANARY_TITLE_SecretProjectAlpha"
CANARY_UUID = "11111111-2222-3333-4444-555555555555"
CANARY_EMAIL = "canary-user@example.com"
CANARY_MSG_UUID_A = "aaaaaaaa-0000-0000-0000-000000000001"
CANARY_MSG_UUID_B = "aaaaaaaa-0000-0000-0000-000000000002"
CANARY_MODEL = "claude-test-opus"
CANARY_ATTACHMENT = "invoice-canary.png"


def _claude_conversation() -> dict:
    return {
        "uuid": CANARY_UUID,
        "name": CANARY_TITLE,
        "account": {"email_address": CANARY_EMAIL},
        "chat_messages": [
            {
                "uuid": CANARY_MSG_UUID_A,
                "sender": "human",
                "text": CANARY_TEXT,
                "created_at": "2026-01-02T03:04:05Z",
                "updated_at": "2026-01-02T03:04:05Z",
                "parent_message_uuid": None,
            },
            {
                "uuid": CANARY_MSG_UUID_B,
                "sender": "assistant",
                "model": CANARY_MODEL,
                "created_at": "2026-01-02T03:05:06Z",
                "updated_at": "2026-01-02T03:05:06Z",
                "parent_message_uuid": CANARY_MSG_UUID_A,
                "content": [
                    {"type": "text", "text": "structured answer canary"},
                    {"type": "tool_use", "name": "search"},
                ],
                "attachments": [{"file_name": CANARY_ATTACHMENT}],
            },
        ],
    }


def _write_zip(path: Path, members: dict[str, bytes | str]) -> Path:
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, payload in members.items():
            if isinstance(payload, bytes):
                bundle.writestr(name, payload)
            else:
                bundle.writestr(name, payload)
    return path


def _write_symlink_zip(path: Path, link_name: str, target: str) -> Path:
    with zipfile.ZipFile(path, "w") as bundle:
        info = zipfile.ZipInfo(link_name)
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        bundle.writestr(info, target)
    return path


def _serialize(profiler, report: dict) -> str:
    return profiler.serialize_report(report)


# --------------------------------------------------------------------------
# 1. Flat conversation array with chat_messages
# --------------------------------------------------------------------------


def test_profiles_zip_with_chat_messages_container(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([_claude_conversation()])},
    )
    report = profiler.profile_export(str(archive))

    assert report["report_schema"] == "anthropic_export_profile_report_v1"
    assert report["profiler_version"] == "1"
    assert report["package"]["kind"] == "zip"
    shape = report["conversation_shape"]
    assert shape["conversations_observed"] is True
    assert shape["candidate_conversation_count"] == 1
    assert any(c["key"] == "chat_messages" for c in shape["message_container_keys"])
    conv_cands = [
        c for c in report["candidate_surfaces"] if c["classification"] == "conversations"
    ]
    assert conv_cands, "expected a conversations candidate surface"


# --------------------------------------------------------------------------
# 2. Detects sender/ids/timestamps/model/project refs without raw values
# --------------------------------------------------------------------------


def test_detects_structural_fields_without_raw_values(profiler, tmp_path):
    conv = _claude_conversation()
    conv["project_uuid"] = "proj-canary-123"
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([conv])},
    )
    report = profiler.profile_export(str(archive))
    shape = report["conversation_shape"]

    role_fields = {c["key"] for c in shape["role_field_names"]}
    assert "sender" in role_fields
    role_values = {c["key"] for c in shape["role_values"]}
    assert {"human", "assistant"} <= role_values

    ts_fields = {c["key"] for c in shape["timestamp_field_names"]}
    assert {"created_at", "updated_at"} <= ts_fields
    formats = {c["key"] for c in shape["timestamp_format_categories"]}
    assert "iso8601" in formats

    model_fields = {c["key"] for c in shape["model_field_names"]}
    assert "model" in model_fields

    id_fields = {c["key"] for c in shape["identifier_field_names"]}
    assert {"uuid", "parent_message_uuid"} <= id_fields

    proj_refs = {c["key"] for c in shape["project_reference_field_names"]}
    assert "project_uuid" in proj_refs

    block_types = {c["key"] for c in shape["content_block_types"]}
    assert {"text", "tool_use"} <= block_types

    # Structural evidence must not leak any raw values.
    blob = _serialize(profiler, report)
    for canary in (
        CANARY_TEXT,
        CANARY_TITLE,
        CANARY_EMAIL,
        CANARY_UUID,
        CANARY_MSG_UUID_A,
        CANARY_MODEL,
        CANARY_ATTACHMENT,
        "proj-canary-123",
        "structured answer canary",
    ):
        assert canary not in blob


# --------------------------------------------------------------------------
# 3. Branch structure (parent_message_uuid)
# --------------------------------------------------------------------------


def test_detects_parent_message_branch_structure(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([_claude_conversation()])},
    )
    report = profiler.profile_export(str(archive))
    parent_fields = {c["key"] for c in report["conversation_shape"]["parent_relationship_field_names"]}
    assert "parent_message_uuid" in parent_fields
    assert report["capabilities_observed"]["message_parent_links"]["observed"] is True
    codes = {w["code"] for w in report["warnings"]}
    assert "possible_branch_structure" in codes


# --------------------------------------------------------------------------
# 4. projects.json / users.json / memories.json candidate surfaces
# --------------------------------------------------------------------------


def test_profiles_projects_users_memories_surfaces(profiler, tmp_path):
    members = {
        "projects.json": json.dumps(
            [{"project_uuid": "p1", "name": "P", "description": "d"}]
        ),
        "users.json": json.dumps(
            [{"email_address": CANARY_EMAIL, "full_name": "Name Canary", "uuid": CANARY_UUID}]
        ),
        "memories.json": json.dumps(
            [{"memory": "remembered canary", "memory_id": "m1"}]
        ),
    }
    archive = _write_zip(tmp_path / "export.zip", members)
    report = profiler.profile_export(str(archive))

    classifications = {
        (c["relative_path"], c["classification"]) for c in report["candidate_surfaces"]
    }
    assert ("projects.json", "projects") in classifications
    assert ("users.json", "users_or_account") in classifications
    assert ("memories.json", "memories") in classifications

    caps = report["capabilities_observed"]
    assert caps["project_records"]["observed"] is True
    assert caps["account_metadata"]["observed"] is True
    assert caps["memory_records"]["observed"] is True

    blob = _serialize(profiler, report)
    for canary in (CANARY_EMAIL, CANARY_UUID, "Name Canary", "remembered canary"):
        assert canary not in blob


# --------------------------------------------------------------------------
# 5. Binary members inventoried, not parsed as JSON
# --------------------------------------------------------------------------


def test_inventories_binary_members_without_json_parse(profiler, tmp_path):
    png = b"\x89PNG\r\n\x1a\n" + b"\x00" * 32
    archive = _write_zip(
        tmp_path / "export.zip",
        {
            "conversations.json": json.dumps([_claude_conversation()]),
            "media/photo.png": png,
        },
    )
    report = profiler.profile_export(str(archive))
    by_path = {f["relative_path"]: f for f in report["files"]}
    png_record = by_path["media/photo.png"]
    assert png_record["broad_type"] == "image"
    assert png_record["json_parse_status"] == "not_json"
    assert png_record["sha256"] != ""
    assert report["capabilities_observed"]["binary_payloads"]["observed"] is True


# --------------------------------------------------------------------------
# 6. Attachment / generated-file / artifact hints distinguished
# --------------------------------------------------------------------------


def test_distinguishes_attachment_generated_and_artifact_hints(profiler, tmp_path):
    conv = {
        "uuid": CANARY_UUID,
        "chat_messages": [
            {
                "uuid": CANARY_MSG_UUID_A,
                "sender": "user",
                "content": [{"type": "text", "text": "x"}],
                "attachments": [{"file_id": "CANARY_FILE_TOKEN"}],
            },
            {
                "uuid": CANARY_MSG_UUID_B,
                "sender": "assistant",
                "content": [
                    {
                        "type": "image",
                        "generated": True,
                        "generation": "CANARY_GEN_TOKEN",
                    }
                ],
                "artifacts": [{"artifact_id": "CANARY_ARTIFACT_TOKEN"}],
            },
        ],
    }
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([conv])},
    )
    report = profiler.profile_export(str(archive))
    caps = report["capabilities_observed"]
    assert caps["attachment_references"]["observed"] is True
    assert caps["generated_file_evidence"]["observed"] is True
    assert caps["artifact_evidence"]["observed"] is True

    blob = _serialize(profiler, report)
    # Distinctive, non-hex tokens so they cannot collide with sha256 hex.
    for token in ("CANARY_GEN_TOKEN", "CANARY_ARTIFACT_TOKEN", "CANARY_FILE_TOKEN"):
        assert token not in blob


# --------------------------------------------------------------------------
# 7. Malformed JSON -> bounded warning, rest preserved
# --------------------------------------------------------------------------


def test_malformed_json_reported_as_warning(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {
            "conversations.json": json.dumps([_claude_conversation()]),
            "broken.json": "{not valid json,,,",
        },
    )
    report = profiler.profile_export(str(archive))
    by_path = {f["relative_path"]: f for f in report["files"]}
    assert by_path["broken.json"]["json_parse_status"] == "failed"
    codes = {(w["code"], w["relative_path"]) for w in report["warnings"]}
    assert ("json_parse_failed", "broken.json") in codes
    # Rest of inventory preserved.
    assert by_path["conversations.json"]["json_parse_status"] == "ok"
    assert report["conversation_shape"]["conversations_observed"] is True


# --------------------------------------------------------------------------
# 8-11. ZIP structural rejections
# --------------------------------------------------------------------------


def test_rejects_zip_traversal_path(profiler, tmp_path):
    archive = _write_zip(tmp_path / "export.zip", {"../escape.json": "[]"})
    with pytest.raises(profiler.UnsafePackageError) as exc:
        profiler.profile_export(str(archive))
    assert exc.value.code == "path_traversal_rejected"


def test_rejects_zip_absolute_path(profiler, tmp_path):
    archive = _write_zip(tmp_path / "export.zip", {"/etc/host.json": "[]"})
    with pytest.raises(profiler.UnsafePackageError) as exc:
        profiler.profile_export(str(archive))
    assert exc.value.code == "absolute_path_rejected"


def test_rejects_zip_symbolic_link(profiler, tmp_path):
    archive = _write_symlink_zip(tmp_path / "export.zip", "link.json", "/etc/passwd")
    with pytest.raises(profiler.UnsafePackageError) as exc:
        profiler.profile_export(str(archive))
    assert exc.value.code == "symlink_rejected"


def test_rejects_normalized_duplicate_member_path(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"data.json": "[]", "./data.json": "[]"},
    )
    with pytest.raises(profiler.UnsafePackageError) as exc:
        profiler.profile_export(str(archive))
    assert exc.value.code == "duplicate_path_rejected"


# --------------------------------------------------------------------------
# 12. Directory symlink rejection
# --------------------------------------------------------------------------


def test_rejects_directory_symbolic_link(profiler, tmp_path):
    root = tmp_path / "extracted"
    root.mkdir()
    (root / "real.json").write_text("[]")
    (root / "link.json").symlink_to(os.path.join(str(root), "real.json"))
    with pytest.raises(profiler.UnsafePackageError) as exc:
        profiler.profile_export(str(root))
    assert exc.value.code == "symlink_rejected"


# --------------------------------------------------------------------------
# 13. Deterministic / identical reports across repeated runs
# --------------------------------------------------------------------------


def test_repeated_runs_produce_identical_reports(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {
            "conversations.json": json.dumps([_claude_conversation()]),
            "projects.json": json.dumps([{"project_id": "p", "name": "n"}]),
        },
    )
    first = profiler.serialize_report(profiler.profile_export(str(archive)))
    second = profiler.serialize_report(profiler.profile_export(str(archive)))
    assert first == second
    # JSON is sorted + two-space indent + trailing newline.
    assert first.endswith("\n")
    assert "\n  \"" in first  # 2-space indentation present


# --------------------------------------------------------------------------
# 14-18. Sensitive-data boundary (no text/title/uuid/email/abs-path)
# --------------------------------------------------------------------------


def test_sensitive_data_boundary(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {
            "conversations.json": json.dumps([_claude_conversation()]),
            "users.json": json.dumps(
                [{"email_address": CANARY_EMAIL, "uuid": CANARY_UUID, "full_name": "Name"}]
            ),
            "projects/11111111-2222-3333-4444-555555555555.json": json.dumps(
                {"name": CANARY_TITLE, "description": "d", "uuid": CANARY_UUID}
            ),
        },
    )
    report = profiler.profile_export(str(archive))
    blob = _serialize(profiler, report)

    # 14. no message text
    assert CANARY_TEXT not in blob
    # 15. no conversation/project titles
    assert CANARY_TITLE not in blob
    # 16. no synthetic UUID values (also redacted from the project filename)
    assert CANARY_UUID not in blob
    # 17. no email addresses
    assert CANARY_EMAIL not in blob
    # 18. no absolute source path
    assert str(tmp_path) not in blob
    assert str(archive.parent) not in blob

    # UUID-shaped project filename is scrubbed but still inventoried uniquely.
    project_paths = [
        f["relative_path"] for f in report["files"] if f["relative_path"].startswith("projects/")
    ]
    assert project_paths == ["projects/<uuid>.json"]


# --------------------------------------------------------------------------
# 19. Truncation when a configured limit is exceeded
# --------------------------------------------------------------------------


def test_reports_truncation_on_file_count_limit(profiler, tmp_path, monkeypatch):
    monkeypatch.setattr(profiler, "MAX_PACKAGE_FILE_COUNT", 2)
    members = {f"f{i}.json": json.dumps([{"name": f"n{i}"}]) for i in range(5)}
    archive = _write_zip(tmp_path / "export.zip", members)
    report = profiler.profile_export(str(archive))

    assert report["package"]["analysis_truncated"] is True
    assert report["package"]["file_count"] == 2
    codes = {w["code"] for w in report["warnings"]}
    assert "analysis_limit_reached" in codes


# --------------------------------------------------------------------------
# 20. Direct JSON-file input
# --------------------------------------------------------------------------


def test_supports_direct_json_file_input(profiler, tmp_path):
    json_path = tmp_path / "single.json"
    json_path.write_text(json.dumps([_claude_conversation()]))
    report = profiler.profile_export(str(json_path))

    assert report["package"]["kind"] == "json"
    assert report["package"]["file_count"] == 1
    assert report["conversation_shape"]["conversations_observed"] is True
    assert report["files"][0]["relative_path"] == "single.json"


# --------------------------------------------------------------------------
# 21. Extracted-directory input
# --------------------------------------------------------------------------


def test_supports_extracted_directory_input(profiler, tmp_path):
    root = tmp_path / "export"
    root.mkdir()
    (root / "conversations.json").write_text(json.dumps([_claude_conversation()]))
    (root / "media").mkdir()
    (root / "media" / "photo.png").write_bytes(b"\x89PNG\r\n\x1a\n" + b"\x00" * 16)

    report = profiler.profile_export(str(root))
    assert report["package"]["kind"] == "directory"
    paths = {f["relative_path"] for f in report["files"]}
    assert {"conversations.json", "media/photo.png"} <= paths
    assert report["conversation_shape"]["conversations_observed"] is True
    assert report["capabilities_observed"]["binary_payloads"]["observed"] is True


# --------------------------------------------------------------------------
# 22. Documented CLI exit codes
# --------------------------------------------------------------------------


def test_cli_exit_codes_via_main(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([_claude_conversation()])},
    )
    out = tmp_path / "report.json"

    # 0: success
    rc = profiler.main([str(archive), "--output", str(out)])
    assert rc == profiler.EXIT_OK
    assert out.exists()
    assert json.loads(out.read_text())["report_schema"]

    # 2: missing input
    rc = profiler.main([str(tmp_path / "missing.zip"), "--output", str(out)])
    assert rc == profiler.EXIT_USAGE

    # 2: unsupported input type (non-zip, non-json file)
    other = tmp_path / "data.bin"
    other.write_bytes(b"\x00\x01\x02\x03")
    rc = profiler.main([str(other), "--output", str(out)])
    assert rc == profiler.EXIT_USAGE

    # 3: unsafe archive
    bad = _write_zip(tmp_path / "bad.zip", {"../escape.json": "[]"})
    rc = profiler.main([str(bad), "--output", str(out)])
    assert rc == profiler.EXIT_UNSAFE


def test_cli_exit_codes_via_subprocess(tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([_claude_conversation()])},
    )
    out = tmp_path / "report.json"
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), str(archive), "--output", str(out)],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert "Anthropic export profile complete" in result.stdout
    assert "package_kind: zip" in result.stdout
    assert "file_count:" in result.stdout
    report = json.loads(out.read_text())
    assert report["report_schema"] == "anthropic_export_profile_report_v1"
    assert report["errors"] == []


# --------------------------------------------------------------------------
# Extra invariants: no Codexify runtime dependency, no extraction to disk
# --------------------------------------------------------------------------


def test_no_codexify_runtime_dependency_imported():
    source = SCRIPT_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "import guardian",
        "from guardian",
        "import backend",
        "from backend",
        "import redis",
        "import sqlalchemy",
        "import psycopg2",
    ):
        assert forbidden not in source, f"profiler must not import {forbidden!r}"


def test_zip_members_are_not_extracted_to_disk(profiler, tmp_path, monkeypatch):
    archive = _write_zip(
        tmp_path / "export.zip",
        {
            "conversations.json": json.dumps([_claude_conversation()]),
            "nested/deep/secret.json": json.dumps({"a": 1}),
        },
    )
    extracted_before = set(p for p in tmp_path.rglob("*") if p.is_file())
    profiler.profile_export(str(archive))
    extracted_after = set(p for p in tmp_path.rglob("*") if p.is_file())
    # Only the archive itself should exist; no member files materialized.
    new_files = extracted_after - extracted_before
    assert new_files == set(), f"unexpected files appeared: {new_files}"


def test_report_has_required_top_level_fields(profiler, tmp_path):
    archive = _write_zip(
        tmp_path / "export.zip",
        {"conversations.json": json.dumps([_claude_conversation()])},
    )
    report = profiler.profile_export(str(archive))
    expected = {
        "report_schema",
        "profiler_version",
        "package",
        "files",
        "candidate_surfaces",
        "conversation_shape",
        "capabilities_observed",
        "unknown_structures",
        "warnings",
        "errors",
    }
    assert expected <= set(report.keys())
    assert set(report.keys()) == expected
    for key in (
        "kind",
        "display_name",
        "sha256",
        "file_count",
        "json_file_count",
        "binary_file_count",
        "total_bytes",
        "analysis_truncated",
    ):
        assert key in report["package"]
