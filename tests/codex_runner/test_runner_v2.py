from __future__ import annotations

import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
root_str = str(ROOT)
if root_str in sys.path:
    sys.path.remove(root_str)
sys.path.insert(0, root_str)

sys.modules.pop("codex_runner", None)
sys.modules.pop("codex_runner.runner", None)

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


def _sample_campaign(
    *,
    date: str = "2026-03-12",
    slug: str = "alpha",
    seq: str = "001",
    tasks: list[dict] | None = None,
) -> dict:
    campaign_id = f"{date}::{slug}::{seq}"
    task_map = {task["id"]: task for task in (tasks or [])}
    return {
        "campaign_id": campaign_id,
        "campaign_slug": slug,
        "campaign_date": date,
        "campaign_seq": seq,
        "depends_on": [],
        "campaign_markdown": "# Campaign",
        "tasks": task_map,
        "materialized": {
            "campaign_doc_path": None,
            "task_artifact_paths": {},
        },
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
        provider="local",
    )
    payload_b = runner.run_inputs_payload(
        repo_root=runner.Path("/tmp/repo"),
        base_ref_sha="deadbeef",
        hashes=hashes,
        pass_index=1,
        execute_mode="dry-run",
        provider="local",
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


def test_task_artifact_paths_do_not_collide_across_campaigns(
    tmp_path: runner.Path,
) -> None:
    task_a = _sample_task("TASK-001-A", "alpha")
    task_b = _sample_task("TASK-001-B", "alpha")
    campaign_a = _sample_campaign(
        date="2026-03-12", slug="alpha", seq="001", tasks=[task_a]
    )
    campaign_b = _sample_campaign(
        date="2026-03-12", slug="alpha", seq="002", tasks=[task_b]
    )

    runner.materialize_campaign_artifacts(tmp_path, campaign_a)
    runner.materialize_campaign_artifacts(tmp_path, campaign_b)

    path_a = campaign_a["materialized"]["task_artifact_paths"][task_a["id"]]
    path_b = campaign_b["materialized"]["task_artifact_paths"][task_b["id"]]

    assert path_a != path_b
    assert "alpha_2026_03_12_001" in path_a
    assert "alpha_2026_03_12_002" in path_b
    assert (tmp_path / path_a).exists()
    assert (tmp_path / path_b).exists()


def test_task_artifact_paths_stable_when_tasks_reordered(
    tmp_path: runner.Path,
) -> None:
    task_two = _sample_task("TASK-002", "beta")
    task_three = _sample_task("TASK-003", "gamma")
    campaign = _sample_campaign(
        date="2026-03-12", slug="alpha", seq="001", tasks=[task_two, task_three]
    )

    runner.materialize_campaign_artifacts(tmp_path, campaign)
    path_before = campaign["materialized"]["task_artifact_paths"][
        task_two["id"]
    ]

    task_one = _sample_task("TASK-001", "alpha")
    campaign["tasks"][task_one["id"]] = task_one
    runner.materialize_campaign_artifacts(tmp_path, campaign)
    path_after = campaign["materialized"]["task_artifact_paths"][task_two["id"]]

    assert path_before == path_after
    assert (tmp_path / path_before).exists()
