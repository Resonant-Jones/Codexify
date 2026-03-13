from __future__ import annotations

import pytest

from codex_runner import runner


def _sample_task(task_id: str = "TASK-001", slug: str = "alpha") -> dict:
    return {
        "id": task_id,
        "slug": slug,
        "area": "backend",
        "risk": "HIGH",
        "files": ["backend/app.py"],
        "tests": ["pytest -q tests/test_app.py"],
        "commit_message": "Implement alpha",
        "task_artifact_markdown": "# Task",
        "activation_prompt": "Do task",
        "dependencies": [],
    }


def test_run_id_determinism() -> None:
    hashes = runner.StageHashes(
        audit_prompt_sha256="a" * 64,
        audit_schema_sha256="b" * 64,
        compiler_prompt_sha256="c" * 64,
        campaign_set_schema_sha256="d" * 64,
    )

    payload_a = runner.run_inputs_payload(
        repo_root=runner.Path("/tmp/repo"),
        base_ref_sha="deadbeef",
        hashes=hashes,
        pass_index=1,
        execute_mode="dry-run",
        provider="codex",
    )
    payload_b = runner.run_inputs_payload(
        repo_root=runner.Path("/tmp/repo"),
        base_ref_sha="deadbeef",
        hashes=hashes,
        pass_index=1,
        execute_mode="dry-run",
        provider="codex",
    )

    run_id_a = runner.sha256_text(runner.canonical_json(payload_a))[:12]
    run_id_b = runner.sha256_text(runner.canonical_json(payload_b))[:12]
    assert run_id_a == run_id_b


def test_parse_campaign_id_validation() -> None:
    date, slug, seq = runner.parse_campaign_id(
        "2026-02-18::security_alpha::007"
    )
    assert date == "2026-02-18"
    assert slug == "security_alpha"
    assert seq == "007"

    with pytest.raises(runner.RunnerError):
        runner.parse_campaign_id("CAMPAIGN_2026_02_18_SECURITY")


def test_merge_conflict_when_task_content_changes() -> None:
    state = {
        "version": 1,
        "campaigns": {},
        "task_index_by_id": {},
        "task_index_by_slug": {},
    }

    payload_1 = {
        "campaigns": [
            {
                "campaign_id": "2026-02-18::security_alpha::001",
                "campaign_slug": "security_alpha",
                "depends_on": [],
                "campaign_markdown": "# Campaign",
                "tasks": [_sample_task("TASK-001", "alpha")],
            }
        ]
    }

    payload_2 = {
        "campaigns": [
            {
                "campaign_id": "2026-02-18::security_alpha::001",
                "campaign_slug": "security_alpha",
                "depends_on": [],
                "campaign_markdown": "# Campaign",
                "tasks": [
                    {
                        **_sample_task("TASK-001", "alpha"),
                        "commit_message": "Different commit message",
                    }
                ],
            }
        ]
    }

    runner.merge_campaign_set(state, payload_1, audit_id="AUDIT_aaaaaaaaaaaa")

    with pytest.raises(runner.RunnerError):
        runner.merge_campaign_set(
            state, payload_2, audit_id="AUDIT_bbbbbbbbbbbb"
        )


def test_mapping_block_updates_only_within_markers(
    tmp_path: runner.Path,
) -> None:
    path = tmp_path / "campaign.md"
    path.write_text(
        "prefix\n"
        "<!-- RUNNER_TASK_MAP -->\n"
        "TASK_X -> [old_impl, old_receipt]\n"
        "<!-- /RUNNER_TASK_MAP -->\n"
        "suffix\n",
        encoding="utf-8",
    )

    runner.update_mapping_block(path, "TASK_A", "impl123", "SELF")
    content = path.read_text(encoding="utf-8")

    assert content.startswith("prefix\n")
    assert content.rstrip().endswith("suffix")
    assert "TASK_A -> [impl123, SELF]" in content


def test_select_campaign_risk_then_date_then_slug() -> None:
    state = {
        "version": 1,
        "campaigns": {
            "2026-02-18::beta::001": {
                "campaign_id": "2026-02-18::beta::001",
                "campaign_slug": "beta",
                "campaign_date": "2026-02-18",
                "campaign_seq": "001",
                "depends_on": [],
                "tasks": {
                    "T1": {"risk": "HIGH", "status": "pending"},
                },
                "status": "open",
            },
            "2026-02-17::alpha::001": {
                "campaign_id": "2026-02-17::alpha::001",
                "campaign_slug": "alpha",
                "campaign_date": "2026-02-17",
                "campaign_seq": "001",
                "depends_on": [],
                "tasks": {
                    "T2": {"risk": "HIGH", "status": "pending"},
                    "T3": {"risk": "HIGH", "status": "pending"},
                },
                "status": "open",
            },
        },
        "task_index_by_id": {},
        "task_index_by_slug": {},
    }

    selected = runner.select_campaign(state)
    assert selected is not None
    assert selected.campaign_id == "2026-02-17::alpha::001"


def test_normalize_repo_relative_path_rejects_parent_segments() -> None:
    with pytest.raises(runner.RunnerError):
        runner.normalize_repo_relative_path("../secrets.txt")

    with pytest.raises(runner.RunnerError):
        runner.normalize_repo_relative_path("/absolute/path.txt")

    assert (
        runner.normalize_repo_relative_path("backend/app.py")
        == "backend/app.py"
    )
