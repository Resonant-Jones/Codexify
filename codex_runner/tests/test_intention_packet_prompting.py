from __future__ import annotations

import json
from pathlib import Path

import pytest
import runner


PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


def _write_required_runner_files(tmp_path: Path) -> dict[str, Path]:
    paths = {
        "audit_prompt": tmp_path / "audit.md",
        "audit_schema": tmp_path / "audit.schema.json",
        "compiler_prompt": tmp_path / "compiler.md",
        "campaign_schema": tmp_path / "campaign.schema.json",
        "task_schema": tmp_path / "task.schema.json",
    }
    for path in paths.values():
        path.write_text("{}", encoding="utf-8")
    return paths


def test_prompt_assembly_without_intention_packet_uses_fallback() -> None:
    audit_prompt = runner.render_audit_prompt(
        "Intention:\n<INTENTION_PACKET>\nAudit: <AUDIT_ID>",
        Path("/repo"),
        "AUDIT_abc123def456",
        "abc123def456",
    )
    compiler_prompt = runner.render_compiler_prompt(
        "Intention:\n<INTENTION_PACKET>\nAudit: <PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>",
        Path("/repo"),
        {"audit_id": "AUDIT_abc123def456"},
    )

    assert runner.DEFAULT_INTENTION_PACKET_TEXT in audit_prompt
    assert runner.DEFAULT_INTENTION_PACKET_TEXT in compiler_prompt
    assert runner.DEFAULT_INTENTION_PACKET_TEXT == (
        "No explicit intention packet was provided. Use the default "
        "repository-grounded audit posture and do not infer a narrower target."
    )


def test_stage_a_prompt_doctrine_interprets_canonical_packet_sections() -> None:
    prompt_template = (PROMPT_DIR / "mega_audit.md").read_text(
        encoding="utf-8"
    )

    rendered = runner.render_audit_prompt(
        prompt_template,
        Path("/repo"),
        "AUDIT_abc123def456",
        "abc123def456",
    )

    assert (
        "separate repo-grounded findings, unsupported intention claims, "
        "and unknowns requiring discovery"
    ) in rendered
    for section_name in (
        "`Objective`",
        "`Scope`",
        "`Evidence Requirements`",
        "`Failure / Stop Conditions`",
    ):
        assert section_name in rendered


def test_stage_b_prompt_doctrine_interprets_canonical_packet_sections() -> None:
    prompt_template = (
        PROMPT_DIR / "audit_report_to_campaign_runner.md"
    ).read_text(encoding="utf-8")

    rendered = runner.render_compiler_prompt(
        prompt_template,
        Path("/repo"),
        {"audit_id": "AUDIT_abc123def456", "findings": []},
    )

    assert (
        "Stage B must not invent campaigns or tasks unsupported by "
        "Stage-A evidence"
    ) in rendered
    assert "Do not invent tasks from packet intent alone" in rendered
    for lane in (
        "`standard`",
        "`architecture_impact`",
        "`discovery`",
        "`docs_only`",
        "`proof_runbook`",
    ):
        assert lane in rendered
    assert (
        "When uncertain between `standard` and `architecture_impact`, "
        "choose `architecture_impact`"
    ) in rendered
    for section_name in (
        "`Stage B Campaign Posture`",
        "`Task-Lane Expectations`",
        "`Release-Truth Constraints`",
    ):
        assert section_name in rendered


def test_prompt_assembly_injects_intention_packet_into_both_stages(
    tmp_path: Path,
) -> None:
    packet_path = tmp_path / "intention.md"
    packet_body = (
        "# Operator Intention\n\n"
        "- Scope: Campaign Runner prompt seam only.\n"
        "- Non-goal: no provider behavior changes.\n"
    )
    packet_path.write_text(packet_body, encoding="utf-8")
    packet_text = runner.load_intention_packet(packet_path)

    audit_prompt = runner.render_audit_prompt(
        "Intention:\n<INTENTION_PACKET>\nAudit: <AUDIT_ID>",
        Path("/repo"),
        "AUDIT_abc123def456",
        "abc123def456",
        packet_text,
    )
    compiler_prompt = runner.render_compiler_prompt(
        "Intention:\n<INTENTION_PACKET>\nAudit: <PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>",
        Path("/repo"),
        {"audit_id": "AUDIT_abc123def456"},
        packet_text,
    )

    assert packet_body in audit_prompt
    assert packet_body in compiler_prompt
    assert runner.DEFAULT_INTENTION_PACKET_TEXT not in audit_prompt
    assert runner.DEFAULT_INTENTION_PACKET_TEXT not in compiler_prompt


def test_intention_packet_text_is_preserved_exactly(tmp_path: Path) -> None:
    packet_path = tmp_path / "intention.md"
    packet_body = "Line one\n\nLine two with trailing spaces.  \n"
    packet_path.write_text(packet_body, encoding="utf-8")

    assert runner.load_intention_packet(packet_path) == packet_body


def test_intention_packet_does_not_mutate_runner_owned_placeholders() -> None:
    packet_text = (
        "Packet literals: <REPO_ROOT> <AUDIT_ID> <RUN_ID> "
        "<PASTE MEGA_AUDIT_OUTPUT_JSON_HERE> <AUDIT_JSON>"
    )
    audit_prompt = runner.render_audit_prompt(
        (
            "Repo: <REPO_ROOT>\n"
            "Audit: <AUDIT_ID>\n"
            "Run: <RUN_ID>\n"
            "Packet:\n<INTENTION_PACKET>"
        ),
        Path("/repo"),
        "AUDIT_abc123def456",
        "abc123def456",
        packet_text,
    )

    assert "Repo: /repo" in audit_prompt
    assert "Audit: AUDIT_abc123def456" in audit_prompt
    assert "Run: abc123def456" in audit_prompt
    assert packet_text in audit_prompt

    audit_payload = {
        "audit_id": "AUDIT_abc123def456",
        "note": "<INTENTION_PACKET> <REPO_ROOT> <AUDIT_JSON>",
    }
    compiler_prompt = runner.render_compiler_prompt(
        (
            "Repo: <REPO_ROOT>\n"
            "Audit: <PASTE MEGA_AUDIT_OUTPUT_JSON_HERE>\n"
            "Packet:\n<INTENTION_PACKET>"
        ),
        Path("/repo"),
        audit_payload,
        packet_text,
    )

    assert "Repo: /repo" in compiler_prompt
    assert packet_text in compiler_prompt
    pasted_json = json.dumps(audit_payload, indent=2, ensure_ascii=False)
    assert pasted_json in compiler_prompt


def test_missing_intention_packet_path_fails_clearly(tmp_path: Path) -> None:
    missing = tmp_path / "missing-intention.md"

    with pytest.raises(
        runner.RunnerError, match="Intention packet file not found"
    ):
        runner.load_intention_packet(missing)


def test_parse_args_validates_missing_intention_packet_path(
    tmp_path: Path,
) -> None:
    paths = _write_required_runner_files(tmp_path)
    missing = tmp_path / "missing-intention.md"

    with pytest.raises(
        runner.RunnerError, match="Intention packet file not found"
    ):
        runner.parse_args(
            [
                "--repo-root",
                str(tmp_path),
                "--audit-prompt-file",
                str(paths["audit_prompt"]),
                "--audit-schema-file",
                str(paths["audit_schema"]),
                "--compiler-prompt-file",
                str(paths["compiler_prompt"]),
                "--campaign-set-schema-file",
                str(paths["campaign_schema"]),
                "--task-result-schema-file",
                str(paths["task_schema"]),
                "--intention-packet-file",
                str(missing),
                "--dry-run",
            ]
        )


def test_parse_args_accepts_intention_packet_file(tmp_path: Path) -> None:
    paths = _write_required_runner_files(tmp_path)
    packet_path = tmp_path / "intention.md"
    packet_path.write_text("intent", encoding="utf-8")

    args = runner.parse_args(
        [
            "--repo-root",
            str(tmp_path),
            "--audit-prompt-file",
            str(paths["audit_prompt"]),
            "--audit-schema-file",
            str(paths["audit_schema"]),
            "--compiler-prompt-file",
            str(paths["compiler_prompt"]),
            "--campaign-set-schema-file",
            str(paths["campaign_schema"]),
            "--task-result-schema-file",
            str(paths["task_schema"]),
            "--intention-packet-file",
            str(packet_path),
            "--dry-run",
        ]
    )

    assert args.intention_packet_file == packet_path.resolve()


def test_directory_intention_packet_path_fails_clearly(tmp_path: Path) -> None:
    with pytest.raises(
        runner.RunnerError, match="Intention packet path is a directory"
    ):
        runner.load_intention_packet(tmp_path)
