from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.marketing import run_marketing_automation

FIXTURE_ROOT = Path("tests/fixtures/marketing/source")


def test_wrapper_derives_campaign_id_and_stays_dry(
    tmp_path: Path, capsys
) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(FIXTURE_ROOT, source_root)

    rc = run_marketing_automation.run(
        [
            "--date",
            "2026-05-12",
            "--campaign-suffix",
            "MARKETING_V1",
            "--audience",
            "local-first-builders",
            "--channels",
            "website,social",
            "--mode",
            "draft",
            "--source-root",
            str(source_root),
            "--output-root",
            str(output_root),
            "--generated-at",
            "2026-05-12T00:00:00Z",
            "--dry-run",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["campaign_id"] == "CAMPAIGN_2026_05_12_MARKETING_V1"
    assert payload["campaign_id_source"] == "derived"
    assert payload["dry_run"] is True
    assert not (output_root / "CAMPAIGN_2026_05_12_MARKETING_V1").exists()


def test_wrapper_writes_outputs_when_not_dry(tmp_path: Path, capsys) -> None:
    source_root = tmp_path / "source"
    output_root = tmp_path / "output"
    shutil.copytree(FIXTURE_ROOT, source_root)

    rc = run_marketing_automation.run(
        [
            "--campaign-id",
            "CAMPAIGN_TEST_AUTOMATION",
            "--audience",
            "local-first-builders",
            "--channels",
            "website,social,community",
            "--mode",
            "draft",
            "--source-root",
            str(source_root),
            "--output-root",
            str(output_root),
            "--generated-at",
            "2026-05-12T00:00:00Z",
        ]
    )

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["campaign_id"] == "CAMPAIGN_TEST_AUTOMATION"
    assert payload["campaign_id_source"] == "explicit"

    campaign_dir = output_root / "CAMPAIGN_TEST_AUTOMATION"
    assert (campaign_dir / "core-brief.md").exists()
    assert (campaign_dir / "evidence-ledger.json").exists()

    history = (
        source_root
        / "docs"
        / "Marketing"
        / "generated"
        / "history"
        / "run-history.jsonl"
    )
    assert history.exists()
    assert history.read_text(encoding="utf-8").strip()
