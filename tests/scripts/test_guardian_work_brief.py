from __future__ import annotations

import json
from pathlib import Path

from scripts import guardian_work_brief as brief


def _write(root: Path, relative_path: str, content: str) -> Path:
    path = root / relative_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


def test_generate_work_brief_writes_axis_and_codex_packets(
    tmp_path, monkeypatch
) -> None:
    _write(
        tmp_path,
        "docs/architecture/00-current-state.md",
        """## Last updated
2026-05-28

## Current phase
Codexify is in local-first beta hardening on `main`.

## Current supported reality
- Chat completion works on the supported path.
- Upload -> embed -> readback works on the supported path.

## Not yet true / do not assume
- Do not assume delegation is part of the present release promise.

## Active blockers
- Config paths still coexist.
- Queue/worker health still needs explicit proof.

## This week’s priorities
1. Keep supported profile and health aligned.

## Release definition right now
- [x] Supported-profile flags match the local-only beta contract.
""",
    )
    _write(
        tmp_path,
        "docs/audits/latest.json",
        json.dumps(
            {
                "summary": {"pass": 4, "warn": 1, "fail": 0},
                "strongest_domains": ["Core Loop Integrity"],
                "weakest_domains": ["Governance Readiness"],
                "warnings": [],
                "failures": [],
            }
        ),
    )
    _write(
        tmp_path,
        "docs/Marketing/generated/history/run-history.jsonl",
        json.dumps(
            {
                "campaign_id": "CAMPAIGN_TEST",
                "approval_state": "draft",
                "mode": "draft",
            }
        )
        + "\n",
    )

    def fake_git(repo_root: Path, *args: str) -> brief.CommandResult:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return brief.CommandResult(0, "main\n", "")
        if args == ("rev-parse", "--short", "HEAD"):
            return brief.CommandResult(0, "abc123\n", "")
        if args == ("rev-list", "--left-right", "--count", "@{upstream}...HEAD"):
            return brief.CommandResult(0, "0\t0\n", "")
        if args == ("status", "--short", "--branch"):
            return brief.CommandResult(0, "## main...origin/main\n", "")
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(brief, "run_git", fake_git)

    generated = brief.generate_work_brief(
        repo_root=tmp_path,
        output_dir=Path("briefs"),
        brief_date="2026-05-28",
    )

    axis_brief = tmp_path / generated.axis_brief
    codex_task = tmp_path / generated.codex_next_task
    truth_ledger = tmp_path / generated.truth_ledger
    decision_log = tmp_path / generated.decision_log

    assert axis_brief.exists()
    assert codex_task.exists()
    assert truth_ledger.exists()
    assert decision_log.exists()

    axis_text = axis_brief.read_text(encoding="utf-8")
    assert "Guardian Work Brief - 2026-05-28" in axis_text
    assert "Manual Closeout" in axis_text
    assert "Do not assume delegation" in axis_text

    codex_text = codex_task.read_text(encoding="utf-8")
    assert "Acceptance Criteria" in codex_text
    assert "Config paths still coexist." in codex_text

    payload = json.loads(truth_ledger.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "guardian-work-brief/v1"
    assert payload["decision"]["focus"] == "Config paths still coexist."
    assert payload["drift"][0]["kind"] == "release_claim_boundary"


def test_dirty_or_behind_repo_becomes_decision_focus(tmp_path, monkeypatch) -> None:
    _write(
        tmp_path,
        "docs/architecture/00-current-state.md",
        """## Current phase
Beta hardening.

## Active blockers
- Config paths still coexist.
""",
    )

    def fake_git(repo_root: Path, *args: str) -> brief.CommandResult:
        if args == ("rev-parse", "--abbrev-ref", "HEAD"):
            return brief.CommandResult(0, "main\n", "")
        if args == ("rev-parse", "--short", "HEAD"):
            return brief.CommandResult(0, "abc123\n", "")
        if args == ("rev-list", "--left-right", "--count", "@{upstream}...HEAD"):
            return brief.CommandResult(0, "2\t0\n", "")
        if args == ("status", "--short", "--branch"):
            return brief.CommandResult(
                0,
                "## main...origin/main [behind 2]\n M docs/audits/latest.json\n",
                "",
            )
        raise AssertionError(f"Unexpected git args: {args}")

    monkeypatch.setattr(brief, "run_git", fake_git)

    ledger = brief.build_truth_ledger(tmp_path, "2026-05-28")

    assert ledger["decision"]["focus"] == (
        "Synchronize the working branch before making release claims."
    )
    assert [item["kind"] for item in ledger["drift"]] == [
        "repo_sync",
        "dirty_worktree",
    ]
