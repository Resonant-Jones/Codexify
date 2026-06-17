from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

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


def _prompt_content(
    tmp_path: runner.Path, campaign: dict, task_id: str
) -> tuple[str, str]:
    prompt_path = campaign["materialized"]["task_prompt_artifact_paths"][
        task_id
    ]
    return prompt_path, (tmp_path / prompt_path).read_text(encoding="utf-8")


def _assert_single_fenced_prompt(content: str) -> None:
    assert content.startswith("```text\n")
    assert content.endswith("\n```\n")
    assert content.count("```") == 2


def _sample_audit_payload(audit_id: str = "AUDIT_abc123def456") -> dict:
    return {
        "audit_id": audit_id,
        "repo": {
            "path": str(ROOT),
            "branch": "test",
            "commit": "deadbeef",
        },
        "generated_at": "2026-06-09T00:00:00Z",
        "agent": {
            "name": "fixture",
            "model": "fixture",
            "mode": "audit",
        },
        "reports": [],
        "runner_ready_findings": [],
        "campaign_derivation_rules": {
            "strategy": "fixture",
            "group_by": [],
            "priority_order": ["RISK", "WARN", "INFO"],
        },
        "derived_campaigns": [
            {
                "campaign_id": "2026-06-09::fixture_alpha::001",
                "campaign_type": "followup",
                "source_findings": [],
            }
        ],
    }


def _sample_campaign_payload(
    audit_id: str = "AUDIT_abc123def456",
    *,
    task_lane: str = "architecture_impact",
) -> dict:
    return {
        "audit_id": audit_id,
        "generated_at": "2026-06-09T00:00:00Z",
        "campaigns": [
            {
                "campaign_id": "2026-06-09::fixture_alpha::001",
                "campaign_slug": "fixture_alpha",
                "depends_on": [],
                "campaign_markdown": "# Fixture Campaign\n",
                "tasks": [
                    {
                        "id": "TASK-FIXTURE-001",
                        "slug": "provider_readiness",
                        "task_lane": task_lane,
                        "area": "docs",
                        "risk": "LOW",
                        "files": ["codex_runner/runner.py"],
                        "tests": ["pytest -q tests/codex_runner/test_runner_v2.py"],
                        "commit_message": "Fixture materialization task",
                        "task_artifact_markdown": "# Fixture Task\n",
                        "activation_prompt": "Review fixture materialization only.",
                        "dependencies": [],
                    }
                ],
            }
        ],
    }


def _write_json(path: runner.Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    runner.json_write(path, payload)


def _fixture_args(
    tmp_path: runner.Path,
    audit_json: runner.Path,
    campaign_json: runner.Path,
    *,
    intention_packet: runner.Path | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        repo_root=tmp_path,
        audit_schema_file=ROOT
        / "codex_runner"
        / "schemas"
        / "mega_audit_output.schema.json",
        campaign_set_schema_file=ROOT
        / "codex_runner"
        / "schemas"
        / "campaign_set.schema.json",
        audit_json_file=audit_json,
        campaign_json_file=campaign_json,
        intention_packet_file=intention_packet,
        debug=False,
    )


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
        provider="pi",
    )
    payload_b = runner.run_inputs_payload(
        repo_root=runner.Path("/tmp/repo"),
        base_ref_sha="deadbeef",
        hashes=hashes,
        pass_index=1,
        execute_mode="dry-run",
        provider="pi",
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
    task_b = {
        **_sample_task("TASK-001-B", "alpha"),
        "task_artifact_markdown": "# Task B",
    }
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
    prompt_a = campaign_a["materialized"]["task_prompt_artifact_paths"][
        task_a["id"]
    ]
    prompt_b = campaign_b["materialized"]["task_prompt_artifact_paths"][
        task_b["id"]
    ]

    assert path_a != path_b
    assert prompt_a != prompt_b
    assert "alpha_2026_03_12_001" in path_a
    assert "alpha_2026_03_12_002" in path_b
    assert "alpha_2026_03_12_001" in prompt_a
    assert "alpha_2026_03_12_002" in prompt_b
    assert (tmp_path / path_a).exists()
    assert (tmp_path / path_b).exists()
    assert (tmp_path / prompt_a).exists()
    assert (tmp_path / prompt_b).exists()
    assert (tmp_path / path_a).read_text(encoding="utf-8") == "# Task\n"
    assert (tmp_path / path_b).read_text(encoding="utf-8") == "# Task B\n"


def test_task_artifact_path_collision_fails_clearly(
    tmp_path: runner.Path,
) -> None:
    task_a = _sample_task("TASK-001-A", "alpha")
    task_b = _sample_task("TASK-001-B", "alpha")
    campaign = _sample_campaign(tasks=[task_a, task_b])

    with pytest.raises(
        runner.RunnerError, match="task artifact path collision"
    ):
        runner.materialize_campaign_artifacts(tmp_path, campaign)


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


def test_materialize_creates_standard_task_prompt_artifact(
    tmp_path: runner.Path,
) -> None:
    task = {**_sample_task("TASK-STANDARD", "alpha"), "task_lane": "standard"}
    campaign = _sample_campaign(tasks=[task])

    touched = runner.materialize_campaign_artifacts(tmp_path, campaign)

    prompt_path, content = _prompt_content(tmp_path, campaign, task["id"])
    assert prompt_path.endswith("PROMPT_alpha_2026_03_12.md")
    assert prompt_path in touched
    assert "This is a reviewable Campaign Runner task prompt artifact" in content
    assert "Prompt shape: Standard Codexify Task" in content
    assert "Context:" in content
    assert "Task:" in content
    assert "File paths to inspect:" in content
    assert "Invariants / constraints:" in content
    assert "Validation commands:" in content
    assert "Git add command:" in content
    assert "Git commit command:" in content
    assert "Required output contract:" in content
    _assert_single_fenced_prompt(content)


def test_architecture_impact_prompt_contains_required_sections(
    tmp_path: runner.Path,
) -> None:
    task = {
        **_sample_task("TASK-ARCH", "arch"),
        "task_lane": "architecture_impact",
    }
    campaign = _sample_campaign(tasks=[task])

    runner.materialize_campaign_artifacts(tmp_path, campaign)

    _prompt_path, content = _prompt_content(tmp_path, campaign, task["id"])
    assert "Prompt shape: Architecture-Impact Codexify Task" in content
    for required in (
        "Required pre-read:",
        "ADR impact:",
        "Current-truth anchors:",
        "Invariants / constraints:",
        "Proof surface:",
        "Documentation follow-through:",
    ):
        assert required in content
    _assert_single_fenced_prompt(content)


def test_discovery_prompt_is_read_only_and_commit_optional(
    tmp_path: runner.Path,
) -> None:
    task = {
        **_sample_task("TASK-DISCOVERY", "discovery"),
        "task_lane": "discovery",
        "files": [],
        "tests": [],
    }
    campaign = _sample_campaign(tasks=[task])

    runner.materialize_campaign_artifacts(tmp_path, campaign)

    _prompt_path, content = _prompt_content(tmp_path, campaign, task["id"])
    assert "Read-only investigation first." in content
    assert (
        "Do not modify files unless a follow-up implementation task is created."
        in content
    )
    assert (
        "No automated tests apply unless the discovery task includes a validation script."
        in content
    )
    assert "Do not commit if no files change." in content
    _assert_single_fenced_prompt(content)


@pytest.mark.parametrize(
    ("task_lane", "expected"),
    [
        ("docs_only", "No runtime behavior changes."),
        ("docs_only", "No release claim widening."),
        ("docs_only", "Run docs validation if available."),
        ("proof_runbook", "Capture proof for an existing path only."),
        ("proof_runbook", "Do not change runtime behavior."),
        (
            "proof_runbook",
            "Evidence must distinguish acceptance, completion, and UI/operator visibility where relevant.",
        ),
        (
            "proof_runbook",
            "Commit only proof/runbook artifacts if files are produced.",
        ),
    ],
)
def test_lane_specific_prompt_language(
    tmp_path: runner.Path, task_lane: str, expected: str
) -> None:
    task = {
        **_sample_task(f"TASK-{task_lane}", task_lane),
        "task_lane": task_lane,
    }
    campaign = _sample_campaign(tasks=[task])

    runner.materialize_campaign_artifacts(tmp_path, campaign)

    _prompt_path, content = _prompt_content(tmp_path, campaign, task["id"])
    assert expected in content
    _assert_single_fenced_prompt(content)


def test_missing_task_lane_defaults_prompt_to_discovery(
    tmp_path: runner.Path,
) -> None:
    task = _sample_task("TASK-LEGACY", "legacy")
    campaign = _sample_campaign(tasks=[task])

    runner.materialize_campaign_artifacts(tmp_path, campaign)

    _prompt_path, content = _prompt_content(tmp_path, campaign, task["id"])
    assert "Task lane: discovery" in content
    assert (
        "TODO(operator): task_lane was missing; defaulted to discovery conservatively."
        in content
    )
    assert "Read-only investigation first." in content
    _assert_single_fenced_prompt(content)


def test_fixture_materialization_creates_artifact_inventory_without_provider(
    monkeypatch: pytest.MonkeyPatch, tmp_path: runner.Path
) -> None:
    audit_json = tmp_path / "fixtures" / "audit.json"
    campaign_json = tmp_path / "fixtures" / "campaign.json"
    packet = tmp_path / "fixtures" / "intention.md"
    _write_json(audit_json, _sample_audit_payload())
    _write_json(campaign_json, _sample_campaign_payload())
    packet.write_text("# Fixture Packet\n", encoding="utf-8")

    def fail_provider(*_args, **_kwargs) -> None:
        raise AssertionError("provider dispatch must not be called")

    monkeypatch.setattr(runner, "run_provider_exec", fail_provider)
    monkeypatch.setattr(runner, "render_audit_prompt", fail_provider)
    monkeypatch.setattr(runner, "render_compiler_prompt", fail_provider)
    monkeypatch.setattr(runner, "git_is_clean", lambda *_args, **_kw: True)

    summary = runner.run_fixture_materialization(
        _fixture_args(tmp_path, audit_json, campaign_json, intention_packet=packet),
        base_ref_sha="deadbeef",
        cli_args=[
            "--materialize-from-fixtures",
            "--audit-json-file",
            str(audit_json),
            "--campaign-json-file",
            str(campaign_json),
        ],
    )

    assert summary["provider_invocation_skipped"] is True
    assert summary["selected_campaign"] == "2026-06-09::fixture_alpha::001"

    campaign_doc = (
        tmp_path
        / "docs"
        / "Campaign"
        / "CAMPAIGN_2026_06_09_FIXTURE_ALPHA_001.md"
    )
    task_artifact = (
        tmp_path
        / "docs"
        / "tasks"
        / "fixture_alpha_2026_06_09_001"
        / "TASK_provider_readiness_2026_06_09.md"
    )
    prompt_artifact = (
        tmp_path
        / "docs"
        / "tasks"
        / "fixture_alpha_2026_06_09_001"
        / "PROMPT_provider_readiness_2026_06_09.md"
    )
    today_iso = runner.datetime.now(runner.timezone.utc).date().isoformat()
    run_meta = (
        tmp_path
        / "docs"
        / "_audits"
        / today_iso
        / "AUDIT_abc123def456"
        / "run_meta.json"
    )
    state_path = tmp_path / runner.STATE_PATH

    assert campaign_doc.exists()
    assert task_artifact.read_text(encoding="utf-8") == "# Fixture Task\n"
    prompt_content = prompt_artifact.read_text(encoding="utf-8")
    _assert_single_fenced_prompt(prompt_content)
    assert "Task lane: architecture_impact" in prompt_content
    assert "Prompt shape: Architecture-Impact Codexify Task" in prompt_content

    state = runner.json_read(state_path)
    task = state["campaigns"]["2026-06-09::fixture_alpha::001"]["tasks"][
        "TASK-FIXTURE-001"
    ]
    assert task["task_lane"] == "architecture_impact"
    assert (
        task["content_hash"]
        == state["task_index_by_id"]["TASK-FIXTURE-001"]["content_hash"]
    )

    meta = runner.json_read(run_meta)
    assert meta["provider"]["name"] == "fixture"
    assert meta["provider"]["invocation_skipped"] is True
    assert meta["fixture_materialization"]["provider_invocation_skipped"] is True
    assert meta["fixture_materialization"]["audit_json_file"] == str(
        audit_json.resolve()
    )
    assert meta["fixture_materialization"]["campaign_json_file"] == str(
        campaign_json.resolve()
    )
    assert meta["fixture_materialization"]["intention_packet_file"] == str(
        packet.resolve()
    )


def test_fixture_parse_args_missing_audit_json_fails_clearly(
    tmp_path: runner.Path,
) -> None:
    campaign_json = tmp_path / "campaign.json"
    _write_json(campaign_json, _sample_campaign_payload())

    with pytest.raises(
        runner.RunnerError,
        match="--materialize-from-fixtures requires --audit-json-file",
    ):
        runner.parse_args(
            [
                "--repo-root",
                str(tmp_path),
                "--materialize-from-fixtures",
                "--campaign-json-file",
                str(campaign_json),
            ]
        )


def test_fixture_parse_args_missing_campaign_json_fails_clearly(
    tmp_path: runner.Path,
) -> None:
    audit_json = tmp_path / "audit.json"
    _write_json(audit_json, _sample_audit_payload())

    with pytest.raises(
        runner.RunnerError,
        match="--materialize-from-fixtures requires --campaign-json-file",
    ):
        runner.parse_args(
            [
                "--repo-root",
                str(tmp_path),
                "--materialize-from-fixtures",
                "--audit-json-file",
                str(audit_json),
            ]
        )


def test_fixture_missing_json_path_fails_clearly(tmp_path: runner.Path) -> None:
    campaign_json = tmp_path / "campaign.json"
    missing_audit = tmp_path / "missing-audit.json"
    _write_json(campaign_json, _sample_campaign_payload())

    with pytest.raises(runner.RunnerError, match="Required file not found"):
        runner.parse_args(
            [
                "--repo-root",
                str(tmp_path),
                "--materialize-from-fixtures",
                "--audit-json-file",
                str(missing_audit),
                "--campaign-json-file",
                str(campaign_json),
            ]
        )


def test_fixture_schema_invalid_campaign_fails_before_materialization(
    monkeypatch: pytest.MonkeyPatch, tmp_path: runner.Path
) -> None:
    audit_json = tmp_path / "fixtures" / "audit.json"
    campaign_json = tmp_path / "fixtures" / "campaign.json"
    invalid_campaign = _sample_campaign_payload()
    del invalid_campaign["campaigns"][0]["tasks"][0]["task_lane"]
    _write_json(audit_json, _sample_audit_payload())
    _write_json(campaign_json, invalid_campaign)
    monkeypatch.setattr(runner, "git_is_clean", lambda *_args, **_kw: True)

    with pytest.raises(
        runner.RunnerError,
        match="Schema validation failed for campaign JSON",
    ):
        runner.run_fixture_materialization(
            _fixture_args(tmp_path, audit_json, campaign_json),
            base_ref_sha="deadbeef",
            cli_args=["--materialize-from-fixtures"],
        )

    assert not (tmp_path / "docs" / "Campaign").exists()
    assert not (tmp_path / "docs" / "tasks").exists()
    assert not (tmp_path / runner.STATE_PATH).exists()
