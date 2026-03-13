from __future__ import annotations

import json
from pathlib import Path

import runner


def test_load_state_falls_back_to_legacy_state_path(tmp_path: Path) -> None:
    legacy_path = tmp_path / runner.LEGACY_STATE_PATH
    legacy_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "version": 1,
        "campaigns": {"camp": {}},
        "task_index_by_id": {},
        "task_index_by_slug": {},
    }
    legacy_path.write_text(json.dumps(payload), encoding="utf-8")

    state = runner.load_state(tmp_path)

    assert state["version"] == 1
    assert "camp" in state["campaigns"]


def test_materialize_campaign_artifacts_uses_year_month_paths(
    tmp_path: Path,
) -> None:
    campaign = {
        "campaign_date": "2026-02-18",
        "campaign_slug": "security_alpha",
        "campaign_seq": "007",
        "campaign_markdown": "# Campaign",
        "tasks": {
            "TASK-B": {
                "id": "TASK-B",
                "slug": "beta",
                "task_artifact_markdown": "# Beta",
            },
            "TASK-A": {
                "id": "TASK-A",
                "slug": "alpha",
                "task_artifact_markdown": "# Alpha",
            },
        },
        "materialized": {
            "campaign_doc_path": "",
            "task_artifact_paths": {},
        },
    }

    touched = runner.materialize_campaign_artifacts(tmp_path, campaign)

    assert (
        campaign["materialized"]["campaign_doc_path"]
        == "docs/work/campaigns/2026/02/CAMPAIGN_2026_02_18_SECURITY_ALPHA_007.md"
    )
    assert campaign["materialized"]["task_artifact_paths"]["TASK-A"].endswith(
        "docs/work/tasks/2026/02/TASK_2026_02_18_001_alpha.md"
    )
    assert campaign["materialized"]["task_artifact_paths"]["TASK-B"].endswith(
        "docs/work/tasks/2026/02/TASK_2026_02_18_002_beta.md"
    )
    assert any(
        path.startswith("docs/work/campaigns/2026/02/") for path in touched
    )
